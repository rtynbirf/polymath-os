# 11 — Agent Runbook

## Session bootstrap

1. Identify repository root and branch.
2. Read root instructions and task-specific docs.
3. Run `git status --short --branch` and record cleanliness.
4. Read recent history and inspect related code/tests/docs.
5. Confirm exact task contract, authorized paths/tools, and approval tier.
6. Identify build/test commands from repository files or existing CI. If unknown, report `UNKNOWN`; do not invent.

## Research handoff format

Return:
- question and scope;
- source URL/title/publisher/date/access date;
- source class (primary specification, implementation source, paper, secondary analysis, search index);
- exact claim supported;
- quoted span or location where permitted;
- provenance/dependencies between sources;
- what the source does NOT establish;
- contradictions and `UNKNOWN`.

## Implementation handoff format

Return:
- task ID and base/head commit;
- patch summary and changed paths;
- design choice and alternatives rejected;
- commands executed with exit codes;
- tests added/changed and why;
- known limitations;
- security implications;
- rollback procedure;
- evidence IDs.

## Reviewer checklist

- Does diff solve the contracted problem at the owning layer?
- Any scope drift, unrelated refactor, dead code, duplicate abstraction?
- Any acceptance/test oracle weakening?
- Any untrusted input reaching shell, SQL, template, filesystem, or tool calls without validation?
- Are permissions, secrets, egress, and logs safe?
- Are failure, retry, cancellation, idempotency, and recovery defined?
- Can a clean environment reproduce the results?
- Do claims match actual code and test output?

## Final report

Use concise table: criterion | evidence | result | gap. State `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, or `UNKNOWN` per criterion. Include residual risk and whether human approval is required.
