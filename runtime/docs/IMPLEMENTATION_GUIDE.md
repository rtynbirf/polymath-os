# Implementation guide for the next engineer (v0.3)

## Local development
1. Install Python 3.10+.
2. Unzip archive.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python src/demo.py`.
5. Open `prototype/index.html`.

## Recommended repository layout for production
- `schemas/`: versioned JSON Schema contracts.
- `kernel/`: state machine, policy gate, planner and verifier interfaces.
- `adapters/`: one adapter per external capability; no adapter owns policy.
- `storage/`: durable append-only event store and export/import.
- `tests/contract/`: adapter contract tests.
- `tests/faults/`: crash, timeout, duplicate, partition and corruption tests.
- `docs/`: threat model, decisions, data flows and operational procedures.

## Rules for implementation
- Never mark `CONFIRMED` unless an independent verifier returns evidence satisfying the expected postcondition.
- Never retry an unknown side effect without querying by idempotency key or asking a human.
- Never let an adapter broaden its permission scope.
- Keep capability manifests versioned and exportable.
- Do not store message bodies or secrets in the evidence ledger by default.
- Every bug fix adds a regression test; every claimed feature maps to code and a test.
- A generated plan is not execution; an adapter response is not verified completion.
- No automatic code/policy self-modification in v0.x.

## Suggested follow-on technologies
Choose only when requirements justify them:
- JSON Schema for wire contracts;
- SQLite/IndexedDB for durable local state;
- OpenTelemetry for traces/metrics/logs;
- WebRTC for peer transport, with separately designed signaling and identity;
- standard platform accessibility APIs for speech, braille, keyboard and switch access.
These are options, not mandatory dependencies.


## v0.3 map of the code
- `src/singulyar_runtime.py` — kernel (state machine, policy, verifier, adapters, in-memory ledger, Runtime).
- `src/sqlite_ledger.py` — durable ledger; open it with the same `redaction_key` you used before, or recovery will refuse.
- `src/schema_validate.py` + `schemas/` — fail-closed subset validator.
- `experiments/ablation.py` — scenario matrix, baselines, results, replay data. Re-run after any kernel change; `tests/test_experiment.py` fails if committed outputs are stale.
- `scripts/check.py` — runs everything and writes `docs/TEST_REPORT.md` and `docs/VALIDATION.md` from the real run.

## Adding an adapter
1. Implement `execute` and `read_state` (tri-state). Raise `NotExecuted` ONLY if you can guarantee no effect.
2. Declare a `Capability` honestly (idempotent? offline? local_only? risk ceiling?).
3. Write contract tests: normal, timeout-after-effect, lying, unreadable, duplicate delivery.
4. Never log payload values.

## Extending the kernel — checklist
Add the failing scenario to `ablation.SCENARIOS` first; add a unit test; run a manual mutation of the new branch (flip its outcome) and confirm a test fails.
