"""runtime/src/agent_mesh_server.py — Decree-Enforced HTTP JSON-RPC Server (per ADR-0027).

AgentMeshServer exposes the local AgentMesh via JSON-RPC 2.0 over HTTP.
External A2A-compatible clients can:
  - GET /.well-known/agent.json → fetch the host Agent Card
  - POST /agent/{agent_id} → send a JSON-RPC IntentRequest to that agent

The decree gate (per ADR-0024) runs BEFORE execute_fn for every
inbound HTTP request, so external clients are subject to the same
DECREE_BLOCK enforcement as in-process agents.

Usage:
    from agent_mesh_server import AgentMeshServer
    from agent_mesh import AgentMesh
    from agent_card import SINGULYAR_EIR_CARD
    from decree_log import DecreeLog

    dl = DecreeLog("~/.polymath-os/decrees.db")
    mesh = AgentMesh(decree_log=dl)
    mesh.register(SINGULYAR_EIR_CARD, execute_fn=my_execute_fn)
    server = AgentMeshServer(mesh=mesh, host_card=SINGULYAR_EIR_CARD, port=7654)
    server.serve_forever()  # blocks

Or via CLI:
    python3 -m runtime.src.agent_mesh_server --port 7654
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# Allow running both as `python3 -m runtime.src.agent_mesh_server` and
# as `python3 runtime/src/agent_mesh_server.py` (for tests).
_RUNTIME_SRC = Path(__file__).resolve().parent
if str(_RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_SRC))

from agent_card import AgentCard, SINGULYAR_EIR_CARD  # noqa: E402
from agent_mesh import (  # noqa: E402
    AgentMesh, IntentRequest, IntentResponse,
    DECREE_BLOCK_ERROR_CODE,
)
from decree_log import DecreeLog  # noqa: E402


class AgentMeshRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler that serves the Agent Card and JSON-RPC endpoints."""

    # Set by AgentMeshServer.setup_handler() — class-level attributes
    # so BaseHTTPRequestHandler can access them via the singleton.
    mesh: Optional[AgentMesh] = None
    host_card: Optional[AgentCard] = None

    def log_message(self, format, *args):
        """Override to suppress default stderr logging (or route to a custom logger)."""
        # In production, route to OTel or similar. For v3.13.0, just
        # emit to stderr.
        import sys as _sys
        _sys.stderr.write(
            f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] "
            f"{self.client_address[0]} - {format % args}\n"
        )

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/.well-known/agent.json":
            self._serve_agent_card()
        elif parsed.path == "/health" or parsed.path == "/":
            self._serve_health()
        else:
            self._send_json_error(404, "NOT_FOUND", f"path {parsed.path} not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        # Expected: /agent/{agent_id}
        path_parts = parsed.path.strip("/").split("/", 1)
        if len(path_parts) == 2 and path_parts[0] == "agent":
            agent_id = path_parts[1]
            self._handle_jsonrpc(agent_id)
        else:
            self._send_json_error(404, "NOT_FOUND", f"path {parsed.path} not found")

    def _serve_agent_card(self):
        if self.host_card is None:
            self._send_json_error(503, "NO_HOST_CARD", "host Agent Card not configured")
            return
        try:
            card_json = self.host_card.to_json(indent=2)
        except Exception as e:
            self._send_json_error(500, "CARD_SERIALIZATION_ERROR", str(e))
            return
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = card_json.encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_health(self):
        body = json.dumps({
            "status": "ok",
            "mesh_agents": len(self.mesh.list_agents()) if self.mesh else 0,
            "host_card_id": self.host_card.id if self.host_card else None,
        }).encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_jsonrpc(self, agent_id: str):
        """Handle a JSON-RPC 2.0 request to /agent/{agent_id}."""
        if self.mesh is None:
            self._send_json_error(503, "NO_MESH", "AgentMesh not configured on server")
            return

        # Read the request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length else b""
        except (ValueError, OSError) as e:
            self._send_json_error(400, "INVALID_REQUEST", f"cannot read body: {e}")
            return

        # Parse JSON
        try:
            request_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except json.JSONDecodeError as e:
            self._send_jsonrpc_error(agent_id, None, -32700, f"Parse error: {e}")
            return

        if not isinstance(request_data, dict):
            self._send_jsonrpc_error(agent_id, None, -32600, "Invalid Request: not a JSON object")
            return

        # Validate JSON-RPC 2.0 envelope
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        if not method:
            self._send_jsonrpc_error(agent_id, request_id, -32600, "Invalid Request: missing 'method'")
            return

        # Build IntentRequest
        intent_request = IntentRequest(
            jsonrpc=request_data.get("jsonrpc", "2.0"),
            method=method,
            params=params if isinstance(params, dict) else {},
            id=str(request_id) if request_id is not None else "",
        )

        # Send to mesh — DECREE_BLOCK fires here (per ADR-0024)
        response = self.mesh.send(agent_id, intent_request)
        # Serialize response
        try:
            response_json = json.dumps(response.to_dict(), ensure_ascii=False)
        except Exception as e:
            self._send_jsonrpc_error(agent_id, request_id, -32603,
                                      f"response serialization failed: {e}")
            return

        body = response_json.encode("utf-8")
        if response.is_blocked():
            # DECREE_BLOCK → HTTP 403 (forbidden)
            self.send_response(403)
        else:
            self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        """Send CORS headers for development. In production, restrict origin."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json_error(self, http_status: int, code: str, message: str):
        """Send an HTTP-level JSON error (not JSON-RPC)."""
        body = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
        self.send_response(http_status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_jsonrpc_error(self, agent_id: str, request_id: Any, code: int, message: str):
        """Send a JSON-RPC 2.0 error response."""
        body = json.dumps({
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": request_id,
        }).encode("utf-8")
        self.send_response(400 if code == -32700 else 200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class AgentMeshServer:
    """HTTP server that exposes an AgentMesh via JSON-RPC 2.0 (per ADR-0027).

    Usage:
        server = AgentMeshServer(mesh=mesh, host_card=SINGULYAR_EIR_CARD, port=7654)
        server.serve_forever()  # blocks
    Or for testing:
        server.start()  # background thread
        # ... make requests ...
        server.stop()
    """

    def __init__(
        self,
        mesh: AgentMesh,
        host_card: AgentCard = None,
        port: int = 7654,
        host: str = "localhost",
    ):
        """Initialize the server.

        Args:
            mesh: AgentMesh instance with registered agents + decree_log
            host_card: AgentCard to serve at /.well-known/agent.json (default: SINGULYAR_EIR_CARD)
            port: HTTP port (default 7654)
            host: bind host (default "localhost" — bind to localhost only for security)
        """
        self.mesh = mesh
        self.host_card = host_card or SINGULYAR_EIR_CARD
        self.port = port
        self.host = host
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def _make_handler(self):
        """Create a handler class with mesh + host_card bound."""
        # Use type() to dynamically create a subclass with our config.
        # This is the standard pattern for BaseHTTPRequestHandler subclassing.
        mesh = self.mesh
        host_card = self.host_card

        class _BoundHandler(AgentMeshRequestHandler):
            pass

        _BoundHandler.mesh = mesh
        _BoundHandler.host_card = host_card
        return _BoundHandler

    def start(self) -> None:
        """Start the server in a background thread (non-blocking).

        Useful for tests. For production, use serve_forever() instead.
        """
        if self._httpd is not None:
            return  # already started
        handler = self._make_handler()
        self._httpd = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        # Brief sleep to ensure the server is listening before we return.
        time.sleep(0.05)

    def stop(self) -> None:
        """Stop the server (if started via start())."""
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._httpd = None
        self._thread = None

    def serve_forever(self) -> None:
        """Start the server and block (production mode)."""
        if self._httpd is not None:
            raise RuntimeError("server already started")
        handler = self._make_handler()
        self._httpd = HTTPServer((self.host, self.port), handler)
        try:
            print(f"AgentMeshServer listening on http://{self.host}:{self.port}")
            print(f"  Agent Card: http://{self.host}:{self.port}/.well-known/agent.json")
            print(f"  Health:     http://{self.host}:{self.port}/health")
            print(f"  JSON-RPC:   POST http://{self.host}:{self.port}/agent/<agent_id>")
            print(f"  Agents registered: {len(self.mesh.list_agents())}")
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


# ─── CLI ──────────────────────────────────────────────────────────────────

def _demo_execute_fn(request: IntentRequest) -> Dict[str, Any]:
    """Demo execute_fn for the CLI server — returns a canned response.

    For production, replace with real Runtime integration (see make_runtime_execute_fn).
    """
    return {
        "state": "CONFIRMED",
        "agent_id": "singulyar-eir.local",
        "intent_id": request.intent_id,
        "description": request.description,
        "operation": request.operation,
        "note": "demo execute_fn — use --use-runtime for real Runtime.run() integration",
    }


def make_runtime_execute_fn(decree_log=None, scope=None):
    """Factory: returns an execute_fn that calls the real SINGULYAR EIR Runtime.

    Per ADR-0027 §5 (v3.15.0): production deployments should use this instead of
    _demo_execute_fn. The Runtime is constructed with:
    - 1 Capability (operation 'send', adapter_id 'memory', risk 'low', idempotent True)
    - 1 MemoryAdapter
    - Policy({'send'}) — allows 'send' operation
    - decree_log attached (if provided) — decree gate fires BEFORE policy

    The execute_fn constructs an Intent from the request and calls rt.run(intent).
    Returns {"state": <State.value>, "intent_id": ..., "description": ..., ...}.
    """
    from singulyar_runtime import Runtime, Policy, Capability, Intent, State, MemoryAdapter

    caps = [Capability("c1", "send", "memory", "low", True, True)]
    rt = Runtime(
        capabilities=caps,
        adapters=[MemoryAdapter()],
        policy=Policy({"send"}),
        redaction_key=b"agent-mesh-server-v3.15.0",
    )
    if decree_log is not None:
        rt.set_decree_log(decree_log, scope=scope)

    def execute_fn(request: IntentRequest) -> Dict[str, Any]:
        # Build an Intent from the JSON-RPC request.
        intent = Intent(
            intent_id=request.intent_id or f"agent-mesh-{int(time.time() * 1000)}",
            description=request.description,
            operation=request.operation or "send",
            payload=request.payload or {},
            expected=request.payload or {},
        )
        try:
            state = rt.run(intent)
            return {
                "state": state.value if hasattr(state, "value") else str(state),
                "agent_id": "singulyar-eir.local",
                "intent_id": intent.intent_id,
                "description": intent.description,
                "operation": intent.operation,
                "note": "real Runtime.run() integration (v3.15.0+)",
            }
        except Exception as e:
            return {
                "state": "FAILED",
                "agent_id": "singulyar-eir.local",
                "intent_id": intent.intent_id,
                "error": f"{type(e).__name__}: {e}",
            }

    return execute_fn


def main(argv=None):
    """CLI entry point: python3 -m runtime.src.agent_mesh_server --port 7654"""
    parser = argparse.ArgumentParser(
        description="Polymath-OS Agent Mesh HTTP Server (ADR-0027)"
    )
    parser.add_argument(
        "--port", type=int, default=7654,
        help="HTTP port (default 7654)"
    )
    parser.add_argument(
        "--host", default="localhost",
        help="bind host (default 'localhost' — bind to localhost only for security)"
    )
    parser.add_argument(
        "--decree-db",
        default=os.path.expanduser("~/.polymath-os/decrees.db"),
        help="path to DecreeLog SQLite DB (default ~/.polymath-os/decrees.db)"
    )
    parser.add_argument(
        "--use-runtime", action="store_true",
        help="use real SINGULYAR EIR Runtime.run() instead of _demo_execute_fn (v3.15.0+ production mode)"
    )
    args = parser.parse_args(argv)

    # Open the decree log (if exists)
    decree_db = Path(args.decree_db).expanduser()
    if not decree_db.exists():
        print(f"⚠ Decree DB not found at {decree_db}", file=sys.stderr)
        print("  Run `python3 /home/z/my-project/scripts/issue_decrees.py` first to issue 7 foundational decrees.", file=sys.stderr)
        dl = None
    else:
        dl = DecreeLog(str(decree_db), check_same_thread=False)
        print(f"✓ DecreeLog opened: {decree_db} ({dl.count()} decrees)", file=sys.stderr)

    # Build the mesh
    mesh = AgentMesh(decree_log=dl)
    # v3.15.0: use real Runtime integration if --use-runtime flag is set
    if args.use_runtime:
        singulyar_exec_fn = make_runtime_execute_fn(decree_log=dl)
        print("✓ Using real SINGULYAR EIR Runtime.run() for singulyar-eir.local (v3.15.0+ production mode)", file=sys.stderr)
    else:
        singulyar_exec_fn = _demo_execute_fn
        print("⚠ Using _demo_execute_fn (canned response). Use --use-runtime for real Runtime.run().", file=sys.stderr)
    mesh.register(SINGULYAR_EIR_CARD, singulyar_exec_fn)
    # Also register the other default cards (all use the demo execute_fn)
    from agent_card import POLYMATH_OS_BROWSER_CARD, CELL65_LLM_CARD
    mesh.register(POLYMATH_OS_BROWSER_CARD, _demo_execute_fn)
    mesh.register(CELL65_LLM_CARD, _demo_execute_fn)

    # Start the server (blocks)
    server = AgentMeshServer(mesh=mesh, host_card=SINGULYAR_EIR_CARD, port=args.port, host=args.host)
    server.serve_forever()


if __name__ == "__main__":
    main()
