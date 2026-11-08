# runtime/docs/LLM_LOCAL_ADAPTER.md — SINGULYAR EIR first real consumer

**Date**: 2026-10-16 (Gate-3, ADR-0012 Layer 5 integration).

## What this is

`runtime/src/adapters/llm_local_adapter.py` is the **first real-world consumer**
of the SINGULYAR EIR kernel (per ADR-0012 — SINGULYAR EIR as Layer 5). Until
now, the kernel was exercised only by test scaffolding adapters
(`MemoryAdapter`, `SQLiteEffectAdapter` in `src/singulyar_runtime.py`). These
proved the tri-state Observation contract but didn't connect to any real
external system.

`LLMLocalAdapter` connects to:
1. **rule-layer** (`runtime/src/adapters/rule_layer.py`) — deterministic, regex-
   based, no model weights required. Python port of singulyar's
   `БИБЛИОТЕКИ/adapter-os/llm.mjs · создатьПравилоСлой()`.
2. **optional llama-cpp-python** — for real Qwen2.5-0.5B-Instruct inference via
   GGUF. If `llama-cpp-python` is not installed, the adapter stays in
   `UNAVAILABLE` state for free-speech intents (per ADR-002 — UNKNOWN is
   first-class), but the rule-layer still handles known voice commands.

## Source reference

The JS adapter lives at `rtynbirf/singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs`
(702 lines, ~68KB). Key constants and shapes are preserved verbatim:

| JS (llm.mjs) | Python (llm_local_adapter.py) |
|---|---|
| `export const СЛОВАРЬ_ВЕРСИЯ = 'v0.11'` | `RULES_VERSION = "v0.11"` |
| `export const LLM_РЕПО = 'rtynbirf/singulyar-llm'` | `LLM_REPO = "rtynbirf/singulyar-llm"` |
| `id: 'llm.local'`, `kind: 'llm'`, `priority: 50` | `ADAPTER_ID = "llm.local"`, `KIND = "llm"`, priority via `Capability.priority` |
| `status() { return { state, privacy, reason } }` | `status() → {"state", "privacy", "reason", "rules_version", "llm_repo", "rule_layer_intents"}` |
| rule-layer fallback (14 intents) | `rule_layer.execute(phrase)` — same 14 intents ported |
| `wllama` (llama.cpp → WASM, browser-only) | `llama-cpp-python` (optional, native Python) |

## State machine

```
                ┌─────────────────────┐
                │  __init__           │
                │  state="not_loaded" │
                │  reason="..."       │
                └─────────┬───────────┘
                          │
              load_model(path)
                          │
              ┌───────────┴───────────┐
              │ llama-cpp-python      │
              │ installed?            │
              └─┬─────────────────┬───┘
                │ YES             │ NO
                ▼                 ▼
       ┌──────────────┐  ┌──────────────────┐
       │ state="ready"│  │ RuntimeError     │
       │ reason=""    │  │ (honest failure) │
       └──────────────┘  └──────────────────┘
                          │
                          │ rule-layer STILL works
                          ▼
                   (state stays "not_loaded",
                    but rule_layer.execute()
                    returns responses for
                    known commands)
```

## Tri-state Observation contract (ADR-006)

| State | Returned when |
|---|---|
| `PRESENT` | rule-layer matched + cached response for this exact `idempotency_key` |
| `ABSENT` | no cached response for this exact `idempotency_key` (effect never happened) — even if a sibling key is in cache (per ADR-0010 S15) |
| `UNAVAILABLE` | cache unreadable (internal error — shouldn't happen, but per contract) |

## Capabilities declared (4)

```python
CAPABILITIES = (
    Capability("llm.command",      "execute_command",   "llm.local", "low",    True, True, True, 5),
    Capability("llm.check_status", "check_status",      "llm.local", "low",    True, True, True, 1),
    Capability("llm.answer",       "answer_question",   "llm.local", "low",    True, True, True, 10),
    Capability("llm.generate",     "generate_response", "llm.local", "medium", True, True, True, 20),
)
```

All 4 capabilities are:
- `offline=True` (sovereign core per ADR-0002 — works without network)
- `local_only=True` (data doesn't leave device)
- `idempotent=True` (same `idempotency_key` → same response, safe retry per ADR-007)

## Rule-layer intent dictionary (14 intents)

Mirrors singulyar-llm `ОБУЧЕНИЕ/ПРИМЕРЫ_КОМАНД.jsonl` (v0.6, 142 phrases):

| Intent | Example phrase | Response |
|---|---|---|
| `ping` | "пинг" | "понг" |
| `stop` | "стоп" | "" (silent) |
| `status` | "статус" | "модель не загружена; правило-слой работает" |
| `identity` | "кто ты" | "я локальный голос СИНГУЛЯРА — маленькая модель в браузере, работаю по правилам РУВСОН" |
| `count` | "сколько команд ты знаешь" | "знаю 14 команд: ..." |
| `help` | "что ты умеешь" | "команды: пинг, стоп, статус, ..." |
| `read_log` | "прочитай журнал" | "журнал пуст" |
| `clear` | "очисти журнал" | "журнал очищен" |
| `clear_field` | "сотри текст из поля" | "поле сообщения очищено" |
| `load_model` | "загрузи модель" | "загрузка модели недоступна в этом окружении (Python-порт; wllama — браузерная вещь)" |
| `open` | "открой зал" | "открываю зал" |
| `repeat` | "повтори: привет" | "привет" (echo back) |
| `send` | "отправь: текст" | "отправлено: текст" |
| `what` | "что такое гармония" | "не знаю, что такое гармония" (honest — no LLM) |

Free speech (e.g. "расскажи про эмерджентность") → no rule-layer match →
`NotExecuted` raised → kernel sees "no effect" → can fail over to other
adapters or WAITING_FOR_HUMAN. **MUST NOT hallucinate** (per ADR-002 —
UNKNOWN is first-class, no guessing).

## Test coverage (`runtime/tests/test_llm_local_adapter.py`, 20 tests)

- `LLMLocalAdapterTests` (11 tests): adapter_id constant, capabilities count,
  default state UNAVAILABLE, rule-layer ping/open/identity, read_state PRESENT
  after execute, read_state ABSENT for never-executed key, S15 partial
  cache-miss sibling test, free-speech raises NotExecuted, load_model
  without llama-cpp-python raises RuntimeError.
- `RuleLayerTests` (5 tests): parse ping, parse open with arg, parse send
  with arg, parse free speech returns None, execute ping, execute unknown
  returns None.
- `IntegrationWithRuntimeTests` (3 tests): full Runtime → LLMLocalAdapter
  command path (CONFIRMED), free-speech via Runtime (WAITING_FOR_HUMAN /
  UNKNOWN / FAILED, NEVER CONFIRMED), idempotency at adapter level.

## What this proves (Gate-3 acceptance)

1. The SINGULYAR EIR kernel is **not just test scaffolding** — it can drive
   a real-world adapter with deterministic behavior.
2. The tri-state Observation contract (PRESENT/ABSENT/UNAVAILABLE) holds
   under a real adapter's lifecycle, including partial cache-miss (S15).
3. The `NotExecuted` exception is the **honest failure mode** for an
   adapter that cannot execute (e.g. no LLM weights + free speech). The
   kernel handles it without hallucination — UNKNOWN, not CONFIRMED.
4. The ADR-0002 Sovereignty Registry Tier 1 invariant holds: the rule-layer
   has zero external dependencies (pure stdlib), works offline, no
   accounts, no network.

## What's NOT here (honest disclosure)

- No real LLM weights in v0.3 — `llama-cpp-python` is optional. The Python
  port's primary value is the **rule-layer** (offline deterministic fallback
  for 14 voice commands). Real LLM inference is v0.4 work.
- No wllama (browser-only). The JS adapter uses `wllama` (llama.cpp → WASM)
  for in-browser LLM; Python doesn't have a direct equivalent. The
  `llama-cpp-python` package is the closest, but it's native (not WASM)
  and requires building llama.cpp on the host.
- No heartbeat / presence broadcasting (the v0.11 JS feature where the
  adapter listens to BroadcastChannel `singular-meaning-bus-v1` and
  responds to `зал-31-дышит` pings with `мозг-жив`). Python doesn't have
  BroadcastChannel; would need a different transport (e.g. ZeroMQ or
  Unix domain sockets) — v0.4 work.

## How to use

```python
from runtime.src.adapters.llm_local_adapter import LLMLocalAdapter, CAPABILITIES
from runtime.src.singulyar_runtime import Runtime, Policy

# Create adapter (offline-capable)
adapter = LLMLocalAdapter()

# Optional: load real LLM weights (requires `pip install llama-cpp-python`)
# adapter.load_model("/path/to/qwen2.5-0.5b-instruct-q4_k_m.gguf")

# Wire into SINGULYAR EIR Runtime
rt = Runtime(
    capabilities=list(CAPABILITIES),
    adapters=[adapter],
    policy=Policy({"execute_command", "answer_question", "generate_response", "check_status"}),
)

# Run a known voice command — rule-layer matches deterministically
from runtime.src.singulyar_runtime import Intent
intent = Intent(
    intent_id="voice-1",
    description="voice command: пинг",
    operation="execute_command",
    payload={"phrase": "пинг"},
    expected={},  # we just expect an effect (rule-layer response)
)
state = rt.run(intent)  # → State.CONFIRMED
```

## Cross-references

- ADR-0002 (Sovereignty Registry) — `llama-cpp-python` is Tier 2 (optional,
  replaceable by `ctransformers` or `transformers`); rule-layer is Tier 1
  (pure stdlib).
- ADR-0006 (tri-state Observation) — verified by test_s15_partial_cache_miss.
- ADR-0007 (failover only on NotExecuted) — verified by
  test_free_speech_without_model_raises_not_executed.
- ADR-0010 (mutation testing) — `LLMLocalAdapter` is real production code,
  NOT marked `# pragma: no mutate`. Should be mutation-tested in Gate-2.5.
- ADR-0012 (SINGULYAR EIR as Layer 5) — this is the first Layer 5 consumer.
- ADR-0009 (default-deny) — `_cache` is in-memory, not durable. For
  durability, wrap with `SQLiteEffectAdapter` or use the kernel's ledger.
