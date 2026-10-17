# ADR-0016 — Self-Rewriting ADR Mechanism (recursive meta-ADR)

**Date:** 2026-10-16 (Gate-7 creative surge, v1.9.0)
**Status:** Accepted
**Deciders:** @USER
**Supersedes:** None (extends ADR-0001 — Record Architecture Decisions)

## Context

ADR-0001 established the ADR pattern: immutable once `Accepted`, superseded
via new ADR with back-reference. But the **mechanism** for self-modification
of the ADR system itself was never specified — it was implied.

This is a recursive concern: how does the ADR system modify its own rules?
Without an explicit mechanism, ADR drift becomes informal — somebody adds
ADR-0017 "because we needed one", and the system silently grows without
governance.

This ADR is the **meta-ADR** — it specifies how ADRs are added, amended,
superseded, and how this very ADR can itself be amended.

## Decision

### 1. ADR lifecycle

Each ADR has a status:
- `Proposed` — written but not yet enforced by `make verify` or a CI check
- `Accepted` — enforced; supersedes any prior ADR it references
- `Deprecated` — replaced by a later ADR; kept for historical reference
- `Superseded by ADR-XXXX` — explicit back-reference to the replacement

### 2. Adding a new ADR

Process:
1. Copy `docs/adr/template.md` to `docs/adr/NNNN-<kebab-slug>.md` where
   NNNN is the next free 4-digit number (zero-padded)
2. Fill in Date, Status (Proposed), Deciders, Context, Decision,
   Consequences, Alternatives, References
3. Add a row to `docs/AUDIT_RESPONSE.md` cross-referencing the new ADR
4. `make verify` check 05 (AUDIT_RESPONSE cross-references all ADRs)
   must pass — otherwise the ADR is not integrated

### 3. Amending an ADR

ADRs are immutable once `Accepted`. To change a decision:
1. Write a new ADR with `Supersedes: ADR-XXXX` (in the new ADR's header)
2. Update the old ADR's status to `Superseded by ADR-YYYY`
3. Both ADRs remain in the tree — the old one for historical context

### 4. Self-amending this ADR (ADR-0016)

This ADR can itself be superseded by a later ADR (e.g. ADR-0020) that
redefines the meta-process. The new meta-ADR must explicitly state:
- What part of ADR-0016 it changes
- Why (the meta-context for the meta-change)
- Whether existing Accepted ADRs are grandfathered or re-evaluated

### 5. The recursive invariant

The ADR system is **recursively self-describing** — every change to the
meta-process is itself an ADR, governed by the meta-process it modifies.

This is a fixed point: the system describes how to describe itself.

## Consequences

- **+**: ADR governance is formal — no informal drift
- **+**: The meta-process is auditable — meta-changes leave a paper trail
- **+**: Recursive self-description — the system can evolve without
  breaking its own rules
- **-**: Adds ceremony — every meta-change requires a new ADR
- **-**: The "what is a meta-change" boundary is fuzzy — adding ADR-0017
  about WebRTC adapter is NOT a meta-change (it's about WebRTC). Adding
  ADR-0020 about "ADRs can be deleted" IS a meta-change.

## Alternatives considered

1. **No meta-ADR (informal)** — rejected: ADR-0001 already implies
   immutability + supersession, but the meta-process is undocumented.
2. **ADR-0001 is the meta-ADR** — rejected: ADR-0001 is about the ADR
   pattern, not about how to amend the pattern itself.
3. **RFC process (like Python PEPs)** — rejected: too heavy for a
   single-author project; ADR is the right granularity.

## Verification

- `make verify` check 04 (ADRs follow template) — passes
- `make verify` check 05 (AUDIT_RESPONSE cross-references all ADRs) — passes
- `docs/SOVEREIGNTY_CONTRACT.md` §3 mentions ADR-0016 as "new in v1.9.0"
- This ADR itself follows the template (Date/Status/Context/Decision/etc.)

## References

- ADR-0001 (Record Architecture Decisions) — the bootstrap ADR this extends
- `docs/adr/template.md` — the template all ADRs follow
- `docs/SOVEREIGNTY_CONTRACT.md` §3 — mentions this ADR
- https://github.com/joelparkerhenderson/architecture-decision-record
- https://cognitect.com/blog/2011/November/22/adr-architecture-decision-records

## Self-reference

This ADR is the **fixed point** of the ADR system — the rule that allows
the rules to change. Per ADR-0006 (falsifiable self-*): this ADR's claim
"ADRs are immutable once Accepted" is itself falsifiable — if you find an
Accepted ADR that has been silently edited (not superseded), this ADR-0016
is violated. Audit by: `git log --follow docs/adr/0001-*.md` — should show
only the initial commit, no edits.
