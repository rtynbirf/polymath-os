"""runtime/tests/test_federation.py — Tests for decree federation over HTTP (ADR-0029).

Verifies that:
  1. AgentMeshServer exposes read-only decree log JSON-RPC methods
     (``decree.get_active_laws``, ``decree.get_all``) that do NOT require
     agent registration.
  2. ``A2AClient.federate_decrees()`` can fetch active laws from a remote
     AgentMeshServer instance and return them as a list.

Tests use a real running server (start/stop pattern, no mocking) — they
verify the full HTTP stack: TCP, http.server, JSON-RPC parsing, decree
log dispatch, response serialization, and the A2A client's federation
fetch path.
"""
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_mesh_server import AgentMeshServer
from agent_mesh import AgentMesh
from agent_card import SINGULYAR_EIR_CARD
from a2a_client import A2AClient
from decree_log import DecreeLog


def _find_free_port() -> int:
    """Find a free TCP port to bind to (avoid hardcoding port)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _FederationTestBase(unittest.TestCase):
    """Shared setup: a decree log with 3 laws + a server, with NO agents
    registered in the mesh (verifying the new decree.* methods work
    without registration)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(
            str(Path(self.tmpdir.name) / "decrees.db"),
            check_same_thread=False,
        )
        # Issue a mix of prohibition + law decrees (all are 'active_laws').
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("always log intents to evidence ledger", category="law", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")

        # Note: we deliberately do NOT register any agent — the new
        # decree.* federation methods must work without registration.
        self.mesh = AgentMesh(decree_log=self.dl)
        self.port = _find_free_port()
        self.server = AgentMeshServer(
            mesh=self.mesh,
            host_card=SINGULYAR_EIR_CARD,
            port=self.port,
            host="localhost",
        )
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.dl.close()
        self.tmpdir.cleanup()

    @property
    def rpc_url(self) -> str:
        """The JSON-RPC endpoint for the (unregistered) singulyar-eir agent."""
        return f"http://localhost:{self.port}/agent/singulyar-eir.local"

    def _post(self, body):
        req = urllib.request.Request(
            self.rpc_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")


class FederationDecreeRpcTests(_FederationTestBase):
    """Verify the read-only decree log JSON-RPC methods exposed by AgentMeshServer."""

    def test_get_active_laws_via_http(self):
        """POST method=decree.get_active_laws → returns the active laws list.

        Critical: works WITHOUT any agent registered in the mesh (no
        AGENT_NOT_FOUND error), and returns HTTP 200 (not 403 DECREE_BLOCK).
        """
        status, body = self._post({
            "jsonrpc": "2.0",
            "method": "decree.get_active_laws",
            "params": {},
            "id": "r-1",
        })
        self.assertEqual(status, 200, f"expected 200, got {status}: {body}")
        resp = json.loads(body)
        # Standard JSON-RPC 2.0 success envelope.
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "r-1")
        self.assertIn("result", resp)
        self.assertNotIn("error", resp)

        result = resp["result"]
        self.assertIsInstance(result, list)
        # All 3 decrees are laws/prohibitions; none superseded.
        self.assertEqual(len(result), 3)

        # Verify shape: each item has seq, timestamp, text, category, scope.
        for item in result:
            self.assertIn("seq", item)
            self.assertIn("text", item)
            self.assertIn("category", item)
            self.assertIn("scope", item)

        texts = sorted(r["text"] for r in result)
        self.assertEqual(texts, sorted([
            "never use Google DNS",
            "always log intents to evidence ledger",
            "never use Cloudflare",
        ]))

    def test_get_all_decrees_via_http(self):
        """POST method=decree.get_all → returns ALL decrees (full record).

        Note: get_all uses ``decree_text`` (vs ``text`` in get_active_laws)
        and includes the ``decree_hash`` field. The full ledger is the
        authoritative source for federation replication/replay.
        """
        status, body = self._post({
            "jsonrpc": "2.0",
            "method": "decree.get_all",
            "params": {},
            "id": "r-2",
        })
        self.assertEqual(status, 200, f"expected 200, got {status}: {body}")
        resp = json.loads(body)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "r-2")
        self.assertIn("result", resp)
        self.assertNotIn("error", resp)

        result = resp["result"]
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

        # Verify ordering and shape.
        seqs = [r["seq"] for r in result]
        self.assertEqual(seqs, [1, 2, 3])

        # get_all() shape uses 'decree_text' + truncated 'decree_hash'.
        for item in result:
            self.assertIn("seq", item)
            self.assertIn("timestamp", item)
            self.assertIn("decree_text", item)
            self.assertIn("category", item)
            self.assertIn("scope", item)
            self.assertIn("decree_hash", item)

        # Verify content matches the issued decrees.
        texts = [r["decree_text"] for r in result]
        self.assertEqual(texts, [
            "never use Google DNS",
            "always log intents to evidence ledger",
            "never use Cloudflare",
        ])

    def test_federate_decrees_fetches_from_remote(self):
        """A2AClient.federate_decrees() fetches active laws from a remote
        AgentMeshServer and returns them as a list.

        This is the core federation round-trip test: the A2AClient issues
        ``decree.get_active_laws`` via HTTP POST and parses the JSON-RPC
        response back into a Python list of decree dicts.
        """
        # No decree_log attached to the client — outbound decree gate is
        # irrelevant for read-only federation (the request body has no
        # intent/payload that could leak sensitive data).
        client = A2AClient(decree_log=None)
        laws = client.federate_decrees(self.rpc_url)

        # Should match the 3 active laws we issued in setUp().
        self.assertIsInstance(laws, list)
        self.assertEqual(len(laws), 3)

        texts = sorted(law["text"] for law in laws)
        self.assertEqual(texts, sorted([
            "never use Google DNS",
            "always log intents to evidence ledger",
            "never use Cloudflare",
        ]))

        # Verify the client emitted a successful federation event.
        events = client.events()
        event_types = [e["event"] for e in events]
        self.assertIn("FEDERATE_DECREES_FETCHED", event_types)
        fetched_ev = next(
            e for e in events if e["event"] == "FEDERATE_DECREES_FETCHED"
        )
        self.assertEqual(fetched_ev["agent_url"], self.rpc_url)
        self.assertEqual(fetched_ev["count"], 3)


if __name__ == "__main__":
    unittest.main()
