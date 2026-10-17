# Changelog

## [0.4.0] — 2026-10-16 (Gate-3 — first real consumer)

First real-world consumer of the SINGULYAR EIR kernel beyond tests:
**LLMLocalAdapter** — Python port of singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs
(·21 ОБЩЕНИЕ).

### Added
- `runtime/src/adapters/` package
- `runtime/src/adapters/__init__.py` — package marker
- `runtime/src/adapters/rule_layer.py` (151 lines) — Python port of
  singulyar's правило-слой (deterministic regex-based command router for
  14 voice commands: ping/stop/status/identity/count/help/read_log/clear/
  clear_field/load_model/open/repeat/send/what). Pure stdlib, no deps
  (ADR-0002 Tier 1).
- `runtime/src/adapters/llm_local_adapter.py` (356 lines) — Python port of
  singulyar's llm.local adapter. Implements SINGULYAR EIR Adapter contract
  (execute + read_state → Observation tri-state). Declares 4 capabilities
  (llm.command / llm.check_status / llm.answer / llm.generate), all offline
  + local_only + idempotent. Optional llama-cpp-python integration for
  real Qwen2.5-0.5B inference; rule-layer fallback works without weights.
- `runtime/tests/test_llm_local_adapter.py` (251 lines, 20 tests):
  - LLMLocalAdapterTests (11): adapter_id, capabilities, default state,
    rule-layer ping/open/identity, read_state PRESENT/ABSENT, S15 partial
    cache-miss sibling test, free-speech raises NotExecuted, load_model
    failure path
  - RuleLayerTests (5): parse ping/open/send/free-speech, execute
  - IntegrationWithRuntimeTests (3): full Runtime → LLMLocalAdapter
    path, free-speech via Runtime (NEVER CONFIRMED), idempotency at
    adapter level
- `runtime/docs/LLM_LOCAL_ADAPTER.md` — design doc

### Test count: 41 → 61
- SINGULYAR EIR kernel: 41 (unchanged)
- LLMLocalAdapter + rule_layer: 20 (new)

### What this proves (per ADR-0012)
1. SINGULYAR EIR kernel is not just test scaffolding — it drives a real
   adapter (regex-based voice command router)
2. Tri-state Observation contract holds under real adapter lifecycle
3. NotExecuted is the honest failure mode (no LLM + free speech →
   NotExecuted → kernel reports UNKNOWN/WAITING_FOR_HUMAN, never
   CONFIRMED — no hallucination per ADR-002)
4. ADR-0002 Sovereignty Registry invariant holds: rule-layer has zero
   external deps, works offline, no accounts

### Honest disclosure
- No real LLM weights in v0.3 (llama-cpp-python optional)
- No wllama (browser-only — Python uses llama-cpp-python native instead)
- No BroadcastChannel heartbeat (v0.11 JS feature — Python would need
  ZeroMQ or Unix domain socket transport)

---



## 0.3.0
Continuation of 0.2 (not a rewrite). Audit of the Polymath OS report/RUNBOOK and of v0.2 itself.
- Kernel: tri-state observations (PRESENT/ABSENT/UNAVAILABLE) and verdicts (PASS/FAIL/INCONCLUSIVE); capability lists with priority and failover only on `NotExecuted`; hard constraints (`local_only`, `offline`); risk ceilings; attempt budget; `grant_consent`/`resume`/`cancel`; fingerprint check on accepted intents; ledger redaction (HMAC fingerprints).
- Durability: SQLite ledger (WAL, verify on open, JSONL export, checkpoints), event-sourced restart (in-flight → UNKNOWN → readback), real process-death test.
- Schemas enforced by a fail-closed validator.
- Experiment: 14-scenario ablation ladder; generated results; replay page driven by real kernel traces (replaces the scripted v0.2 animation).
- Docs: audit, hardened runbook, experiment plan, limitations, updated spec/roadmap/research/threat model/ADRs.
- Tests: 12 → 40, plus manual mutation check that found and closed one gap.
- Removed: the scripted HTML animation; `fault_after_effect` remains only as a test convenience.

## 0.2.0
Executable kernel, 12 tests, scripted HTML walkthrough.
