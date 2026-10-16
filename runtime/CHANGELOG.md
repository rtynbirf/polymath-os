# Changelog

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
