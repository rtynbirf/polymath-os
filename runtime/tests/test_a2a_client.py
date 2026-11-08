"""runtime/tests/test_a2a_client.py — Tests for Decree-Driven A2A Client (ADR-0025).

Verifies that the outbound decree gate fires BEFORE any network request,
so sensitive data in Intents that violate decrees never reaches the wire.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from a2a_client import (
    A2AClient, A2AClientError, OutboundBlockResponse,
    DEFAULT_OUTBOUND_SCOPE, DECREE_BLOCK_OUTBOUND_ERROR_CODE,
)
from agent_mesh import IntentRequest, IntentResponse, DECREE_BLOCK_ERROR_CODE
from agent_card import AgentCard, SINGULYAR_EIR_CARD
from decree_log import DecreeLog


class A2AClientBasicTests(unittest.TestCase):
    def test_no_decree_log_skips_outbound_gate(self):
        """When decree_log is None, A2AClient just does plain HTTP POST."""
        client = A2AClient(decree_log=None)
        # check_outbound returns compliant=True always
        r = client.check_outbound("anything")
        self.assertTrue(r["compliant"])

    def test_default_scope_is_outbound(self):
        client = A2AClient()
        self.assertEqual(client.default_scope, DEFAULT_OUTBOUND_SCOPE)
        self.assertEqual(DEFAULT_OUTBOUND_SCOPE, "outbound")

    def test_check_outbound_with_decree_log_compliant(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(str(Path(tmp) / "decrees.db"))
            dl.issue("never use Google DNS", category="prohibition", scope="all")
            client = A2AClient(decree_log=dl)
            # An intent that doesn't mention Google → compliant
            r = client.check_outbound("publish note about default-deny")
            self.assertTrue(r["compliant"])
            dl.close()

    def test_check_outbound_with_decree_log_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(str(Path(tmp) / "decrees.db"))
            dl.issue("never use Google DNS", category="prohibition", scope="all")
            client = A2AClient(decree_log=dl)
            r = client.check_outbound("send data to Google API")
            self.assertFalse(r["compliant"])
            self.assertGreater(len(r["violations"]), 0)
            dl.close()


class A2AClientOutboundDecreeGateTests(unittest.TestCase):
    """Core ADR-0025 tests — outbound decree gate fires BEFORE network."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        # Issue prohibition decrees with various scopes.
        # Note: 'PII' as single word (SINGLE classification) matches any
        # intent description containing 'pii' (case-insensitive, word-boundary).
        # Using "never transmit PII" rather than "never send PII to external
        # services" — the latter would extract "PII to external services"
        # as a fallback phrase, which only matches exact phrase (incl.
        # plural 's'). Single-word is more robust.
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")
        self.dl.issue("never transmit PII", category="prohibition", scope="outbound")

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    def test_outbound_decree_blocks_before_network_request(self):
        """CRITICAL: when intent mentions Google, A2AClient must NOT make
        any HTTP request — the outbound decree gate fires first."""
        client = A2AClient(decree_log=self.dl)

        # Mock urllib.request.urlopen to ensure it's NOT called
        with patch("urllib.request.urlopen") as mock_urlopen:
            req = IntentRequest(
                id="r-1",
                params={
                    "intent_id": "i-1",
                    "description": "send data to Google API",
                    "operation": "send",
                },
            )
            resp = client.send("https://external-agent.local/agent", req)
            # CRITICAL: urlopen MUST NOT have been called
            mock_urlopen.assert_not_called()
            # Response should be DECREE_BLOCK
            self.assertTrue(resp.is_blocked())
            self.assertEqual(resp.error.code, DECREE_BLOCK_OUTBOUND_ERROR_CODE)
            self.assertIn("OUTBOUND_DECREE_BLOCK", resp.error.message)
            self.assertIn("google", resp.error.message)
            self.assertEqual(resp.error.data["direction"], "outbound")
            self.assertEqual(resp.error.data["matched_term"], "google")

    def test_outbound_decree_blocks_pii_to_external(self):
        """The 'never send PII to external services' decree (scope=outbound)
        should match intents containing 'PII'."""
        client = A2AClient(decree_log=self.dl)
        with patch("urllib.request.urlopen") as mock_urlopen:
            req = IntentRequest(
                id="r-2",
                params={
                    "intent_id": "i-2",
                    "description": "send user PII to external service",
                    "operation": "send",
                },
            )
            resp = client.send("https://external-agent.local/agent", req)
            mock_urlopen.assert_not_called()
            self.assertTrue(resp.is_blocked())
            self.assertEqual(resp.error.data["matched_term"], "pii")

    def test_compliant_intent_proceeds_to_network(self):
        """When intent is clean, A2AClient SHOULD make the HTTP request."""
        client = A2AClient(decree_log=self.dl)
        # Mock urlopen to return a fake successful response
        mock_response_body = json.dumps({
            "jsonrpc": "2.0",
            "result": {"state": "CONFIRMED"},
            "id": "r-3",
        }).encode("utf-8")

        class FakeCtxManager:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                return mock_response_body

        fake_cm = FakeCtxManager()
        with patch("urllib.request.urlopen", return_value=fake_cm) as mock_urlopen:
            req = IntentRequest(
                id="r-3",
                params={
                    "intent_id": "i-3",
                    "description": "publish note about default-deny",  # no decree violation
                    "operation": "send",
                },
            )
            resp = client.send("https://external-agent.local/agent", req)
            # HTTP request SHOULD have been made
            mock_urlopen.assert_called_once()
            self.assertFalse(resp.is_blocked())
            self.assertEqual(resp.result.get("state"), "CONFIRMED")

    def test_outbound_decree_block_events_recorded(self):
        """OUTBOUND_DECREE_BLOCK event should be in the client's event log."""
        client = A2AClient(decree_log=self.dl)
        with patch("urllib.request.urlopen"):
            req = IntentRequest(
                id="r-4",
                params={"description": "use Google Cloud Storage"},
            )
            client.send("https://external-agent.local/agent", req)
        events = client.events()
        event_types = [e["event"] for e in events]
        self.assertIn("OUTBOUND_DECREE_BLOCK", event_types)

    def test_caller_can_override_scope(self):
        """Caller can pass scope= in params to override default 'outbound'."""
        client = A2AClient(decree_log=self.dl)
        # Issue a decree scoped to 'internal-only' — won't match default 'outbound' scope.
        # Use single-word "WebRTC" so LIST classification doesn't produce a multi-word phrase.
        # (3-word decrees like "never use WebRTC for video" fall into the fallback case
        # that extracts "webrtc for video" as one term — that's a v0.6 limitation, not a
        # bug in the client. We want to test scope filtering, not phrase classification.)
        self.dl.issue("never use WebRTC", category="prohibition", scope="internal-only")

        # With default outbound scope, 'webrtc' decree doesn't apply → request goes through
        mock_response_body = json.dumps({"jsonrpc": "2.0", "result": {}}).encode("utf-8")
        class FakeCtxOK:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self): return mock_response_body
        with patch("urllib.request.urlopen", return_value=FakeCtxOK()):
            req = IntentRequest(
                id="r-5",
                params={"description": "use WebRTC for video"},
            )
            resp = client.send("https://external-agent.local/agent", req)
            # Should pass — 'internal-only' scope doesn't apply to outbound
            self.assertFalse(resp.is_blocked(), f"Expected to pass with default outbound scope. Got: {resp.to_dict()}")

        # Now override scope to 'internal-only' — decree should fire
        with patch("urllib.request.urlopen") as mock_urlopen:
            req = IntentRequest(
                id="r-6",
                params={
                    "description": "use WebRTC for video",
                    "decree_scope": "internal-only",
                },
            )
            resp = client.send("https://external-agent.local/agent", req)
            mock_urlopen.assert_not_called()
            self.assertTrue(resp.is_blocked())
            self.assertEqual(resp.error.data["matched_term"], "webrtc")


class A2AClientDiscoverTests(unittest.TestCase):
    """Tests for the discover() method — fetches Agent Card from remote."""

    def test_discover_parses_valid_agent_card(self):
        client = A2AClient()
        # Mock urlopen to return a valid agent card JSON
        card_json = SINGULYAR_EIR_CARD.to_json()
        card_bytes = card_json.encode("utf-8")

        class FakeCtx:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self): return card_bytes

        with patch("urllib.request.urlopen", return_value=FakeCtx()):
            card = client.discover("https://example.local/.well-known/agent.json")
            self.assertEqual(card.id, SINGULYAR_EIR_CARD.id)
            self.assertEqual(card.decree_scope, SINGULYAR_EIR_CARD.decree_scope)

    def test_discover_http_error_raises_a2a_client_error(self):
        client = A2AClient()
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://example.local/.well-known/agent.json",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )):
            with self.assertRaises(A2AClientError) as ctx:
                client.discover("https://example.local/.well-known/agent.json")
            self.assertIn("HTTP 404", str(ctx.exception))

    def test_discover_invalid_card_raises_a2a_client_error(self):
        client = A2AClient()
        invalid_bytes = b"{not valid json"

        class FakeCtx:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self): return invalid_bytes

        with patch("urllib.request.urlopen", return_value=FakeCtx()):
            with self.assertRaises(A2AClientError):
                client.discover("https://example.local/.well-known/agent.json")


class A2AClientResponseParsingTests(unittest.TestCase):
    """Tests for parsing various A2A server responses."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")
        self.client = A2AClient(decree_log=self.dl)

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    def _mock_response(self, body: bytes):
        """Return a context-manager-like fake HTTP response."""
        class FakeCtx:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *args): return None
            def read(self_inner): return body
        return FakeCtx()

    def test_remote_returns_decree_block_error(self):
        """When remote A2A server returns DECREE_BLOCK, A2AClient parses it."""
        remote_error = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "DECREE_BLOCK: intent violates decree #1",
                "data": {"decree_seq": 1, "matched_term": "google"},
            },
            "id": "r-7",
        }
        with patch("urllib.request.urlopen",
                   return_value=self._mock_response(json.dumps(remote_error).encode("utf-8"))):
            req = IntentRequest(id="r-7", params={"description": "publish note"})
            resp = self.client.send("https://agent.local/agent", req)
            self.assertTrue(resp.is_blocked())
            self.assertIn("DECREE_BLOCK", resp.error.message)
            self.assertEqual(resp.error.data["matched_term"], "google")

    def test_remote_returns_network_error(self):
        """Network errors are wrapped in IntentResponse with error field."""
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            req = IntentRequest(id="r-8", params={"description": "publish note"})
            resp = self.client.send("https://nonexistent.local/agent", req)
            self.assertTrue(resp.is_blocked())
            self.assertIn("Network error", resp.error.message)
            self.assertEqual(resp.error.data["exception_type"], "URLError")

    def test_remote_returns_invalid_json(self):
        with patch("urllib.request.urlopen",
                   return_value=self._mock_response(b"not json at all")):
            req = IntentRequest(id="r-9", params={"description": "publish note"})
            resp = self.client.send("https://agent.local/agent", req)
            self.assertTrue(resp.is_blocked())
            self.assertIn("Invalid JSON", resp.error.message)


class A2AClientFullRoundTripTests(unittest.TestCase):
    """Full scenario: polymath-os agent sends to external A2A server,
    outbound decree gate fires before network, then remote returns."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        # 'never transmit PII' (single word) → matches any description containing 'pii'
        self.dl.issue("never transmit PII", category="prohibition", scope="outbound")
        self.client = A2AClient(decree_log=self.dl)

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    def test_full_scenario_blocked_outbound(self):
        """PII in description → OUTBOUND_DECREE_BLOCK, no network request."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            req = IntentRequest(
                id="full-blocked",
                params={
                    "intent_id": "i-full-1",
                    "description": "send user PII to external service",
                    "operation": "send",
                },
            )
            resp = self.client.send("https://marketing.external/agent", req)
            self.assertTrue(resp.is_blocked())
            self.assertEqual(resp.error.code, DECREE_BLOCK_OUTBOUND_ERROR_CODE)
            self.assertEqual(resp.error.data["direction"], "outbound")
            self.assertEqual(resp.error.data["agent_url"], "https://marketing.external/agent")
            mock_urlopen.assert_not_called()

    def test_full_scenario_compliant_proceeds(self):
        """Clean intent → outbound decree passes → network request made."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "result": {"state": "CONFIRMED", "id": "full-ok"},
            "id": "full-ok",
        }).encode("utf-8")
        mock_response.__enter__ = lambda self: mock_response
        mock_response.__exit__ = lambda self, *args: None
        with patch("urllib.request.urlopen", return_value=mock_response):
            req = IntentRequest(
                id="full-ok",
                params={
                    "intent_id": "i-full-2",
                    "description": "publish local note about default-deny",
                    "operation": "send",
                },
            )
            resp = self.client.send("https://agent.local/agent", req)
            self.assertFalse(resp.is_blocked())
            self.assertEqual(resp.result.get("state"), "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
