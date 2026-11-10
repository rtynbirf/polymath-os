# 08 — Testing and Agent Evaluation

## Test pyramid for agent-produced changes

1. **Static checks:** format, lint, typecheck, schema validation, dependency policy.
2. **Unit tests:** deterministic local logic.
3. **Contract tests:** API/event/schema compatibility between components.
4. **Integration tests:** real component boundaries with controlled dependencies.
5. **End-to-end tests:** user-visible workflows and recovery.
6. **Security tests:** secret scanning, permission checks, injection boundaries, dependency checks.
7. **Performance/reliability:** latency, memory, throughput, timeouts, cancellation, crash recovery.
8. **Independent acceptance:** tests unknown to the implementer when feasible; frozen evaluation fixtures.

## Avoid lucky PASS

A patch passing tests is not enough to assess the process. Record trajectory-quality signals:

- tests run before and after implementation;
- blind retries and repeated identical failures;
- test/fixture/oracle edits;
- sequence of exploration, implementation, and verification;
- scope drift and unrelated file changes;
- missing reproduction or undocumented environment mutation;
- reliance on network state or mutable external services.

Research such as AgentLens identifies passing trajectories that still contain poor engineering process (e.g., blind retries, regression cycles, missing verification). Therefore evaluate process as well as final outcome.

## Frozen oracle

Acceptance criteria and baseline tests are frozen before implementation. New tests may be added, but a failure cannot be removed or weakened by the implementer. If requirements change, issue a new task revision and preserve the old contract and run results.

## Required test record

Record exact command, cwd, OS/runtime/tool versions, dependency lock state, environment variables by name only (never values), start/end times, base/head commit, exit code, stdout/stderr paths or redacted excerpts, and known nondeterminism.

## Flaky and probabilistic behavior

For non-deterministic agents, define number of trials, seeds where possible, success distribution, confidence interval or uncertainty description, failure taxonomy, and budget. One successful run does not establish reliability.

## Verdicts

- `PASS`: all required acceptance checks executed and passed; required independent review passed.
- `FAIL`: one or more required checks fail.
- `BLOCKED`: unable to run/check due to missing access, environment, data, or approval.
- `NOT_RUN`: deliberately not executed; explain why.
- `UNKNOWN`: insufficient evidence to classify.

Do not average away critical failures. A critical false PASS blocks the release candidate.
