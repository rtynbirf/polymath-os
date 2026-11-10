# 00 — Product / Execution Specification

**Product:** RTYNBIRF Agent Execution System (working title)  
**Target host:** `rtynbirf/polymath-os` (assumption until repository identity and ownership are verified)  
**Maturity:** specification only; runtime not implemented or verified.

## 1. Problem

AI-assisted work across multiple repositories loses context, confuses declared capability with executed behavior, allows scope drift, and can report success without reproducible evidence. A multi-agent workflow can amplify these failures unless authority, state, evidence, and acceptance are explicit.

## 2. Goal

Define a portable, model/provider-agnostic operating layer for agent-assisted engineering. It must make tasks executable under constrained permissions, preserve human control, and make every completion claim traceable to code, specification, tests, and run evidence.

## 3. Non-goals

- Do not replace the existing OS/runtime architecture before inspection.
- Do not require a single LLM provider, commercial orchestration framework, vector database, or hosted memory service.
- Do not merge repositories or force a monorepo.
- Do not grant autonomous merge, release, deployment, deletion, credential, or permission powers.
- Do not treat a role prompt as a separate independent agent.
- Do not define universal philosophical meanings of information/knowledge. Operational field names are local interface contracts, not declarations of universal truth.

## 4. Functional requirements

- **FR-001 Task contract:** every non-trivial task has a versioned machine-readable contract.
- **FR-002 Task graph:** tasks express dependencies, ownership, and parallelizable boundaries.
- **FR-003 Agent manifest:** each execution records agent identity, role, provider/model/version where known, capabilities, and permissions.
- **FR-004 Isolation:** implementation agents work in isolated worktrees/branches and bounded filesystem scopes.
- **FR-005 Tool authorization:** tools are typed, scoped, validated, logged, and authorized at execution time.
- **FR-006 Human gates:** external writes, merge, release, deploy, delete, permission change, and data disclosure require human approval.
- **FR-007 Evidence:** claims link to source/run/artifact evidence and provenance lineage.
- **FR-008 Run record:** commands, environments, exit codes, commit IDs, and gaps are recorded.
- **FR-009 Frozen acceptance:** criteria and test oracle cannot be weakened by the implementation agent.
- **FR-010 Independent review:** non-trivial implementation receives review from a distinct context; high-risk changes prefer different model family or human reviewer.
- **FR-011 Bounded retries:** repair iterations are limited and blind retries are rejected.
- **FR-012 Cancellation:** running tasks can be cancelled and cancellation is observable.
- **FR-013 Recovery:** crashes/timeouts recover from durable state without duplicating non-idempotent actions.
- **FR-014 Observability:** task state transitions, tool calls, failures, costs, and policy denials are traceable.
- **FR-015 Portability:** core contracts do not depend on one provider/runtime.
- **FR-016 Repository boundaries:** cross-repo edges require source evidence and contract tests.
- **FR-017 Evaluation:** agent outcome and execution process are both evaluated.
- **FR-018 Privacy:** repository contents and secrets are not sent to external services unless explicitly authorized.
- **FR-019 Auditability:** decisions, overrides, and policy changes are append-only or versioned.
- **FR-020 Honest status:** missing data remains UNKNOWN/BLOCKED/NOT_RUN; never inferred PASS.

## 5. Quality attributes

- **Safety:** least privilege, sandboxing, human approval, secret redaction.
- **Reliability:** bounded retries, idempotency, durable state, crash recovery.
- **Reproducibility:** exact commit, commands, environment, lockfiles, and artifacts.
- **Interoperability:** versioned schemas, adapters, conformance tests.
- **Portability:** local-first operation, replaceable providers, exportable evidence.
- **Maintainability:** concise root instructions; detailed, indexed documentation; machine-checkable contracts.
- **Efficiency:** parallelize non-overlapping work; avoid duplicated agent context and unnecessary retries.

## 6. Acceptance for the specification package

- A new agent can identify the governing docs and task lifecycle from `AGENTS.md`.
- Task, agent, run, claim, and evidence examples parse against their JSON Schemas.
- The first repository-inspection tasks can be assigned without inventing repo commands.
- Existing repository instructions are never overwritten by installation.
- The package validator and unit tests pass.

## 7. Open decisions

The following require real repository inspection and ADR, not guesswork:

- execution runtime and orchestrator;
- event bus and persistence engine;
- worktree/container backend;
- provider adapters and local model routing;
- memory store and retention model;
- policy engine and approval UI;
- tracing/metrics storage;
- cross-repository contract versioning.
