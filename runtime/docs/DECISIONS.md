# Architecture decision log

## ADR-001 — Intent is a contract, not just a prompt
**Decision:** represent desired outcome and postcondition separately from execution instructions.
**Reason:** an instruction can run while the intended outcome fails.
**Trade-off:** structured intent requires validation and sometimes clarification.

## ADR-002 — UNKNOWN is a first-class state
**Decision:** a timeout or lost response does not imply failure or success.
**Reason:** external effects may have occurred even when the caller did not receive confirmation.
**Trade-off:** some tasks remain unresolved pending evidence or human input.

## ADR-003 — Verification is separate from execution
**Decision:** adapter invocation and final-state validation are separate components.
**Reason:** execution response is not independent evidence of the intended result.
**Trade-off:** adapters need query/readback capabilities or a declared inability to verify.

## ADR-004 — No automatic self-modification in v0.x
**Decision:** failures may produce proposed regression tests or change requests, but not silently modify code/policy.
**Reason:** unreviewed adaptation can compound errors and authority violations.
**Trade-off:** improvement is slower but auditable.

## ADR-005 — Small standard-library kernel
**Decision:** no external dependency in the first executable kernel.
**Reason:** easier to inspect, reproduce and run in constrained environments.
**Trade-off:** in-memory storage and simulation are not production-ready.


## ADR-006 — Observation is tri-state
**Decision:** adapters return PRESENT / ABSENT / UNAVAILABLE. **Reason:** v0.2 conflated absence with inability to read, which either blocked safe retries or invited unsafe ones. **Trade-off:** adapters must say honestly when they cannot read.

## ADR-007 — Failover only on a no-effect guarantee
**Decision:** only `NotExecuted` permits trying another capability. **Reason:** any other failure may have produced an effect; a second adapter could duplicate it. **Trade-off:** fewer automatic completions (S07, S14 end UNKNOWN).

## ADR-008 — Restart turns in-flight work into UNKNOWN
**Decision:** on open, EXECUTING/VERIFYING/RECOVERING → UNKNOWN, then recover by readback. **Reason:** the process cannot know what happened between the last durable record and death. **Trade-off:** requires write-ahead logging and readable adapters.

## ADR-009 — Ledger stores fingerprints, not values
**Decision:** HMAC fingerprints and field names. **Reason:** privacy-by-default and consistency with the spec. **Trade-off:** debugging needs the original intent; key management is the operator's job.

## ADR-010 — Consent is not restored from the ledger
**Decision:** fail closed after restart. **Reason:** ledger write access must not equal authority. **Trade-off:** re-grant needed until signed decisions exist.

## ADR-011 — Ablation ladder expressed as separate baselines (for now)
**Decision:** baselines are separate code in `experiments/`, not flags of the kernel. **Reason:** keep the kernel strict. **Trade-off:** a factorial 2^4 design (needed for interaction effects) requires refactoring into flags; planned in Phase 5.
