# Research basis and synthesis (checked 2026-10-16, v0.3)

This is a targeted review of standards and established practices relevant to the prototype, not a claim to have exhaustively reviewed every world trend.

## Practices adopted

1. **Risk management across lifecycle — NIST AI RMF / GenAI Profile.** Adopted as a lifecycle discipline: identify context and risks, define controls, test, monitor, and update. The prototype operationalizes this narrowly through policy gates, failure taxonomy, explicit uncertainty, fault injection and acceptance criteria. It does not claim NIST conformity.
   - https://www.nist.gov/itl/ai-risk-management-framework
   - https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf

2. **Common observability semantics — OpenTelemetry.** Adopted conceptually: distinguish task/attempt/adapter/verifier events and use consistent names. Prototype ledger is intentionally tiny; it is not an OpenTelemetry implementation.
   - https://opentelemetry.io/docs/concepts/semantic-conventions/
   - https://opentelemetry.io/docs/specs/semconv/

3. **Offline-capable local data — IndexedDB guidance.** Adopted as a future browser persistence option, with explicit warning that offline capability does not itself guarantee durability or prevent eviction. The current tested kernel uses in-memory Python objects.
   - https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB
   - https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Basic_Terminology

4. **Transport semantics — W3C WebRTC.** Adopted as a later adapter option, not built into the kernel. Reliable delivery at a data-channel layer is not equivalent to recipient understanding or even application-level acknowledgement.
   - https://www.w3.org/TR/webrtc/

5. **Transactional recovery and state verification.** Adopted from established reliability engineering: never infer final state from a timeout; query state by idempotency key; make duplicate suppression explicit; treat irreversible external effects as non-rollbackable. SQLite WAL documentation also highlights that durability depends on handling all parts of persistent state correctly.
   - https://www.sqlite.org/wal.html

## Emergent proposal — inference, not external fact

The prototype's distinctive hypothesis is **intent-preserving, evidence-gated composition**:
- hold intent and hard constraints stable;
- choose a capability/adaptor based on declared properties;
- verify the final state independently;
- turn verified defects into regression tests, not automatic unreviewed self-modification;
- retain `UNKNOWN` when evidence is insufficient.

This combines known practices; no claim is made that each component is new. Novelty can only be evaluated after a systematic prior-art search and a measurable experiment.

## Known gaps in research

- No systematic patent or academic literature review.
- No formal comparison against LangGraph, AutoGen, Temporal, durable workflow engines, actor systems, event sourcing, workflow nets, or transaction/outbox patterns.
- No empirical evidence yet that this architecture outperforms a simpler workflow.
- No security review of real communications or cryptographic design.


## v0.3 refresh (2026-10-16) — with confidence labels
Source quality: items marked **[secondary]** come from third-party explainers retrieved in search, not from the primary specification page; verify against the primary source before relying on them.

9. **MCP current revision [secondary].** Third-party sources report the current MCP specification revision as 2026-07-28 (stateless core: per-request version/capabilities, initialize handshake and session id removed), after the Dec 2025 donation to the Agentic AI Foundation under the Linux Foundation. Consequence adopted: keep protocol code behind a thin internal adapter (`Capability`/`Adapter` here) and pin versions. Primary: https://modelcontextprotocol.io
10. **OpenTelemetry GenAI semantic conventions [secondary].** Reported as still developing / not stable. Consequence: event names in the ledger are internal and stable for this project; mapping to OTel is a later adapter. Primary: https://opentelemetry.io/docs/specs/semconv/
11. **SLSA / Sigstore [secondary].** Sources describe the stabilised Build track L1–L3 (L2 = provenance signed by a hosted build platform; L3 = platform prevents the build from forging provenance) and a newer spec version with a Source track; versions disagree across sources. Consequence: Polymath v1.0 target stated as Build L2 (see `AUDIT_POLYMATH.md` A3). Primary: https://slsa.dev
12. **Durable execution — Temporal (from v0.2 notes).** Retried activities must be idempotent; timeouts may follow an effect. Adopted: idempotency key, UNKNOWN, readback. Not adopted: workflow engine dependency in the minimal kernel. A real comparison against Temporal is open work (`EXPERIMENT_PLAN.md`).
13. **Local-first software (Kleppmann et al., 2019).** User-owned data and offline capability; adopted as design intent for export/restore. Not claimed: CRDT sync or multi-device conflict handling (Phase 6).
14. **Mutation testing as a test-quality check.** Not an external source claim; applied manually here, and it found a real gap (see `LIMITATIONS.md`).

## What this synthesis adds, stated carefully
Known: idempotency keys, write-ahead logging, event sourcing, outbox, readback verification, contract tests, hash chains. Proposed combination: a single small kernel in which (a) hard constraints and risk ceilings gate adapter selection, (b) failover is permitted only on a no-effect guarantee, (c) completion requires independent PASS, (d) UNKNOWN is a state that survives restarts, and (e) the ledger keeps fingerprints rather than data. Whether this combination is novel or better than existing workflow engines is **unproven**.
