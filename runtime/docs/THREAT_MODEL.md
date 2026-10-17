# Threat model (prototype scope)

## Assets
User intent, permissions, task state, evidence integrity, adapter credentials (none in prototype), external side effects (simulated).

## Threats and controls
- **False success after timeout:** state remains UNKNOWN until queried/verified.
- **Duplicate action on retry:** idempotency key and adapter-side deduplication.
- **Adapter lies or is buggy:** independent postcondition validator queries adapter state.
- **Unauthorized action:** policy gate checks permissions and consent before execution.
- **Ledger edits:** hash chain detects changed links when compared to a trusted checkpoint.
- **Sensitive data leakage through logs:** current demo uses synthetic text; production must redact by default.
- **Registry single point of failure:** future registry must be rebuildable from versioned manifests.
- **Browser/device loss:** current runtime is in-memory; no durability guarantee.

## Out of scope
Network attacker, malicious browser extension, supply-chain compromise, cryptographic identity, key custody, real payments/messages, multi-user authorization, DoS and production deployment. These require dedicated design and review.


## v0.3 additions
- **Adapter lies (claims success, stores nothing / wrong value):** independent readback, PASS needed (S04–S06).
- **Duplicate effect after ambiguous failure:** same idempotency key; no failover after ambiguous failure; non-idempotent retry needs a human (S03, S13, S14).
- **Silent downgrade of a hard constraint during failover:** capability filter before selection (S10).
- **Intent rewritten after acceptance:** HMAC fingerprint check on recover/resume/cancel.
- **Privacy leak via logs:** ledger stores fingerprints and field names only. Residual risk: low-entropy values behind an HMAC are brute-forceable by anyone holding the key; protect the key.
- **Consent forgery through ledger writes:** consent is not restored from the ledger (fail closed). Residual: anyone who can call `grant_consent` in-process can grant it; real identity/signature is Phase 3/4.
- **Ledger truncation:** needs an external checkpoint; not automated.
- **Hard process death between effect and record:** covered by a real `os._exit` test.
Out of scope still: network attacker, malicious extension, supply chain, key custody, DoS, multi-writer coordination.
