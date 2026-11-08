# ADR-0017 — Ecosystem Governance Protocol

**Date:** 2026-10-16 (v2.5.0)
**Status:** Accepted
**Deciders:** @USER
**Supersedes:** None (extends ADR-0002 + ADR-0007)

## Context

Gate-5 (third-level audit of singulyar) produced 90 findings. Steps 1-5 of
the ecosystem integration path (v2.1.0-v2.4.0) filed 5 critical findings as
issues in singulyar and created 5 PRs — all 5 MERGED. The circuit closed:
audit → issue → kernel → GitAdapter → PR → MERGE.

This ADR formalizes the governance protocol that made that possible.

## Decision

### 1. Audit cadence

polymath-os audits singulyar quarterly (or on-demand via workflow_dispatch).
Findings are categorized:
- **Critical** (security, data loss, broken feature) → filed as issue + PR
- **Medium** (discipline failure, doc drift) → filed as issue
- **Low** (code smell, minor inconsistency) → documented in AUDIT_SINGULYAR.md only

### 2. Cross-repo execution protocol

When a critical finding requires a code fix:
1. **Intent**: human (or AI session) says "fix S{N}"
2. **Kernel**: SINGULYAR EIR routes Intent → GitAdapter capability
3. **Branch**: created in target repo (singulyar) from main HEAD
4. **Fix**: applied to the specific file (surgical, minimal diff)
5. **Commit**: with message referencing audit finding + issue number
6. **PR**: created with body linking to AUDIT_SINGULYAR.md + issue
7. **Merge**: squash-merged if fix is surgical (one-file, <10 lines changed)
8. **Verify**: target repo's CI/tests pass after merge

### 3. Governance workflow

`.github/workflows/cross-repo-governance.yml` runs weekly (Tuesday 03:00 UTC):
- Checks singulyar has AGENTS.md, CODEOWNERS, SECURITY.md
- Counts open issues (incl. audit findings from polymath-os)
- Uploads governance report as artifact

### 4. Sovereignty drill (cross-repo)

Extends `scripts/sovereignty_drill.py` to also disable singulyar's Tier 2
dependencies (Nostr relays, STUN, mempool) and verify singulyar's offline
core still works. (Future — requires singulyar test suite integration.)

### 5. Issue lifecycle

Issues filed from AUDIT_SINGULYAR:
- **Open** until PR is merged or finding is closed as "won't fix"
- Auto-close when linked PR is merged (GitHub auto-close via "closes #N" in commit message)
- P0 label for critical (security/data-loss), P1 for medium, P2 for low

## Consequences

- **+**: Formal governance — polymath-os doesn't just audit, it ACTS
- **+**: Surgical fixes — one-file, <10 line diffs, squash-merged
- **+**: Full traceability — audit finding → issue → PR → merge, all linked
- **-**: Requires PAT with `contents:write` + `pulls:write` on target repo
- **-**: Cross-repo merge conflicts possible (especially when two findings
  affect the same file — see S26+S27 both in ·17 ЗАЛ)

## Alternatives considered

1. **File issues only, let human create PRs** — rejected: too slow, the
   human has limited ability to manually create PRs
2. **Full automation (AI creates + merges without human review)** — accepted
   for surgical fixes (<10 lines, one file). Complex fixes stay open for review.
3. **Cross-repo CI only (no PRs)** — rejected: CI checks but doesn't fix

## Verification

- PR #11 (S18): MERGED — S15_MAX 140→200 live in singulyar ✅
- PR #13 (S1): MERGED — honest tagline live ✅
- PR #14 (S26): MERGED — CSP Nostr allowlist live ✅
- PR #15 (S27): MERGED — innerHTML→textContent XSS fix live ✅
- PR #16 (S37): MERGED — data-clearing warning live ✅

All 5 critical findings from AUDIT_SINGULYAR.md are fixed and live.

## References

- ADR-0002 (Sovereignty Registry) — Tier classification for all repos
- ADR-0007 (Multi-agent) — research=parallel, execution=single+verifier
- ADR-0016 (Self-rewriting ADR mechanism) — how to amend this protocol
- docs/AUDIT_SINGULYAR.md — the 90 findings that drove this protocol
- docs/ECOSYSTEM.md — the 4-repo map
- .github/workflows/cross-repo-governance.yml — weekly governance check
