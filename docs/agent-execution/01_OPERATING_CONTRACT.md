# 01 — Operating Contract

## 1. Human control

The human defines goal, constraints, forbidden actions, and approval boundaries. Agents may propose changes to the plan but may not change the human-approved goal or authorization level. A tool being technically available does not mean its use is authorized.

## 2. Separation of duties

For non-trivial tasks, separate these responsibilities:

- task owner / orchestrator;
- investigator or researcher;
- architect / spec author;
- implementer;
- test engineer;
- adversarial reviewer;
- independent auditor;
- human release approver.

One runtime may host multiple roles for low-risk work, but role labels do not create independence. A reviewer is independent only if it receives the frozen task contract, baseline, diff, and evidence without relying on the implementer's self-assessment, and has a distinct execution context. Prefer a different model family or human reviewer for high-risk changes.

## 3. Evidence before confidence

Every material claim must point to evidence. Evidence has a type, origin, timestamp, relevant commit/file/line or run ID, and limitations. Citation count is not source independence. Copies of one source remain one origin lineage.

## 4. No self-amending acceptance

After implementation begins, the implementer must not weaken acceptance criteria, remove failing tests, edit expected values to make a result pass, or alter the test environment to hide a failure. If the contract is wrong, stop and raise a change request; a separate owner approves and versions the revised contract.

## 5. Bounded repair

After baseline, allow at most two focused repair iterations per finding. Each iteration records hypothesis → patch → test → result. If still failing, stop, revert or isolate the patch, and escalate with evidence. No blind retries.

## 6. Smallest correct change

Inspect the owning layer and root cause before editing. Avoid broad refactors, new frameworks, duplicate cleanup loops, and cross-repo moves unless the task requires them and the contract authorizes them.

## 7. Honest status

Use `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, or `UNKNOWN`. `PASS` requires an executed acceptance check. `PARTIAL` is not a substitute for listing failed and unrun checks. A green test suite does not prove requirements not covered by tests.

## 8. Completion

A task is complete only when implementation, verification, independent review, evidence record, documentation, and human approval requirements are satisfied. A PR opened is not a merge; a merge is not a deployment; a deployment is not proof of successful operation.
