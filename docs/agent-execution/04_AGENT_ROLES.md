# 04 — Agent Roles and Independence

Roles are responsibility boundaries, not claims that separate models or processes are already running.

| Role | Owns | Must not do |
|---|---|---|
| Orchestrator | Decompose task, assign agents, enforce state/budget/gates | Declare own work independently verified |
| Researcher | Discover primary sources, extract claims and provenance | Treat search ranking or repeated copies as proof |
| Architect | Contracts, interfaces, ADRs, compatibility map | Hide unknowns behind speculative architecture |
| Implementer | Smallest scoped patch, local tests | Change task acceptance or grant own permissions |
| Test engineer | Test plan, clean execution, logs, regression tests | Alter production code to make tests pass |
| Red team | Adversarial cases, failure injection within authorized sandbox | Expand attack beyond explicitly authorized scope |
| Independent auditor | Reproduce acceptance, inspect evidence and diff | Rely solely on implementer's report |
| Integrator | Resolve branch/worktree conflicts, run combined suite | Merge/deploy without gate |
| Release steward | Build metadata, SBOM, attestations, release checklist | Publish without explicit approval |

## Independence matrix

- Separate role labels in one prompt: **not independent**.
- Separate contexts, same model/provider: partial independence; disclose correlation risk.
- Different model family/provider and separate evidence review: stronger independence, still not proof.
- Human review plus automated tests: complementary, not interchangeable.

## Assignment policy

Choose an agent by tested capability, not title. Record the exact model/version and tools used. If unknown, write `UNKNOWN`. Do not fabricate agent roster, parallel execution, or provider diversity.

## Disagreement protocol

When agents disagree, do not resolve by vote or confidence. Convert the disagreement into competing claims, identify the evidence each predicts, and run a discriminating test or seek a primary source. Preserve unresolved disagreement as `BLOCKED/UNKNOWN`.
