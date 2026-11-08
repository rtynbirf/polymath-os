# Technical Specification — SINGULYAR EIR v0.6.1

## 1. Goal
Preserve a person's declared intent across interchangeable execution methods; make every completion claim depend on inspectable evidence of the required final state; treat "cannot tell" as a first-class outcome.

## 2. Entities (separate on purpose)
| Entity | Purpose | Code |
|---|---|---|
| Intent | desired outcome, expected postcondition, risk, consent need, hard constraints (`local_only`, `offline`) | `Intent`, `schemas/intent.schema.json` |
| Capability | declared ability of an adapter: operation, risk ceiling, offline, idempotent, local_only, priority | `Capability`, `capability.schema.json` |
| Execution | one attempt: capability, adapter, idempotency key, attempt number | `Execution` |
| Observation | what the adapter reports about actual state: PRESENT / ABSENT / UNAVAILABLE (+count) | `Observation` |
| Evidence | verifier verdict PASS / FAIL / INCONCLUSIVE over an observation | `Evidence`, `evidence.schema.json` |
| Policy | permissions, consent, risk ceilings, constraint compatibility | `Policy` |

## 3. State machine
`CREATED → PLANNED → EXECUTING → VERIFYING → CONFIRMED`; exceptional: `UNKNOWN`, `FAILED`, `WAITING_FOR_HUMAN`, `RECOVERING`, `CANCELLED`. The transition table is `TRANSITIONS` in code; invalid transitions raise `InvalidTransition`. `CONFIRMED` and `CANCELLED` are terminal.

Key edges: `EXECUTING→UNKNOWN` (ambiguous failure), `EXECUTING→FAILED` (no adapter executed anything), `VERIFYING→UNKNOWN` (state unreadable), `RECOVERING→PLANNED` (absence established, idempotent retry), `RECOVERING→WAITING_FOR_HUMAN` (absent but retry could duplicate), `WAITING_FOR_HUMAN→PLANNED` (after consent / new capability).

## 4. Invariants (each has tests)
1. `CONFIRMED` only after verdict PASS: observation PRESENT, exactly one effect, expected fields equal.
2. UNAVAILABLE ≠ ABSENT. Unreadable state yields UNKNOWN; only ABSENT may lead to retry.
3. Retry of an effect is allowed only for idempotent capabilities, with the same idempotency key, within `max_attempts`, with policy re-checked.
4. Failover to another capability happens only when the previous adapter raised `NotExecuted` (a guarantee of no effect). Any other exception → UNKNOWN; the second adapter is not touched (it could duplicate).
5. Hard constraints and risk ceilings are never downgraded to make a task "work". No compatible capability → `WAITING_FOR_HUMAN` with reasons logged.
6. Write-ahead: `EXECUTION_STARTED` is durable before the adapter is called.
7. After process restart, tasks that were EXECUTING / VERIFYING / RECOVERING become UNKNOWN (`_rehydrate`), then are resolved via `recover()` by readback.
8. An accepted intent cannot be silently altered: `recover/resume/cancel` compare an HMAC fingerprint, mismatch → `ContractError`.
9. Ledger holds fingerprints and field names, never payload values.
10. Consent is not restored from the ledger after restart (fail closed).

## 5. Recovery algorithm (`recover`)
Read actual state with the stored idempotency key:
- UNAVAILABLE → stay UNKNOWN. No guess.
- PRESENT → verify; PASS → CONFIRMED, otherwise FAILED (e.g. wrong value, duplicate count).
- ABSENT → idempotent and attempts left and still authorised → PLANNED → execute again with the same key; non-idempotent → WAITING_FOR_HUMAN; budget exhausted → FAILED.

## 6. Human-control policy
Order: never exceed permissions → never perform prohibited actions → consent for high-risk/irreversible → hard constraints → optimise soft preferences → on unresolved conflict stop and ask. Consent proportional to risk, not per click.

## 7. Evidence and integrity
Hash-linked events (SHA-256 over canonical JSON). SQLite implementation: WAL, `synchronous=FULL`, sequence allocated inside `BEGIN IMMEDIATE`, chain re-verified on open (fail closed), JSONL export, `checkpoint()` / `verify_against()` for truncation detection. Not a signature, trusted timestamp, or truth oracle.

## 8. Privacy / offline
Synthetic data only in prototype. Production: minimise, export/delete/restore, per-capability offline behaviour, queue only safe user-visible pending operations, never claim remote completion while disconnected.

## 9. Error taxonomy and reaction
`CONTRACT_ERROR` (reject), `POLICY_BLOCK` (wait for human), `ADAPTER_NOT_EXECUTED` (fail over), `ADAPTER_EXCEPTION` (UNKNOWN), `VERIFICATION FAIL` (retry only if ABSENT+idempotent), `LEDGER_INTEGRITY_ERROR` (refuse to open). A failure produces a proposed regression test or change request, never an automatic code/policy edit.
