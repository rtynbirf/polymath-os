# 03 — Proposed System Architecture

**Status: PROPOSED.** This is a target architecture, not a claim about current `polymath-os` implementation.

## Logical planes

1. **Human control plane** — goal, policy, permissions, approvals, stop/cancel, release decision.
2. **Task/control plane** — task graph, state machine, scheduler, ownership, deadlines, budgets, retries, cancellation.
3. **Agent execution plane** — specialized agents running in isolated workspaces with explicit role, model/provider identity, tool set, and token/compute budget.
4. **Tool/capability plane** — typed tools exposed through narrow adapters; per-tool authorization and input/output validation.
5. **Knowledge/evidence plane** — task contracts, repository maps, source material, claims, evidence lineage, decisions, run records.
6. **Artifact plane** — source changes, tests, build outputs, reports, SBOMs, attestations, releases.
7. **Observability plane** — event log, traces, cost/latency, tool calls, failures, retries, policy denials, and state transitions.

## Control flow

`HumanIntent → TaskContract → Baseline → Plan/DAG → ScopedExecution → Verification → IndependentReview → HumanReleaseGate → Result`

The flow is not allowed to skip baseline, verification, or required approval gates. Research and implementation branches can run in parallel only when their inputs and owned paths are independent.

## Agent cell boundary

Each cell MUST have:

- immutable `agent_id` and task/run IDs;
- declared role and capability manifest;
- model/provider/version metadata when available (otherwise `UNKNOWN`);
- isolated working directory or git worktree;
- explicit read/write path allowlist;
- scoped credentials supplied out-of-band and short-lived where possible;
- bounded tool, token, time, and retry budgets;
- structured input/output envelope;
- cancellation and timeout behavior;
- event trace and artifact manifest;
- no inherited ambient credentials unless explicitly required.

## Contracts before frameworks

Do not select a multi-agent framework solely because it is popular. First define task, event, artifact, capability, provenance, cancellation, and approval contracts. Then compare candidate runtimes against those contracts with a small benchmark. Keep adapters replaceable.

## Failure domains

The failure of one agent, model endpoint, tool server, machine, or repository must not silently corrupt the task state. Use idempotency keys for repeatable operations, explicit handling for non-idempotent actions, durable run state, and recovery from a recorded checkpoint.
