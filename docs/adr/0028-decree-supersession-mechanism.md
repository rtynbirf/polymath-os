# ADR-0028 — Decree Supersession Mechanism

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** decree, v3.14.0
**Deciders:** @USER
**Supersedes:** None (extends ADR-0021 Decree as Supreme Law)

## Context

Per ADR-0021, the DecreeLog is **append-only, immutable, hash-chained**.
Once a decree is issued, it cannot be modified or deleted — only new
decrees can be added. This is the right invariant for audit trails and
tamper-evidence.

But the human sometimes needs to **revoke** a previous decree:
- A prohibition that's no longer relevant ("never use WebRTC" — but now
  WebRTC is needed for cell65-llm P2P)
- A permission that was too broad ("allow local unbound DNS" — but now
  we use DNS-over-HTTPS only)
- An observation that was wrong ("Chrome 124 has CVE-2026-XXXX" — but
  Chrome 125+ doesn't)

Without a supersession mechanism, the human has two bad options:
1. Delete the old decree (impossible — append-only invariant)
2. Add a new decree saying "ignore decree #N" (but check_compliance
   doesn't recognize this pattern — it would still enforce the old one)

## Decision

Implement **Decree Supersession** as a new decree category:
- Decrees with `category="supersession"` mark a target decree as superseded
- The target decree remains in the log (immutable, hash-chained) — but
  `get_active_laws()` skips it
- `check_compliance()` only checks non-superseded decrees

### Decree format

A supersession decree has:
- `category="supersession"`
- `scope="supersession:<target_seq>"` — e.g. `"supersession:3"` means
  this decree supersedes decree #3
- `text="<reason>"` — the reason for supersession

Example:
```python
dl.supersede(target_seq=3, reason="no longer need to prohibit WebRTC for cell65-llm P2P")
# → issues a new decree with:
#   category='supersession'
#   scope='supersession:3'
#   text='no longer need to prohibit WebRTC for cell65-llm P2P'
```

### Behavior changes

1. **`DecreeLog.supersede(target_seq, reason)`** — new method
   - Validates target_seq exists (else raises ValueError)
   - Issues a new decree with category="supersession" + scope="supersession:<seq>"
   - Returns the new decree record

2. **`DecreeLog.get_active_laws()`** — modified
   - Builds a `_superseded_set` by scanning for decrees with
     `category='supersession'` and `scope='supersession:N'`
   - Returns only decrees whose seq is NOT in the superseded set
   - Supersession decrees themselves are NOT returned (they're meta-decrees,
     not laws to enforce)

3. **`DecreeLog.check_compliance()`** — unchanged (uses get_active_laws)
   - Automatically skips superseded decrees because they're filtered
     out by get_active_laws

4. **`DecreeLog.get_superseded_decrees()`** — new helper method
   - Returns list of (superseded_seq, superseded_by_seq, reason) tuples
   - For audit / UI display

5. **`DecreeLog.get_all()`** — unchanged (still returns ALL decrees
   including superseded ones — for audit trail)

### Immutability invariant preserved

- Original decrees are NEVER modified (no `superseded_by` column added)
- Supersession is implemented purely via append + scope convention
- The hash chain remains intact — supersession decrees hash-chain
  onto the previous decree like any other

### CLI / UI integration

- `decree-bridge.js`: `supersedeDecree(seq, reason)` API method
- `decree-bridge.js supersede <seq> "<reason>"` CLI verb
- Decree Portal UI: "Supersede" button on each decree (prompts for reason)

## Consequences

**Positive:**
- **Closes a real gap** — decrees can now be revoked without breaking
  append-only invariant
- **Audit trail preserved** — supersession is visible in the log
  (who revoked what, when, why)
- **Backward compatible** — existing decrees work unchanged;
  `get_active_laws()` was already filtering by category, now also
  filters by supersession status
- **Composes with ADR-0026** — AdrAmender handles ADR-level operations
  (create/amend/supersede/deprecate ADR); this ADR handles decree-level
  supersession

**Negative:**
- **Supersession chains are not transitive** — if decree #3 supersedes
  decree #1, and then later decree #5 supersedes decree #3, the system
  still considers decree #1 as superseded (correct) but decree #3's
  supersession effect is not "revoked" (incorrect — it would need a
  separate decree to re-instate #1)
- **Scope format is convention-based** — `"supersession:N"` is parsed
  by string matching, not enforced by schema. A typo like
  `"supersession : 3"` (with spaces) wouldn't be recognized.

**Neutral:**
- Supersession is **non-reversible** (you can't "un-supersede") —
  but you can issue a new decree with the same text as the original
  to re-establish the rule

## Verification

- `runtime/tests/test_decree_log.py` — add 5+ tests for supersession
  scenarios
- `make verify` check 01 (SINGULYAR EIR tests) — still passes
- Manual: issue a decree, supersede it, verify check_compliance no
  longer blocks matching intents

## Alternatives considered

1. **Add `superseded_by` column to decrees table** — rejected:
   requires schema migration; breaks immutability invariant
   (modifying existing rows)
2. **Delete superseded decrees** — rejected: violates append-only
   invariant, loses audit trail
3. **Use a separate "revocations" table** — rejected: more complex,
   requires JOIN in get_active_laws
4. **Use decree text convention like "revoke decree #N"** — rejected:
   natural language parsing is fragile, no clear scope marker

## References

- ADR-0021 (Decree as Supreme Law) — append-only hash-chained invariant
- ADR-0016 (Self-Rewriting ADR Mechanism) — analogous mechanism for ADRs
- ADR-0026 (Decree-Driven ADR Amendment) — meta-architecture counterpart
- `runtime/src/decree_log.py` — implementation
- `runtime/tests/test_decree_log.py` — tests

## Self-reference

This ADR itself can be superseded by a future decree-driven amendment
(per ADR-0026). For example:
- Decree #N (amendment): "supersede ADR-0028 with ADR-0030"
- Decree #N+1 (supersession): "supersede decree #N because ADR-0028's
  non-transitive limitation is too restrictive"

The supersession decree would mark decree #N as superseded, but
AdrAmender would still need to act on the original ADR-0026 decree
to actually create ADR-0030. The two systems compose but don't
overlap.
