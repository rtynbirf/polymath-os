"""runtime/tests/test_agent_mesh_server.py — Tests for Decree-Enforced HTTP JSON-RPC Server (ADR-0027).

Tests use a real running server (start/stop pattern, no mocking) so they
verify the full HTTP stack: TCP, http.server, JSON-RPC parsing, decree gate,
response serialization.
"""
import json
import os
import socket
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from threading import Thread

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_mesh_server import AgentMeshServer
from agent_mesh import AgentMesh, IntentRequest
from agent_card import SINGULYAR_EIR_CARD, CELL65_LLM_CARD
from decree_log import DecreeLog


def _find_free_port() -> int:
    """Find a free TCP port to bind to (avoid hardcoding port)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _FakeExecute:
    """Test helper — captures intents and returns a canned response."""
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {"state": "CONFIRMED", "agent_id": "singulyar-eir.local"}

    def __call__(self, request):
        self.calls.append(request)
        return self.response


class AgentMeshServerBasicTests(unittest.TestCase):
    """Basic server lifecycle tests — start/stop, health endpoint, agent card serving."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"), check_same_thread=False)
        # Issue a few prohibition decrees for enforcement tests
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")

        self.exec_fn = _FakeExecute()
        self.mesh = AgentMesh(decree_log=self.dl)
        self.mesh.register(SINGULYAR_EIR_CARD, self.exec_fn)

        self.port = _find_free_port()
        self.server = AgentMeshServer(mesh=self.mesh, host_card=SINGULYAR_EIR_CARD, port=self.port, host="localhost")
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.dl.close()
        self.tmpdir.cleanup()

    def _base_url(self):
        return f"http://localhost:{self.port}"

    def _get(self, path):
        req = urllib.request.Request(f"{self._base_url()}{path}")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8")

    def _post_json(self, path, body):
        req = urllib.request.Request(
            f"{self._base_url()}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_health_endpoint(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["host_card_id"], "singulyar-eir.local")
        self.assertEqual(data["mesh_agents"], 1)

    def test_root_redirects_to_health(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("ok", body)

    def test_agent_card_endpoint(self):
        status, body = self._get("/.well-known/agent.json")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["id"], "singulyar-eir.local")
        self.assertEqual(data["decree_scope"], "all")
        self.assertIn("intent.execute", data["capabilities"])

    def test_unknown_path_404(self):
        try:
            urllib.request.urlopen(f"{self._base_url()}/nonexistent", timeout=5)
            self.fail("should have raised HTTPError 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


class AgentMeshServerJsonRpcTests(unittest.TestCase):
    """JSON-RPC dispatch tests — send Intents to agents over HTTP."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"), check_same_thread=False)
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")

        self.exec_fn = _FakeExecute()
        self.mesh = AgentMesh(decree_log=self.dl)
        self.mesh.register(SINGULYAR_EIR_CARD, self.exec_fn)
        self.mesh.register(CELL65_LLM_CARD, _FakeExecute({"state": "CONFIRMED", "answer": "42"}))

        self.port = _find_free_port()
        self.server = AgentMeshServer(mesh=self.mesh, host_card=SINGULYAR_EIR_CARD, port=self.port)
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.dl.close()
        self.tmpdir.cleanup()

    def _post(self, path, body):
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_send_compliant_intent_returns_success(self):
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-1",
                "description": "publish note about default-deny",
                "operation": "send",
            },
            "id": "r-1",
        }
        status, response_body = self._post("/agent/singulyar-eir.local", body)
        self.assertEqual(status, 200)
        resp = json.loads(response_body)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "r-1")
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["state"], "CONFIRMED")
        # Verify execute_fn was called
        self.assertEqual(len(self.exec_fn.calls), 1)

    def test_send_blocked_intent_returns_decree_block_403(self):
        """CRITICAL: decree blocks → HTTP 403, execute_fn NOT called."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-2",
                "description": "send data to Google API",
                "operation": "send",
            },
            "id": "r-2",
        }
        status, response_body = self._post("/agent/singulyar-eir.local", body)
        self.assertEqual(status, 403)  # DECREE_BLOCK → 403 Forbidden
        resp = json.loads(response_body)
        self.assertIn("error", resp)
        self.assertIn("DECREE_BLOCK", resp["error"]["message"])
        self.assertEqual(resp["error"]["code"], -32603)
        self.assertEqual(resp["error"]["data"]["matched_term"], "google")
        # CRITICAL — execute_fn NOT called (decree blocked before)
        self.assertEqual(len(self.exec_fn.calls), 0)

    def test_send_to_unknown_agent_returns_503_or_error(self):
        """Unknown agent_id → mesh.send() returns AGENT_NOT_FOUND error."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {"description": "test"},
            "id": "r-3",
        }
        status, response_body = self._post("/agent/nonexistent.local", body)
        # AgentMesh returns IntentResponse with error — server returns 200
        # (the JSON-RPC error is in the response body, not the HTTP status)
        self.assertIn(status, (200, 403))
        resp = json.loads(response_body)
        self.assertIn("error", resp)
        self.assertIn("AGENT_NOT_FOUND", resp["error"]["message"])

    def test_invalid_json_returns_parse_error(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/agent/singulyar-eir.local",
            data=b"not valid json at all",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                status = r.status
                body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8")
        # Parse error → JSON-RPC -32700
        resp = json.loads(body)
        self.assertEqual(resp["error"]["code"], -32700)
        self.assertIn("Parse error", resp["error"]["message"])

    def test_missing_method_returns_invalid_request(self):
        body = {"jsonrpc": "2.0", "params": {}, "id": "r-4"}  # no method
        status, response_body = self._post("/agent/singulyar-eir.local", body)
        resp = json.loads(response_body)
        self.assertEqual(resp["error"]["code"], -32600)
        self.assertIn("missing 'method'", resp["error"]["message"])

    def test_send_to_cell65_llm_uses_different_agent(self):
        """Verify routing — /agent/cell65-host.llm dispatches to cell65 agent."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-5",
                "description": "ask the LLM about default-deny patterns",
                "operation": "llm.answer",
                "payload": {"prompt": "explain default-deny"},
            },
            "id": "r-5",
        }
        status, response_body = self._post("/agent/cell65-host.llm", body)
        self.assertEqual(status, 200)
        resp = json.loads(response_body)
        self.assertEqual(resp["result"]["answer"], "42")
        # singulyar-eir exec_fn NOT called
        self.assertEqual(len(self.exec_fn.calls), 0)


class AgentMeshServerCorsTests(unittest.TestCase):
    """CORS headers tests."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"), check_same_thread=False)
        self.exec_fn = _FakeExecute()
        self.mesh = AgentMesh(decree_log=self.dl)
        self.mesh.register(SINGULYAR_EIR_CARD, self.exec_fn)

        self.port = _find_free_port()
        self.server = AgentMeshServer(mesh=self.mesh, host_card=SINGULYAR_EIR_CARD, port=self.port)
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.dl.close()
        self.tmpdir.cleanup()

    def test_cors_headers_present(self):
        req = urllib.request.Request(f"http://localhost:{self.port}/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("GET", r.headers.get("Access-Control-Allow-Methods", ""))

    def test_options_preflight(self):
        req = urllib.request.Request(
            f"http://localhost:{self.port}/health",
            method="OPTIONS",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                self.assertEqual(r.status, 204)
        except urllib.error.HTTPError as e:
            self.fail(f"OPTIONS should return 204, got {e.code}")


class AgentMeshServerEndToEndTests(unittest.TestCase):
    """End-to-end: full HTTP cycle with real decree DB and multiple agents."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"), check_same_thread=False)
        # Issue all 5 typical prohibition decrees
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")
        self.dl.issue("never use Chrome Firefox Edge Safari", category="prohibition", scope="all")

        self.exec_calls = []
        def my_exec(req):
            self.exec_calls.append(req)
            return {"state": "CONFIRMED", "intent_id": req.intent_id}

        self.mesh = AgentMesh(decree_log=self.dl)
        self.mesh.register(SINGULYAR_EIR_CARD, my_exec)
        self.mesh.register(CELL65_LLM_CARD, my_exec)

        self.port = _find_free_port()
        self.server = AgentMeshServer(mesh=self.mesh, host_card=SINGULYAR_EIR_CARD, port=self.port)
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.dl.close()
        self.tmpdir.cleanup()

    def test_full_scenario_blocked(self):
        """Full HTTP cycle — DECREE_BLOCK on Google DNS violation."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-blocked",
                "description": "configure DNS with Google 8.8.8.8",
                "operation": "send",
            },
            "id": "full-blocked",
        }
        req = urllib.request.Request(
            f"http://localhost:{self.port}/agent/singulyar-eir.local",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                status, response_body = r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status, response_body = e.code, e.read().decode("utf-8")

        self.assertEqual(status, 403)  # DECREE_BLOCK → 403
        resp = json.loads(response_body)
        self.assertIn("DECREE_BLOCK", resp["error"]["message"])
        self.assertEqual(resp["error"]["data"]["matched_term"], "google")
        # execute_fn NOT called
        self.assertEqual(len(self.exec_calls), 0)

    def test_full_scenario_compliant(self):
        """Full HTTP cycle — compliant intent passes through."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-ok",
                "description": "publish local note about default-deny",
                "operation": "send",
            },
            "id": "full-ok",
        }
        req = urllib.request.Request(
            f"http://localhost:{self.port}/agent/singulyar-eir.local",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            status, response_body = r.status, r.read().decode("utf-8")

        self.assertEqual(status, 200)
        resp = json.loads(response_body)
        self.assertEqual(resp["result"]["state"], "CONFIRMED")
        self.assertEqual(resp["result"]["intent_id"], "i-ok")
        # execute_fn WAS called once
        self.assertEqual(len(self.exec_calls), 1)

    def test_full_scenario_chrome_blocked(self):
        """Chrome decree (LIST classification) — single word match."""
        body = {
            "jsonrpc": "2.0",
            "method": "intent.execute",
            "params": {
                "intent_id": "i-chrome",
                "description": "install Chrome as default browser",
                "operation": "send",
            },
            "id": "full-chrome",
        }
        req = urllib.request.Request(
            f"http://localhost:{self.port}/agent/singulyar-eir.local",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                status, response_body = r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status, response_body = e.code, e.read().decode("utf-8")

        self.assertEqual(status, 403)
        resp = json.loads(response_body)
        self.assertEqual(resp["error"]["data"]["matched_term"], "chrome")


if __name__ == "__main__":
    unittest.main()
