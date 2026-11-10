# 05 — Execution Workflow

## State machine

`INTAKE → DISCOVERY → CONTRACTED → BASELINED → PLANNED → IMPLEMENTING → TESTING → ADVERSARIAL_REVIEW → AUDIT → AWAITING_HUMAN_APPROVAL → ACCEPTED`

Any active state may transition to `BLOCKED`, `CANCELLED`, or `REJECTED`. `ACCEPTED` is not synonymous with merged, released, or deployed.

## Required gates

### G0 — Intake

- preserve original request;
- identify target repo and requested outcome;
- record ambiguity and security sensitivity;
- no mutation.

### G1 — Discovery

- inspect repo state, existing docs, owners, CI, tests, dependencies;
- distinguish observed facts, declarations, hypotheses, unknowns;
- identify primary sources and upstream versions;
- produce a baseline map.

### G2 — Contract freeze

- task contract valid against JSON Schema;
- acceptance criteria approved;
- ownership/path boundaries and approval gates explicit;
- test design prepared before implementation.

### G3 — Baseline

- record base commit and clean/dirty tree;
- execute existing project checks where safe;
- save commands, environment, stdout/stderr, exit codes;
- no passing baseline? Record it; do not conceal it.

### G4 — Plan

- task DAG with dependencies and owners;
- identify parallelizable non-overlapping work;
- allocate attempt and resource budgets;
- assign reviewer before implementation.

### G5 — Implementation

- isolated branch/worktree;
- only paths in task scope;
- small commits; no secrets; no direct default-branch push;
- update tests and docs without weakening frozen acceptance.

### G6 — Verification

- unit, integration, contract, regression, security, performance, compatibility checks as applicable;
- execute from clean or documented environment;
- record failures and skipped tests;
- no inferred success from static inspection.

### G7 — Adversarial review

- challenge assumptions and acceptance coverage;
- search for lucky-pass behavior, blind retries, hidden test edits, false-positive tests, untested paths, and scope drift;
- review changed code and evidence, not only summary.

### G8 — Audit

- map each requirement to changed code and executed test;
- independently reproduce critical criteria;
- record verdict and residual risk.

### G9 — Human approval

- show exact diff, risk, checks, migrations, rollback, and effects;
- ask permission for merge/release/deploy/destructive operation;
- if approval absent, stop at PR-ready state.

## Retry semantics

Retries must be bounded and classified. Automatic retries are allowed only for transient, idempotent operations with an explicit policy. Never retry an uncertain non-idempotent operation until state has been reconciled.
