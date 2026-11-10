# 10 — Implementation Roadmap

All phases are gated. Dates are deliberately omitted until repository baseline, owner capacity, and access are known.

## Phase 0 — Safe repository entry

**Work:** revoke exposed PATs; use web-based GitHub CLI/App login; identify default branch, current `AGENTS.md`, branch rules, CODEOWNERS, CI, tests, license, repo security settings.  
**Exit:** accurate repo snapshot; credentials not exposed; no source changes; unknowns explicit.

## Phase 1 — Baseline and repo truth

**Work:** map tree, source modules, entrypoints, build/test commands, dependencies, Actions, release path, current open defects; run safe existing checks; save evidence.  
**Exit:** baseline commit and reproducible checks; test coverage gaps; architecture map with OBSERVED vs DECLARED vs UNKNOWN.

## Phase 2 — Adopt documentation contract

**Work:** merge short `AGENTS.md` navigation map; add task/evidence/run/ADR templates; validate links/schema; define project commands from observed repo facts.  
**Exit:** one pilot task can be executed using the contract without ambiguity or overwriting existing rules.

## Phase 3 — Single-agent harness pilot

**Work:** choose one small, reversible, low-risk task; run task contract → isolated implementation → tests → independent review → evidence closeout.  
**Exit:** reproducible end-to-end run, clear cost/time/failure data, no policy bypass.

## Phase 4 — Multi-agent pilot

**Work:** parallelize only independent discovery/test-design tasks; then one implementer and a separate reviewer; compare same-model vs different-model review if available.  
**Exit:** measured gain over single-agent baseline without higher critical false-PASS rate or uncontrolled scope drift.

## Phase 5 — Shared portfolio contracts

**Work:** investigate cross-repo edges; define only proven shared contracts; add conformance fixtures and versioning.  
**Exit:** two real implementations pass same contract tests; independent release cadence remains possible.

## Phase 6 — Controlled autonomy

**Work:** branch-level write capability; scoped credentials; policy enforcement; observability; cancellation/recovery; artifact provenance.  
**Exit:** risk-tiered actions enforced by runtime and host, not prompt alone; destructive/release actions remain human-approved.

## Stop conditions

Stop and replan on credential exposure, unclear data ownership, test oracle mutation, unverifiable base state, repeated false PASS, unsafe tool scope, uncontrolled egress, or two failed repair iterations.
