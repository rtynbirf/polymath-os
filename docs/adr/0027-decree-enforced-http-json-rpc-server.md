# ADR-0027 — Decree-Enforced HTTP JSON-RPC Server

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** layer-2, layer-5, agent-stack, a2a, http, json-rpc, v3.13.0
**Deciders:** @USER
**Supersedes:** None

## Context

ADR-0023 (Agent Card Protocol) declares that SINGULYAR EIR is reachable
at `http://localhost:7654/agent/singulyar` (in `.well-known/agent.json`).
But there's no actual server listening there — the Agent Card declares
an endpoint that doesn't exist yet.

This makes the A2A-compatible discovery a half-truth: external A2A
clients can fetch the Agent Card, see the HTTP endpoint, send a
JSON-RPC request — and get a connection refused. The СИНГУЛЯР property
(decree-enforced multi-agent communication) is only operational for
in-process agents (AgentMesh) and outbound (A2AClient), not for
inbound-over-HTTP.

## Decision

Implement `AgentMeshServer` — an HTTP server based on Python stdlib
`http.server` that exposes the local AgentMesh via JSON-RPC 2.0 over
HTTP.

### Endpoints

- `GET /.well-known/agent.json` → serve the SINGULYAR_EIR_CARD (or
  whichever Agent Card is configured as the "host" agent for this
  server)
- `POST /agent/{agent_id}` → JSON-RPC 2.0 endpoint for sending
  Intents to the agent with that id (must be registered in the local
  AgentMesh)

### JSON-RPC 2.0 protocol

Request:
```json
{
  "jsonrpc": "2.0",
  "method": "intent.execute",
  "params": {
    "intent_id": "...",
    "description": "...",
    "operation": "...",
    "payload": {...},
    "decree_scope": null
  },
  "id": "request-id"
}
```

Response (success):
```json
{
  "jsonrpc": "2.0",
  "result": {"state": "CONFIRMED", ...},
  "id": "request-id"
}
```

Response (DECREE_BLOCK, per ADR-0024):
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "DECREE_BLOCK: intent violates decree #3 'never use Google DNS' (matched term: google)",
    "data": {
      "agent_id": "singulyar-eir.local",
      "decree_seq": 3,
      "matched_term": "google",
      "laws_checked": 7
    }
  },
  "id": "request-id"
}
```

### Implementation

- `runtime/src/agent_mesh_server.py` — `AgentMeshServer` class
  based on `http.server.BaseHTTPRequestHandler`
  - Constructor: `AgentMeshServer(mesh, host_card, port=7654, host="localhost")`
  - `start()` / `stop()` for non-blocking test mode
  - `serve_forever()` for production mode
- `runtime/tests/test_agent_mesh_server.py` — tests using
  `urllib.request` against a real running server (no mocking)
- CLI: `python3 -m runtime.src.agent_mesh_server --port 7654`

### Security considerations

- **Bind to localhost by default** — prevents external access without
  explicit configuration
- **Decree gate runs BEFORE execute_fn** — inbound HTTP requests go
  through the same decree gate as in-process AgentMesh calls (per
  ADR-0024)
- **CORS** — `Access-Control-Allow-Origin: *` for development only.
  Production deployments should restrict to known origins
- **Rate limiting** — out of scope for v3.13.0, target for v3.14.0
  via middleware
- **Authentication** — none in v3.13.0. Target for v3.14.0 via
  `Authorization: Bearer <token>` header

## Consequences

**Positive:**
- **Closes the A2A endpoint loop** — `.well-known/agent.json` now
  actually serves a real JSON-RPC endpoint
- **External A2A clients can register** — polymath-os becomes a
  real participant in the A2A ecosystem, not just a card issuer
- **Decree enforcement is symmetric over HTTP** — same DECREE_BLOCK
  response whether the Intent comes from in-process or over HTTP
- **Zero external dependencies** — uses Python stdlib `http.server`
  only

**Negative:**
- **No async** — `http.server` is synchronous. For high-throughput
  scenarios, switch to `aiohttp` or `uvicorn` (target v3.14.0)
- **No HTTPS** — localhost-only by default. Production needs reverse
  proxy with TLS
- **No WebSocket support** — JSON-RPC over HTTP only (WebSockets
  target v3.15.0)

**Neutral:**
- The HTTP server is optional — polymath-os still works fully without
  it (in-process AgentMesh + outbound A2AClient)

## Verification

- `runtime/tests/test_agent_mesh_server.py` — 10+ tests covering
  Agent Card serving, JSON-RPC dispatch, DECREE_BLOCK over HTTP,
  unknown agent 404, invalid JSON 400, etc.
- Manual: `python3 -m runtime.src.agent_mesh_server --port 7654`
  then `curl http://localhost:7654/.well-known/agent.json` returns
  the SINGULYAR_EIR_CARD JSON

## Alternatives considered

1. **aiohttp server** — rejected: adds external dependency. Use stdlib
   http.server for v3.13.0, migrate when needed.
2. **uvicorn + FastAPI** — rejected: same external dep concern, and
   adds ASGI complexity that's not needed yet.
3. **gRPC** — rejected: A2A ecosystem uses JSON-RPC, not gRPC.
   Adding gRPC would require protocol translation layer.

## References

- ADR-0023 (Agent Card Protocol) — declares the HTTP endpoint
- ADR-0024 (Decree-Enforced Multi-Agent Communication) — defines
  the DECREE_BLOCK JSON-RPC error format this server uses
- ADR-0025 (Decree-Driven A2A Client) — outbound counterpart;
  this ADR enables the inbound counterpart over HTTP
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
- [A2A Protocol (Google)](https://github.com/google/A2A) — uses
  JSON-RPC 2.0 over HTTP

## Self-reference

This ADR closes the loop declared by ADR-0023: `.well-known/agent.json`
now actually serves a working JSON-RPC endpoint. СИНГУЛЯР property
extends from in-process + outbound to **inbound-over-HTTP**.

Future amendments (per ADR-0026) may add:
- WebSocket transport
- HTTPS / TLS support
- Authentication middleware
- Rate limiting
- Multi-tenant support (multiple agents per server)
