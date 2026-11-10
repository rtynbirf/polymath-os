# 09 — Cross-Repository Rules

## No premature monorepo

Do not merge, relocate, rename, or archive repositories on the basis of naming similarity or public descriptions. First establish actual code ownership, dependency edges, duplicated behavior, release coupling, and independently valuable use cases.

## Portfolio graph

Every proposed edge between repositories must state:

- source repo and target repo;
- edge type: runtime dependency, build dependency, schema/contract, adapter, data flow, deployment relation, conceptual similarity;
- evidence: manifest/import/workflow/API call/commit or explicit declaration;
- version/commit tested;
- compatibility status and owner.

A dotted/hypothetical graph edge is not a dependency claim.

## Shared contracts before shared code

Prioritize candidate contracts only after source inspection:

- event envelope and event identity;
- task/run/agent identity;
- capability declaration and authorization;
- artifact manifest and media metadata;
- evidence/provenance relation;
- schema versioning and migration;
- cancellation, retry, idempotency and failure semantics.

Implementations may remain separate. Shared conformance tests are preferred over forced code sharing.

## Integration gate

A cross-repo integration requires:
1. both repositories' baseline commits;
2. owner and compatibility matrix;
3. versioned schema/contract;
4. contract tests in both implementations;
5. migration and rollback plan;
6. security and data-flow review;
7. explicit human approval for repository-level changes.

## Initial investigation candidates

The following are research questions, not verified dependencies: `commons` ↔ `runtime-protocol`; `universal-agent` ↔ `cell-swarm`; `cell-swarm` ↔ `runtime-protocol` ↔ `cell-rs`; `polymath-os` ↔ product applications; `polymath-atlas` ↔ evidence ledger; voice/media generation projects ↔ artifact manifest; system-control projects ↔ state/rollback protocol. Replace these hypotheses with source evidence after access.
