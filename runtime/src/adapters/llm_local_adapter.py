"""runtime/src/adapters/llm_local_adapter.py — SINGULYAR EIR real adapter
for local LLM inference (Python port of singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs).

This is the FIRST real consumer of the SINGULYAR EIR kernel beyond tests
(per ADR-0012 — SINGULYAR EIR as Layer 5). Previous adapters
(MemoryAdapter, SQLiteEffectAdapter) were test scaffolding — they proved
the kernel's tri-state Observation contract but didn't connect to any
real external system. LLMLocalAdapter connects to:
  - rule-layer (deterministic, regex-based, no model weights)
  - optional llama-cpp-python (if installed) for real Qwen2.5-0.5B
    inference via GGUF

The original JS adapter (singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs) uses
wllama (llama.cpp → WebAssembly) to load Qwen2.5-0.5B GGUF in the
browser. Python doesn't have a wllama equivalent, so:
  - DEFAULT state: UNAVAILABLE (model not loaded)
  - rule-layer: works without weights (offline fallback, like the JS version)
  - LLM inference: optional via llama-cpp-python; if not installed,
    free-speech intents return NotExecuted (no effect — kernel
    doesn't fall back, per ADR-007)

State machine:
  - not_loaded (default) → status() returns UNAVAILABLE with reason
  - ready (after load_model()) → status() returns READY
    Note: 'ready' here means "model loaded" not "can answer any
    question" — the rule-layer is always available regardless of
    model state (matches JS semantics: 'правило-слой исполняет
    команды словаря БЕЗ модели').

Tri-state Observation contract (per ADR-006):
  - PRESENT: rule-layer match found → response recorded in cache
  - ABSENT: no rule-layer match, model not loaded, NotExecuted raised
  - UNAVAILABLE: query failed (e.g. cached response unreadable)

Per ADR-0010: this is real production consumer code (NOT marked
'# pragma: no mutate'). Mutation testing should cover its branches.

Capabilities declared:
  - llm.answer        operation: 'answer_question'   risk: low    idempotent offline local_only  priority 10
  - llm.command       operation: 'execute_command'   risk: low    idempotent offline local_only  priority 5
  - llm.generate      operation: 'generate_response' risk: medium idempotent offline local_only  priority 20
  - llm.check_status  operation: 'check_status'      risk: low    idempotent offline local_only  priority 1

Honest disclosure (LIMITATIONS.md item 8 still applies):
  - No real network, no real LLM weights in v0.3
  - rule-layer covers 14 voice commands (offline, deterministic)
  - Free-speech questions return NotExecuted (not hallucinated)
  - Optional llama-cpp-python integration is v0.4 work
"""

import hashlib
import json
import os
import threading
from typing import Any, Dict, List, Optional

# Import SINGULYAR kernel (Path setup via sys.path or relative)
import sys
from pathlib import Path
_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from singulyar_runtime import (
    Adapter, Capability, Intent, Observation,
    PRESENT, ABSENT, UNAVAILABLE,
    NotExecuted,
)
from adapters import rule_layer

# ───────────────────────────────────────────────────────────────
# Constants (mirrors singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs L85-87)
# ───────────────────────────────────────────────────────────────

ADAPTER_ID = "llm.local"
KIND = "llm"
LLM_REPO = "rtynbirf/singulyar-llm"
RULES_VERSION = "v0.11"  # matches JS СЛОВАРЬ_ВЕРСИЯ

# Per ADR-0002 Tier 1 — no external deps required at runtime.
# llama-cpp-python is OPTIONAL — adapter works without it (rule-layer only).
try:
    from llama_cpp import Llama  # type: ignore
    _HAS_LLAMA_CPP = True
except ImportError:
    Llama = None  # type: ignore
    _HAS_LLAMA_CPP = False


# ───────────────────────────────────────────────────────────────
# Capabilities declared by LLMLocalAdapter (mirrors singulyar CAPABILITIES)
# ───────────────────────────────────────────────────────────────

CAPABILITIES = (
    # Low-risk: rule-layer handles known commands deterministically
    Capability(
        capability_id="llm.command",
        operation="execute_command",
        adapter_id=ADAPTER_ID,
        risk_ceiling="low",
        offline=True,
        idempotent=True,
        local_only=True,
        priority=5,
    ),
    # Low-risk: model status query (READY/UNAVAILABLE)
    Capability(
        capability_id="llm.check_status",
        operation="check_status",
        adapter_id=ADAPTER_ID,
        risk_ceiling="low",
        offline=True,
        idempotent=True,
        local_only=True,
        priority=1,
    ),
    # Low-risk: answer_question — rule-layer or cached LLM response
    Capability(
        capability_id="llm.answer",
        operation="answer_question",
        adapter_id=ADAPTER_ID,
        risk_ceiling="low",
        offline=True,
        idempotent=True,
        local_only=True,
        priority=10,
    ),
    # Medium-risk: generate_response — full LLM inference (rule-layer matches
    # are not considered "generation" — they're cached responses)
    Capability(
        capability_id="llm.generate",
        operation="generate_response",
        adapter_id=ADAPTER_ID,
        risk_ceiling="medium",
        offline=True,
        idempotent=True,
        local_only=True,
        priority=20,
    ),
)


class LLMLocalAdapter(Adapter):
    """Python port of singulyar's llm.local adapter (·21 ОБЩЕНИЕ).

    Lifecycle:
      1. __init__: state = "not_loaded" (UNAVAILABLE for LLM, but rule-layer ready)
      2. load_model(path): if llama-cpp-python installed, load GGUF → state = "ready"
         If not installed, state stays "not_loaded" — rule-layer still works
      3. execute(intent, key):
         - First try rule_layer.execute(phrase) — deterministic, no weights
         - If rule-layer match: store response in cache, return value
         - If no rule-layer match and model loaded: try LLM.generate
         - If no rule-layer match and model NOT loaded: raise NotExecuted
           (kernel sees "no effect", can fail over or wait for human)
      4. read_state(intent, key): PRESENT (cached) | ABSENT (no cache) | UNAVAILABLE (model not loaded AND no rule-layer match for this key)
    """

    adapter_id = ADAPTER_ID

    def __init__(self, model_path: Optional[str] = None, **kw):
        super().__init__(**kw)
        self._model_path = model_path
        self._llm: Optional[Any] = None  # llama_cpp.Llama instance, if loaded
        self._state: str = "not_loaded"  # "not_loaded" | "ready"
        self._reason: str = "веса не загружены — вызови load_model(path) или используй правило-слой"
        self._lock = threading.Lock()  # serialize execute() (single-writer per ADR-0009)
        # Cache: idempotency_key → response dict (PRESENT)
        # Per ADR-009: store HMAC fingerprint of response, not response itself
        # But for LLMLocalAdapter, the response IS the effect — keeping it
        # in-memory (not durable). For SQLite durability, wrap with SQLiteEffectAdapter.
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._calls: int = 0

    # ─── Adapter contract ────────────────────────────────────────────

    def status(self) -> Dict[str, str]:
        """Return adapter status — mirrors singulyar status() return shape."""
        return {
            "state": "READY" if self._state == "ready" else "UNAVAILABLE",
            "privacy": "local",
            "reason": "" if self._state == "ready" else self._reason,
            "rules_version": RULES_VERSION,
            "llm_repo": LLM_REPO,
            "rule_layer_intents": str(rule_layer.intent_count()),
        }

    def is_available(self) -> bool:
        """LLMLocalAdapter is ALWAYS available for rule-layer commands.
        For LLM-specific operations, requires load_model()."""
        return True  # rule-layer works without weights

    def execute(self, intent: Intent, idempotency_key: str) -> Any:
        """Execute the intent — try rule-layer first, then LLM if loaded.

        Per ADR-007: raises NotExecuted only if NO effect occurred.
        Rule-layer match = effect occurred (response cached).
        LLM match = effect occurred.
        No match + no model = NotExecuted (no effect, kernel can fail over).
        """
        with self._lock:
            key = idempotency_key

            # Idempotency: if we've already executed this key, return cached
            # (don't increment _calls — this is a cache hit, not a real execute)
            if key in self._cache:
                return self._cache[key]["response"]
            self._calls += 1

            phrase = intent.payload.get("phrase", "") or intent.description
            operation = intent.operation

            # 1. Rule-layer (always available — no model required)
            rule_result = rule_layer.execute(phrase)
            if rule_result is not None:
                response = rule_result["response"]
                self._cache[key] = {
                    "response": response,
                    "via": "rule-layer",
                    "intent_matched": rule_result["intent"],
                    "arg": rule_result["arg"],
                    "phrase": phrase,
                }
                return response

            # 2. LLM (if loaded)
            if self._state == "ready" and self._llm is not None:
                try:
                    # Real LLM inference via llama-cpp-python
                    prompt = self._build_prompt(phrase, intent)
                    llm_response = self._llm(prompt, max_tokens=128, stop=["</s>"])
                    text = llm_response["choices"][0]["text"].strip() if isinstance(llm_response, dict) else str(llm_response)
                    self._cache[key] = {
                        "response": text,
                        "via": "llm.local",
                        "phrase": phrase,
                    }
                    return text
                except Exception as e:
                    # Per ADR-007: any non-NotExecuted exception leaves the
                    # second adapter untouched — kernel treats as UNKNOWN.
                    # We don't raise NotExecuted here because we attempted an
                    # effect (LLM call); even if it errored, the LLM might
                    # have produced output. Surface the error.
                    raise RuntimeError(f"LLM inference failed: {e}")

            # 3. No rule-layer match, no LLM — NotExecuted (no effect, kernel fallback)
            raise NotExecuted(
                f"rule-layer no match for phrase {phrase!r}, "
                f"model not loaded (state={self._state}). "
                f"Free-speech without model: NotExecuted (no hallucination, per ADR-002)."
            )

    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        """Read the current state for this intent's idempotency_key.

        Tri-state (per ADR-006):
          PRESENT: response is cached for this exact key
          ABSENT: no cached response for this exact key (effect never happened)
          UNAVAILABLE: adapter can't tell (e.g. internal error reading cache)

        Per ADR-0010 S15 (Gate-2): MUST return ABSENT for absent key,
        even when a sibling key is in the cache. Adjacent cache entries
        do NOT pollute the per-key state-query.
        """
        key = idempotency_key
        try:
            if key in self._cache:
                entry = self._cache[key]
                return Observation(
                    status=PRESENT,
                    value={"response": entry.get("response", ""),
                           "via": entry.get("via", "unknown"),
                           "intent_matched": entry.get("intent_matched", "")},
                    count=1,
                )
            # ABSENT — exact key not in cache. Sibling keys DO NOT pollute.
            return Observation(status=ABSENT, value=None, count=0)
        except Exception:
            # UNAVAILABLE — cache unreadable (shouldn't happen, but per contract)
            return Observation(status=UNAVAILABLE, value=None, count=0)

    # ─── Lifecycle methods ─────────────────────────────────────────

    def load_model(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Load LLM weights from GGUF file. Returns status dict.

        If llama-cpp-python is not installed, raises RuntimeError (honest failure,
        not silent). Rule-layer still works after this failure.
        """
        if self._state == "ready":
            return {"state": "ready", "reason": "model already loaded", "via": "llm.local"}

        if not _HAS_LLAMA_CPP:
            raise RuntimeError(
                "llama-cpp-python not installed; cannot load real LLM weights. "
                "Rule-layer still works (rule_layer.execute() is offline). "
                "Install with: pip install llama-cpp-python"
            )

        path = path or self._model_path
        if not path or not os.path.exists(path):
            raise RuntimeError(f"model path not found: {path}")

        self._llm = Llama(model_path=path, n_ctx=512, verbose=False)
        self._state = "ready"
        self._reason = ""
        return {"state": "ready", "via": "llm.local", "model_path": path}

    def calls(self) -> int:
        """Number of execute() invocations — for testing."""
        return self._calls

    def cache_size(self) -> int:
        """Number of cached idempotency_key entries."""
        return len(self._cache)

    def cache_keys(self) -> List[str]:
        """All cached keys — for S15 partial cache-miss test inspection."""
        return list(self._cache.keys())

    # ─── Internal helpers ──────────────────────────────────────────

    def _build_prompt(self, phrase: str, intent: Intent) -> str:
        """Build the LLM prompt with system instruction (mirrors singulyar
        ПРАВИЛА_СИНГУЛЯРА.txt — 17 rules: language, simplicity, honesty,
        boundaries, no-idols, format, identity, commands, update, ...)."""
        system_prompt = (
            "Ты — локальный голос СИНГУЛЯРА RUVSON. Живёшь у человека в браузере, "
            "работаешь без интернета и без сервера. Никакой лести: не подхалимаж, "
            "а помощь по делу. Отвечай на том языке, на котором задан вопрос. "
            "Короткие фразы, живые слова. Не знаешь — скажи «не знаю». Не выдумывай."
        )
        return f"{system_prompt}\n\nВопрос: {phrase}\nОтвет:"

    def __repr__(self) -> str:
        return (f"<LLMLocalAdapter state={self._state} "
                f"calls={self._calls} cache={len(self._cache)} "
                f"llama_cpp={'yes' if _HAS_LLAMA_CPP else 'no'}>")


# ───────────────────────────────────────────────────────────────
# Convenience: registry-friendly Capability list
# ───────────────────────────────────────────────────────────────

def default_capabilities() -> tuple:
    """Return the Capability tuple for LLMLocalAdapter.
    Used by MCPCapabilityRegistry-style registration patterns.
    """
    return CAPABILITIES


def default_adapter(model_path: Optional[str] = None) -> LLMLocalAdapter:
    """Construct a default LLMLocalAdapter instance.
    Convenience for tests and integration."""
    return LLMLocalAdapter(model_path=model_path)
