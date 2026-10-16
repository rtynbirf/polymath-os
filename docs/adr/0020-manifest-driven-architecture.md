# ADR-0020 — Manifest-Driven Architecture + Hash-Pin-at-Loader

**Date:** 2026-10-16 (v2.8.0)
**Status:** Accepted
**Deciders:** @USER
**Supersedes:** None (extends ADR-0018 Genomic + ADR-0006 Falsifiable)

## Context

WIN_PE material (H-PE11 design projection) introduced several patterns
that polymath-os can incorporate without executing WIN_PE itself. This
ADR formalizes the two most impactful:

1. **HoloManifest as single source of truth** — one record yields multiple
   projections (CI check, test, audit cross-ref, AGENTS.md mention). No
   desynchronization possible in principle.

2. **Hash-pin at loader, not just at repo** — singulyar-llm has MANIFEST.txt
   with SHA-256 but the browser loader ignores it. Hash must be verified
   at USE time: tampered part → UNAVAILABLE with reason, not silent accept.

## Decision

### 1. Hash-pin at loader (implemented)

`LLMLocalAdapter.verify_model_hash(path, expected_sha256) → bool`:
- Computes SHA-256 of the model file at load time
- If mismatch → state stays UNAVAILABLE, reason = "hash mismatch"
- Per ADR-0006: honest failure, not silent accept
- Per WIN_PE audit B1: "pin at loader, not just at repo"

### 2. PREPARED as evidence edge case (documented, future implementation)

Evidence verdict currently: PASS / FAIL / INCONCLUSIVE.
WIN_PE introduces PREPARED_NOT_SENT — effect prepared but deferred.

Proposed mapping:
- New verdict: `PREPARED` (effect prepared, awaiting human action)
- New operation: `prepare` (like `answer_question` but doesn't execute)
- `expected: {url}` — the prepared artifact
- Human clicks link → triggers follow-up Intent with `operation: "execute"`
- Evidence: PREPARED → on human action → PASS or FAIL

This is **documented but not yet implemented** in v2.8.0. Future v0.5.

### 3. HoloManifest pattern (documented, future implementation)

A single `MANIFEST.json` in polymath-os root:
```json
{
  "adapters": [
    {"id": "llm.local", "kind": "adapter", "version": "v0.4",
     "sha256": "...", "capabilities": ["llm.command", "llm.answer", ...],
     "offline": true, "local_only": true}
  ],
  "adrs": [
    {"id": "0002", "kind": "adr", "status": "Accepted",
     "title": "Sovereignty Registry"}
  ],
  "patterns": [
    {"id": "P04", "kind": "pattern", "ci_check": "#16", "status": "ACTIVE"}
  ]
}
```

One record → projections: CI check, test, audit cross-ref, AGENTS.md
mention, Sovereignty Registry Tier. Adding a part = adding one record.

This is **documented but not yet implemented** in v2.8.0. Future v0.5.

### 4. Version-marker discipline (strict `>` not `>=`)

Per WIN_PE audit D2: singulyar-llm gate `>=` lets equal-version upstream
through silently. Must be strict `>`.

Applied to polymath-os: ADR-0016 (self-rewriting ADR mechanism) —
when checking if a new ADR supersedes an old one, the version must be
strictly greater, not equal.

### 5. `eir://` URI scheme (documented, future)

`eir://intent/{intent_id}?operation={operation}&phrase={phrase}` —
URI-encoded Intent, parsable by the Python↔JS bridge.

This is **documented but not yet implemented**. Future v0.5.

## Consequences

- **+**: Hash verified at use time, not just storage time
- **+**: PREPARED state formalizes "deferred side-effect" pattern
- **+**: HoloManifest prevents desynchronization between CI/tests/audit
- **+**: Version-marker discipline catches silent upstream drift
- **-**: verify_model_hash adds ~1s per model load (SHA-256 of 469MB)
- **-**: PREPARED/HoloManifest/eir:// are future work (v0.5)

## Verification

- `LLMLocalAdapter.verify_model_hash()` exists and returns bool
- `make verify` still 20/20
- ADR-0016 cross-references this ADR for version-marker discipline

## References

- WIN_PE material (H-PE11 design projection, shared by user 2026-10-16)
- ADR-0006 (Falsifiable self-*) — hash mismatch = UNAVAILABLE, not silent
- ADR-0018 (Genomic Architecture) — each part carries the whole
- ADR-0016 (Self-rewriting ADR) — version-marker discipline
- AUDIT_CELL65_LLM.md L4 (weight integrity) — this ADR closes that finding
