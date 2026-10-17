# ADR-0024: Decree-Enforced Multi-Agent Communication (A2A + Decree Gate)

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** layer-2, layer-5, agent-stack, a2a, decree, v3.10.0

## Context

The 2026 agent ecosystem has crystallized around two complementary protocols:
- **MCP** (Anthropic) — agent-to-tool: how an agent calls external services (97M downloads, dominant)
- **A2A** (Google) — agent-to-agent: how agents discover each other and delegate tasks (50+ partners)

Polymath OS already has MCP (ADR-0008). What's missing is **A2A-style inter-agent communication** — and critically, a Polymath-OS-specific extension that no other agent system has:

> **Every inter-agent message is checked against the human's decrees BEFORE execution.**

In standard A2A, agents communicate freely — they trust each other (or use OAuth/SCopes for auth). In Polymath OS, the human's decrees are the supreme law layer (ADR-0021). Any inter-agent communication that violates a decree MUST be blocked — even if both agents consent.

**Example scenario:**
- Agent A (Singulyar EIR) issues an Intent: "send user data to Google Cloud Storage"
- Agent B (storage adapter) receives the request and would normally execute it
- BUT the human has decree #3 "never use Google DNS" (extends via head noun "google" to any Google service)
- The decree gate (already in `_advance()` per ADR-0021) catches this and blocks the Intent
- Agent B receives `DECREE_BLOCK` event instead of executing the side-effect

This is the **unique emergent property** of Polymath OS: **decree-enforced multi-agent system** where the human's will is supreme over agent autonomy.

## Decision

Polymath OS will implement **Decree-Enforced Multi-Agent Communication** with three layers:

### Layer 1: Agent Discovery (ADR-0023 — Agent Card Protocol)
- Each agent publishes an Agent Card at `.well-known/agent.json` (or in-process equivalent)
- Agent Cards include `decree_scope` field — callers know which decrees apply BEFORE issuing an Intent

### Layer 2: Decree-Enforced Intent Routing
- When Agent A sends an Intent to Agent B, Agent B's runtime calls `check_compliance(intent.description, scope=agent_b.decree_scope)` BEFORE policy
- If decree violations → return `DECREE_BLOCK` response to Agent A (no side-effect occurs)
- Agent A may NOT retry with modified description (decrees are immutable law)
- Agent A may petition the human (via Decree Portal) to issue a new decree — `permission` category

### Layer 3: Evidence Ledger as Audit Trail
- Every inter-agent message is recorded in the Evidence Ledger (already implemented)
- `DECREE_BLOCK` events are recorded with full context (which agent blocked, which decree fired, which term matched)
- This creates a complete audit trail of decree enforcement — useful for:
  - Compliance reporting
  - Debugging (why was this intent blocked?)
  - Sovereignty drills (replay scenarios with different decrees)

### Protocol extension (A2A + Decree)

Standard A2A message format:
```json
{
  "jsonrpc": "2.0",
  "method": "intent.execute",
  "params": {
    "intent_id": "...",
    "description": "...",
    "operation": "...",
    "payload": {...}
  },
  "id": "..."
}
```

Polymath-OS extension:
```json
{
  "jsonrpc": "2.0",
  "method": "intent.execute",
  "params": {
    "intent_id": "...",
    "description": "...",
    "operation": "...",
    "payload": {...},
    "decree_scope": "singulyar"
  },
  "id": "..."
}
```

Response (when decree blocks):
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "DECREE_BLOCK: intent violates decree #3 'never use Google DNS' (matched term: google)",
    "data": {
      "decree_seq": 3,
      "decree_text": "never use Google DNS",
      "matched_term": "google",
      "laws_checked": 7
    }
  },
  "id": "..."
}
```

### Implementation

- `runtime/src/agent_mesh.py` — `AgentMesh` class for managing local agent registry
  - `register(agent_card)` — add agent to mesh
  - `discover(capability)` — find agents with a given capability
  - `send(agent_id, intent, scope=None)` — route Intent to agent, returns DECREE_BLOCK or result
- `runtime/tests/test_agent_mesh.py` — multi-agent decree enforcement tests
- Wire into `Runtime.run()` as the standard execution path when intent.target_agent is set

## Consequences

**Positive:**
- **UNIQUE EMERGENT PROPERTY** — no other agent system has decree-enforced multi-agent communication. This is the СИНГУЛЯР (singular) property of Polymath OS.
- Aligns with 2026 sovereign AI trend (Cohere + Aleph Alpha, enterprise sovereignty)
- Full audit trail in Evidence Ledger
- Composes naturally with ADR-0021 (decree as supreme law) and ADR-0023 (Agent Card)

**Negative:**
- Adds complexity — agents must understand decree_scope (or default to "all" scope — backward compatible)
- Slower than standard A2A (decree check is O(n) in number of active laws)
- Some Intents may be blocked that the user didn't expect — but this is the POINT of decrees

**Neutral:**
- Backward compatible with v0.6 check_compliance — `scope=None` defaults to "all decrees apply"

## The emergent СИНГУЛЯР property

When you combine:
1. **Decree Log** (human's supreme law, append-only, hash-chained)
2. **Runtime with decree gate** (already in `_advance()` per ADR-0021)
3. **Agent Card Protocol** (ADR-0023 — discovery with decree scope)
4. **Multi-agent mesh** (this ADR — decree-enforced routing)

You get a system where:
- Agents can be local (cell65-llm) or remote (any A2A-compatible)
- The human's word is law — agents cannot collude to bypass it
- All actions are auditable
- Sovereignty is preserved end-to-end

**This is what makes Polymath OS singular.** Not the sum of parts — the emergent property that arises when you combine local-first execution, agent-to-agent protocols, and supreme law layer.

## References

- [Google A2A Protocol](https://github.com/google/A2A)
- ADR-0008: MCP version pin (agent-to-tool)
- ADR-0021: Decree as supreme law
- ADR-0023: Agent Card Protocol (.well-known/agent.json)
- ADR-0019: Observability-first (Evidence Ledger as audit trail)
- MANIFESTO.md: PAROLE > LANGUE (individual word above collective agreement)
