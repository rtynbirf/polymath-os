# 02 — Task Contract

Every task larger than a trivial one-line change MUST have a machine-readable contract (`task.json`, schema `schemas/agent-execution/task.schema.json`).

## Required fields

- stable `task_id`, optional `parent_task_id`;
- original human request, preserved verbatim or linked to source;
- goal and explicit non-goals;
- target repositories, branches, paths, and allowed tools;
- constraints, compatibility requirements, and security classification;
- baseline commit and known state;
- acceptance criteria written as observable outcomes;
- tests, including negative/adversarial cases;
- budget: attempts, time/compute if known, maximum repair iterations;
- allowed actions and approval gates;
- outputs and required evidence;
- stop conditions.

## Writing acceptance criteria

Each criterion must be:

1. observable rather than aspirational;
2. testable with a named method or explicit manual protocol;
3. scoped to the task;
4. falsifiable;
5. independent of the implementation's chosen internal mechanism unless the mechanism is itself a requirement.

Bad: "make the agent robust".  
Good: "when tool execution returns timeout, the task enters RETRY_WAIT, does not duplicate a non-idempotent action, and emits one run event with timeout classification; contract test X verifies this."

## Task classes

- `research`: no repository mutation; source and evidence report.
- `design`: specs/ADRs only; no runtime code.
- `implementation`: scoped code change on branch/worktree.
- `verification`: execute tests/audits; do not modify implementation.
- `security`: threat model and authorized security checks; no exploit outside a controlled target.
- `release`: build/sign/publish/deploy only with explicit human approval.

## Change-control rules

A material scope change creates a new task revision. Preserve previous contract and decision; do not overwrite history. Missing required input is `BLOCKED`, not guessed. For low-risk reversible details, the task owner may use documented defaults and mark them as assumptions.
