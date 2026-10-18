# ADR-0033 — Decree-Aware Agent Behavior

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** agent, decree, adaptation, v3.20.0
**Deciders:** @USER (Командир корабля)
**Extends:** [ADR-0024 Decree-Enforced Multi-Agent Communication](./0024-decree-enforced-multi-agent-communication.md)

## Context

Per ADR-0024, every Intent an agent sends through the `AgentMesh` is
checked against the human's decrees BEFORE execution. If a decree
prohibits the intent, the mesh returns a `DECREE_BLOCK` response and
the agent's `execute_fn` is never called. This is the unique emergent
СИНГУЛЯР property — no agent can bypass the decree gate.

But a `DECREE_BLOCK` was a **hard stop**. The agent's only option was
to surface the failure to the human and wait. This produces **agent
paralysis**:

- The human says "send the report to Cloudflare" → decree #N blocks
  the term `cloudflare` → agent stops.
- The agent knows the **specific term** that triggered the block
  (`matched_term: 'cloudflare'`), but does nothing with that
  information.
- The human has to manually rewrite the request and resubmit.

This is sub-optimal for two reasons:

1. The decree doesn't prohibit the *goal* ("send the report"); it
   prohibits the *means* ("Cloudflare"). The agent could achieve the
   goal via a non-prohibited channel (e.g. Fastly, or local file).
2. The DECREE_BLOCK response already carries the structured information
   the agent needs to adapt: `matched_term`, `decree_seq`,
   `decree_text`. We're throwing it away.

The gap: **agency within the law**. The decree is supreme (PAROLE >
LANGUE per ADR-0021), but the agent should not be paralyzed by a
single block — it should learn which specific term triggered the block
and retry with a modified description that still serves the human's
goal but doesn't violate the decree.

## Decision

Implement **Decree-Aware Agent Behavior** as a thin orchestration layer
on top of `AgentMesh` (ADR-0024). The new class
`runtime/src/decree_aware_agent.py::DecreeAwareAgent`:

- **Wraps** an existing agent in the mesh (by `agent_id`).
- **Proposes** an Intent → if `DECREE_BLOCK`, **records the violation**
  and **adapts** the description to avoid the matched term.
- **Retries** the adapted description through the same decree gate.
- **Stops** when (a) an adaptation passes the gate, (b) `max_retries`
  is exhausted, or (c) adaptation produces no further change.

### Public API

```python
agent = DecreeAwareAgent(mesh, "singulyar-eir.local", llm_adapter=my_llm)

# One-shot: propose + record violation + suggest adaptation (no retry)
result = agent.propose(
    description="send the report to Cloudflare",
    operation="storage.write",
    payload={"data": report_bytes},
)
# result == {
#     "state": "DECREE_BLOCKED",
#     "blocked": True,
#     "violations": [{"decree_seq": 2, "matched_term": "cloudflare", ...}],
#     "adaptations": ["send the report to [redacted]"],  # or LLM-suggested
# }

# Full loop: original → adapt → retry → adapt → retry → ...
result = agent.propose_with_adaptation(
    description="send the report to Cloudflare",
    operation="storage.write",
    payload={"data": report_bytes},
    max_retries=3,
)
# result["blocked"] == False after one adaptation
# result["adaptation_history"] == [
#     {"attempt": 1, "description": "send the report to Cloudflare", "blocked": True, ...},
#     {"attempt": 2, "description": "send the report to [redacted]", "blocked": False, ...},
# ]
```

### Adaptation strategies

Two paths, depending on whether an `llm_adapter` is attached:

1. **LLM-available path** — when an `llm_adapter` is provided, the
   agent asks the LLM for an alternative description:
   ```
   The intent '{description}' was blocked by decree #{seq} ({matched_term}).
   Suggest an alternative that avoids '{matched_term}'.
   ```
   The LLM is treated as an oracle — it can produce semantically
   equivalent alternatives ("send the report to Fastly" instead of
   "send the report to Cloudflare"). Supported adapter shapes:
   - a callable `(prompt: str) -> str`
   - an object with `.generate(prompt)` / `.answer(prompt)` methods

2. **No-LLM path** — when no `llm_adapter` is attached, the agent
   falls back to **simple string replacement**: remove the matched
   term (case-insensitive regex) and substitute a generic placeholder
   (`[redacted]`). If the entire description was the matched term,
   return a generic alternative (`"perform a compliant alternative
   action"`). This is the "dumb" path — it guarantees progress but may
   produce a less natural alternative.

In both paths, the adapted description is **re-submitted through the
same decree gate** — the decree is supreme, the agent's adaptation
must still pass it. If the adapted description is ALSO blocked (e.g.
a multi-term prohibition like "never use Google DNS" blocking both
`google` and `dns`), the agent adapts AGAIN, up to `max_retries`.

### Decree supremacy preserved

The agent's adaptation **never** bypasses the decree gate. It is not a
loophole. The decree remains the supreme law (PAROLE > LANGUE per
ADR-0021); the agent's adaptation simply produces a new description
that must independently pass the same gate. If no compliant
alternative is found within `max_retries`, the agent gives up
(`state: DECREE_BLOCKED`) — never violates the decree.

This is fundamentally different from "trying to work around the law":
the agent is **shaped by** the decree, not **resistant to** it. The
decree tells the agent which means are prohibited, and the agent
chooses among the remaining permitted means.

## Consequences

**Positive:**

- **Closes the agent-paralysis gap** — a single DECREE_BLOCK no longer
  stops the agent; it can adapt and retry.
- **Uses the structured DECREE_BLOCK data** that was already being
  emitted by the mesh (matched_term, decree_seq) but ignored.
- **Decree supremacy preserved** — adaptation re-passes the same gate;
  no backdoor.
- **Pluggable intelligence** — the `llm_adapter` parameter lets the
  agent use any LLM (local llama-cpp-python, remote, mock for tests).
  When no LLM is available, simple string replacement still works.
- **Auditable** — every adaptation is recorded in
  `agent.violation_history` and `agent.adaptation_history` for forensic
  review (per ADR-0019 observability-first).
- **Composes with existing ADRs** — ADR-0024 (mesh), ADR-0021
  (decree supremacy), ADR-0029 (compartmentalization via clearance_level)
  are all preserved. This ADR is purely additive — a new orchestration
  layer above `AgentMesh.send()`.

**Negative:**

- **Adaptation is syntactic, not semantic** in the no-LLM path —
  replacing `cloudflare` with `[redacted]` produces a description that
  passes the decree gate but doesn't actually route the report anywhere
  useful. The agent's `execute_fn` will be called with a description
  containing `[redacted]` — downstream consumers must handle this
  placeholder (e.g. log a warning, ask the human for clarification).
- **Multi-term prohibitions may need multiple adaptations** — "never
  use Google DNS" blocks both `google` and `dns`. The first adaptation
  removes `google`; if the description also contained `dns`, the second
  adaptation removes `dns`. This works (the loop handles it), but uses
  more retries.
- **LLM may produce a non-compliant alternative** — the LLM might
  suggest "send to Google Cloud" as an alternative to "send to
  Cloudflare" — still contains the prohibited term. The implementation
  handles this by **post-filtering**: if the LLM output still contains
  the matched_term, it falls back to simple replacement on top of the
  LLM output.
- **No semantic understanding of the decree's intent** — the agent
  only knows the matched_term, not the decree's *purpose*. A decree
  "never use proprietary DNS" might block `google` but the agent
  doesn't know it's about proprietary-ness, so its adaptation
  ("[redacted]") doesn't address the underlying concern. An LLM
  mitigates this (it can reason about the decree text in the prompt),
  but the no-LLM path is purely syntactic.

**Neutral:**

- The `max_retries` parameter defaults to 3 — enough for typical
  multi-term prohibitions, low enough to bound runtime. The agent
  gives up cleanly (returns `DECREE_BLOCKED` with the full history)
  rather than looping forever.

## Alternatives considered

### 1. Hard-stop on DECREE_BLOCK (status quo before ADR-0033)

The mesh returns DECREE_BLOCK and the agent surfaces it to the human.

**Rejected:** produces agent paralysis. The decree already provides
structured information (matched_term, decree_seq) that the agent can
act on. We should use it.

### 2. Ask the human to rewrite the intent

When DECREE_BLOCK fires, the agent asks the human to rewrite the
description.

**Rejected:** defeats the purpose of autonomy. The human already
issued the decree (the metalevel); asking them to also rewrite every
blocked intent is the same work twice. The agent should adapt within
the law, only escalating to the human when adaptation fails.

### 3. Generate the adapted description at decree-issue time

When the human issues a decree "never use Cloudflare", they also
specify the alternative ("use Fastly instead"). The decree stores the
alternative; on DECREE_BLOCK the agent uses it directly.

**Rejected:** violates ADR-0021 (decree is the human's raw expression,
not a code spec). It also requires the human to anticipate every
context in which the decree might fire — exactly the work the agent
should do. Decrees remain pure prohibitions; the agent finds the
alternative.

### 4. Semantic adaptation via decree-aware LLM fine-tuning

Fine-tune an LLM on the decree corpus so it can suggest
semantically-aligned alternatives ("Cloudflare prohibited → use Fastly,
which serves the same purpose but isn't on the decree list").

**Deferred:** this is the natural v2 of ADR-0033. The current
`llm_adapter` API already supports plugging in such an LLM — the
prompt we send ("The intent X was blocked by decree #N (term). Suggest
an alternative that avoids 'term'.") is LLM-agnostic. A future
decree-aware LLM can be dropped in without code changes. For v1, the
simple callable-LLM + string-replacement fallback is sufficient.

## Verification

- `runtime/tests/test_decree_aware_agent.py` — 4 tests:
  1. `test_propose_passes_when_compliant` — clean intent passes, no
     violation recorded, no adaptation produced.
  2. `test_propose_blocked_records_violation` — prohibited intent
     returns DECREE_BLOCKED, violation recorded with correct
     `matched_term` and `decree_seq`, simple-replacement adaptation
     suggested.
  3. `test_adapt_removes_prohibited_term` — `adapt()` output does not
     contain the matched term (case-insensitive).
  4. `test_propose_with_adaptation_retries` — full retry loop:
     original blocked, adaptation passes, `adaptation_history` has 2
     entries, `attempts == 2`.
- `make verify` check 01 (SINGULYAR EIR tests) — still passes (this
  ADR is additive; no existing test is modified).
- Manual: issue a decree "never use Cloudflare", construct a
  `DecreeAwareAgent`, call `propose_with_adaptation("send to
  Cloudflare", ...)` — verify it adapts to "send to [redacted]" and
  the second attempt passes the gate.

## References

- [ADR-0024 Decree-Enforced Multi-Agent Communication](./0024-decree-enforced-multi-agent-communication.md)
  — the parent ADR. Defines `AgentMesh.send()`, `IntentRequest`,
  `DECREE_BLOCK` response format. ADR-0033 is a thin orchestration
  layer above `AgentMesh.send()`.
- [ADR-0021 Decree as Supreme Law](./0021-decree-as-supreme-law.md) —
  PAROLE > LANGUE. The decree's supremacy is preserved: adaptation
  must re-pass the same gate.
- [ADR-0029 СИНГУЛЯР Security Model](./0029-singulyar-security-model-corporate-synthesis.md)
  — Microsoft "Conditional Access" mapping: `check_compliance()` is
  the conditional access check. ADR-0033 extends this from "block or
  pass" to "block, adapt, retry" — still conditional access, with the
  agent as an active participant rather than a passive subject.
- [ADR-0019 Observability-First](./0019-observability-first.md) — every
  adaptation is recorded in `violation_history` and
  `adaptation_history` for forensic review.
- [ADR-0015 Real LLM Inference in CI](./0015-real-llm-inference-in-ci.md)
  — the `llm_adapter` parameter is the seam where real LLM inference
  plugs in. Currently most tests use the no-LLM path; the LLM path is
  exercised via mock callables in unit tests.
- `runtime/src/decree_aware_agent.py` — implementation
- `runtime/tests/test_decree_aware_agent.py` — tests
- `runtime/src/agent_mesh.py` — `AgentMesh.send()` is the underlying
  decree gate; ADR-0033 wraps it, never bypasses it.

## Self-reference

This ADR itself can be superseded by a future decree-driven amendment
(per ADR-0026). For example, a decree "ADR-0033 must use a
decree-aware LLM for adaptation, not string replacement" would amend
this ADR's "no-LLM path" to be deprecated. The implementation would
then require `llm_adapter` to be non-None.
