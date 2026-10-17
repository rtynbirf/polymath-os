# ADR-0025: Decree-Driven A2A Client (Outbound Decree Gate)

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** layer-2, layer-5, agent-stack, a2a, decree, v3.11.0

## Context

ADR-0024 established **inbound** decree enforcement — when an Agent B receives an Intent from Agent A, Agent B's runtime checks the Intent against decrees before executing.

But the decree system is asymmetric without an **outbound** gate. Consider:
- Agent A composes an Intent: "send user PII to marketing-provider.external"
- Agent A's own decree_scope might not cover marketing-provider
- Agent A sends the Intent to Agent B (external marketing provider)
- Agent B's decree gate fires → DECREE_BLOCK
- **But Agent A already disclosed the PII in the message payload!**

The decree gate at Agent B is too late — the data was already sent over the wire. The decree system needs an **outbound gate** at the source.

## Decision

Polymath-OS will implement a **Decree-Driven A2A Client** — when polymath-os acts as a CLIENT to external A2A-compatible agents, the client-side runtime checks the Intent against decrees BEFORE sending the request.

### Two-tier decree enforcement

```
┌──────────────────────────────────────────────────────────────┐
│ Agent A (Polymath-OS)                                        │
│                                                              │
│   1. Compose Intent                                          │
│   2. OUTBOUND decree gate (NEW — ADR-0025)                   │
│      check_compliance(intent.description, scope="outbound")  │
│      if violation → block locally, no network request       │
│   3. Send to Agent B via a2a_client.send()                  │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼ (over the wire)
┌──────────────────────────────────────────────────────────────┐
│ Agent B (external A2A server)                                │
│                                                              │
│   4. INBOUND decree gate (if Polymath-OS — ADR-0024)        │
│      check_compliance(intent.description, scope=agent_b)    │
│      if violation → DECREE_BLOCK JSON-RPC response          │
│   5. execute_fn(intent)                                      │
└──────────────────────────────────────────────────────────────┘
```

### Implementation

- `runtime/src/a2a_client.py` — `A2AClient` class
  - `send(agent_url, intent_request)` — outbound decree gate + HTTP POST
  - `discover(agent_url)` — fetch Agent Card from `.well-known/agent.json`
  - `check_outbound(intent_description, scope="outbound")` — public method to pre-check
- `runtime/tests/test_a2a_client.py` — outbound decree gate tests
- Default `decree_scope` for outbound: `"outbound"` (allows human to issue decrees that apply only to outbound traffic, separate from inbound)

### Decree categories that matter for outbound

| Decree text | Why it matters at outbound |
|-------------|---------------------------|
| `never use Google DNS` (prohibition) | Even composing an Intent mentioning Google should be blocked — don't let the request leave the system |
| `never send PII to external services` (prohibition, scope=outbound) | Outbound-only — the human might allow PII within local agents but block external transmission |
| `always encrypt payloads to external agents` (law, scope=outbound) | Outbound payload encryption requirement — enforced at client side |
| `never use marketing-provider.external` (prohibition, scope=outbound) | Outbound-only — block specific external services |

## Consequences

**Positive:**
- **Symmetric decree enforcement** — both inbound (ADR-0024) and outbound (ADR-0025)
- **Pre-network blocking** — sensitive data never leaves the system
- **Outbound-specific decrees** — `scope="outbound"` lets the human express "this rule only applies to outgoing traffic" (PII, encryption, etc.)
- **Composable with ADR-0024** — A2AClient + AgentMesh = full decree-enforced multi-agent system

**Negative:**
- Adds latency (decree check before every network call)
- False positives at outbound could prevent legitimate traffic (but the human can amend decrees)
- Network errors might mask decree blocks (but we return DECREE_BLOCK_OUTBOUND locally before any network call)

**Neutral:**
- Backward compatible: `decree_log=None` on A2AClient → no outbound gate, just plain HTTP POST

## The СИНГУЛЯР property now has both directions

| Direction | Where | ADR | Status |
|-----------|-------|-----|--------|
| Inbound (Agent A → Polymath Agent B) | Runtime._advance() | ADR-0021 + ADR-0024 | ✓ v3.6.0+ |
| **Outbound (Polymath Agent A → External Agent B)** | A2AClient.send() | **ADR-0025 (this)** | **✓ v3.11.0** |

Combined with ADR-0023 (Agent Card) + ADR-0024 (inbound), Polymath-OS is now a fully symmetric decree-enforced multi-agent system.

## References

- ADR-0021: Decree as supreme law
- ADR-0023: Agent Card Protocol
- ADR-0024: Decree-Enforced Multi-Agent Communication (inbound)
- ADR-0019: Observability-first (outbound decree blocks also logged)
