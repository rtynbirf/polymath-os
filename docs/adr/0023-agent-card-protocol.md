# ADR-0023: Agent Card Protocol (.well-known/agent.json)

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** layer-2, agent-stack, mcp, a2a, v3.10.0

## Context

Per the v3.10.0 release (2026-10-17), Polymath OS needs to participate in the emerging **Agent-to-Agent (A2A) protocol ecosystem** that has crystallized in 2026 (Google A2A, 50+ partners: Salesforce, Accenture, MongoDB, Langchain; complementing Anthropic's MCP at 97M downloads).

The key discovery mechanism in A2A is the **Agent Card** — a JSON document exposed at a well-known endpoint (`.well-known/agent.json`) that describes:
- Agent identity (`id`, `name`, `description`)
- Capabilities (`operations` — what this agent can do)
- Decree scope (which decrees apply to this agent — Polymath-OS extension)
- Transport (`endpoints` — HTTP, WebSocket, WebRTC)
- Authentication (`auth` — what credentials the agent accepts)
- Versioning (`version`, `protocol_version`)

Without an Agent Card, Polymath-OS agents cannot:
1. Be discovered by other A2A-compatible agents (external systems, multi-agent research workflows)
2. Discover other agents that could collaborate on Intents
3. Advertise their decree scope (so callers know which decrees apply BEFORE issuing an Intent)
4. Participate in the broader 2026 sovereign agent ecosystem

## Decision

Polymath OS will adopt the **Agent Card Protocol** as defined by the A2A ecosystem, with **Polymath-OS-specific extensions** for decree enforcement.

### Agent Card schema (JSON)

Located at `.well-known/agent.json` (for HTTP-discoverable agents) OR embedded in the Agent class (for in-process agents).

```json
{
  "$schema": "https://polymath-os.local/schemas/agent-card.json",
  "id": "singulyar-eir.local",
  "name": "SINGULYAR EIR",
  "description": "Execution kernel — preserves intent across executor changes; enforces human decrees before policy",
  "version": "v0.6",
  "protocol_version": "a2a/1.0 + mcp/1.0",
  "capabilities": [
    "intent.execute", "intent.recover", "intent.cancel",
    "evidence.query", "decree.check_compliance"
  ],
  "decree_scope": "all",
  "endpoints": [
    {"type": "http", "url": "https://polymath.local/agent/singulyar"},
    {"type": "webrtc", "offer": "DATA_CHANNEL:polymath-agent"}
  ],
  "auth": {
    "type": "decree",
    "description": "All requests checked against DecreeLog before execution"
  },
  "maintainer": "rtynbirf",
  "license": "MIT",
  "homepage": "https://github.com/rtynbirf/polymath-os"
}
```

### Polymath-OS-specific extensions

Standard A2A doesn't include `decree_scope` — we add it because:
1. Callers need to know which decrees apply BEFORE issuing an Intent (otherwise they hit decree blocks)
2. Different agents have different decree scopes (e.g., `singulyar` vs `polymath-os` vs `cell65-host`)
3. The decree scope is part of the **contract** — it's not just runtime info

### Implementation

- `runtime/src/agent_card.py` — `AgentCard` class with `from_dict()`, `to_json()`, `validate()` methods
- `runtime/tests/test_agent_card.py` — schema validation tests
- `runtime/schemas/agent-card.schema.json` — JSON Schema for validation
- `.well-known/agent.json` — root-level Agent Card for the SINGULYAR EIR agent

## Consequences

**Positive:**
- Polymath-OS agents become discoverable by any A2A-compatible client
- Decree scope is part of the agent's contract — no surprises for callers
- Aligns with 2026 industry direction (Google A2A, Anthropic MCP, 97M+ downloads)
- Foundation for ADR-0024 (Decree-Enforced Multi-Agent Communication)

**Negative:**
- Adds new dependency: A2A-compatible clients must understand `decree_scope` extension (or ignore it — backward compatible)
- Agent Card must be kept in sync with actual capabilities (or callers get confused)

**Neutral:**
- Agent Card is static (per-agent, doesn't change between requests) — fits naturally with the immutable ADR pattern

## References

- [Google A2A Protocol](https://github.com/google/A2A) — 50+ partners
- [Anthropic MCP](https://modelcontextprotocol.io) — 97M downloads (already integrated in polymath-os as `tooling/agents/mcp/`)
- ADR-0008: MCP version pin
- ADR-0021: Decree as supreme law
- ADR-0024 (next): Decree-Enforced Multi-Agent Communication
