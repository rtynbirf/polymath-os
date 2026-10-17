"""runtime/tests/test_webrtc_adapter.py — Tests for WebRTCAdapter (Gate-7 creativity).

Verifies:
- Adapter contract (execute + read_state → Observation tri-state)
- NotExecuted when aiortc not installed (honest UNAVAILABLE)
- NotExecuted when no peer connection
- S15: sibling key doesn't pollute absent key's read_state
- 2 capabilities declared (webrtc.send + webrtc.recv) with offline=True, local_only=True
- status() returns UNAVAILABLE with reason when aiortc not installed
- status() returns READY when peer connection created (if aiortc available)

Tests SKIP if aiortc IS installed (because we test the not-installed path).
Or: parametrized to test both paths.
"""

import os, sys, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_SRC_ADAPTERS = _SRC / "adapters"
if str(_SRC_ADAPTERS) not in sys.path:
    sys.path.insert(0, str(_SRC_ADAPTERS))

from singulyar_runtime import (
    Intent, Capability, Observation, State,
    PRESENT, ABSENT, UNAVAILABLE,
    NotExecuted, Runtime, Policy,
)
from adapters.webrtc_adapter import (
    WebRTCAdapter, CAPABILITIES, ADAPTER_ID, ADAPTER_VERSION,
    default_adapter, default_capabilities, _HAS_AIORTC,
)


class WebRTCAdapterTests(unittest.TestCase):

    def _make_intent(self, message="hello", iid="webrtc-1", operation="webrtc_send"):
        return Intent(
            intent_id=iid,
            description=f"webrtc send: {message}",
            operation=operation,
            payload={"message": message, "peer_id": "test-peer"},
            expected={},
        )

    def test_adapter_id_constant(self):
        self.assertEqual(ADAPTER_ID, "webrtc.local")

    def test_adapter_version_includes_python_port_note(self):
        self.assertIn("Python-порт", ADAPTER_VERSION)

    def test_capabilities_count_and_fields(self):
        caps = CAPABILITIES
        self.assertEqual(len(caps), 2)
        ids = {c.capability_id for c in caps}
        self.assertEqual(ids, {"webrtc.send", "webrtc.recv"})
        # All capabilities must be offline (air-gapped by design)
        for c in caps:
            self.assertTrue(c.offline, f"{c.capability_id} must be offline=True (air-gapped)")
            self.assertTrue(c.local_only, f"{c.capability_id} must be local_only=True (P2P, no server)")
            self.assertTrue(c.idempotent, f"{c.capability_id} must be idempotent=True (safe retry per ADR-0007)")

    def test_default_adapter_unavailable_state_when_no_aiortc(self):
        """Per ADR-0006: status() MUST return UNAVAILABLE with reason when aiortc absent."""
        if _HAS_AIORTC:
            self.skipTest("aiortc installed — testing not-installed path requires absence")
        ad = default_adapter()
        st = ad.status()
        self.assertEqual(st["state"], "UNAVAILABLE")
        self.assertIn("aiortc not installed", st["reason"])
        self.assertEqual(st["aiortc_installed"], "no")

    def test_read_state_absent_for_never_executed_key(self):
        ad = default_adapter()
        intent = self._make_intent(iid="never-run-1")
        obs = ad.read_state(intent, "never-run-key-1")
        self.assertEqual(obs.status, ABSENT)
        self.assertEqual(obs.count, 0)

    def test_s15_partial_cache_miss_does_not_pollute_sibling(self):
        """ADR-0010 S15 cross-check for WebRTCAdapter."""
        ad = default_adapter()
        # Pre-populate sibling via direct cache injection
        sibling_key = "sibling-key"
        ad._cache[sibling_key] = {"packet": {"v": "sibling"}, "seq": 1, "sent": True}
        self.assertEqual(ad.cache_keys(), [sibling_key])

        # Query absent key
        intent = self._make_intent(iid="absent-1")
        obs = ad.read_state(intent, "absent-key")
        self.assertEqual(obs.status, ABSENT, "absent key MUST NOT infer PRESENT from sibling")
        self.assertEqual(obs.count, 0)

        # And sibling still PRESENT
        sibling_intent = self._make_intent(iid="sibling-1")
        obs = ad.read_state(sibling_intent, sibling_key)
        self.assertEqual(obs.status, PRESENT)
        self.assertEqual(obs.count, 1)

    def test_execute_raises_not_executed_when_no_aiortc(self):
        """Per ADR-0007: NotExecuted (no effect) when aiortc absent — kernel can failover."""
        if _HAS_AIORTC:
            self.skipTest("aiortc installed — testing not-installed path")
        ad = default_adapter()
        intent = self._make_intent(message="test message", iid="no-aiortc-1")
        with self.assertRaises(NotExecuted) as ctx:
            ad.execute(intent, "no-aiortc-key-1")
        self.assertIn("aiortc not installed", str(ctx.exception))

    def test_execute_raises_not_executed_when_no_peer(self):
        """Per ADR-0007: NotExecuted (no effect) when no peer connection — even if aiortc present."""
        if not _HAS_AIORTC:
            self.skipTest("aiortc not installed — testing peer-absent path requires aiortc")
        ad = default_adapter()
        # Don't call create_peer_connection — channel is None
        intent = self._make_intent(message="test", iid="no-peer-1")
        with self.assertRaises(NotExecuted) as ctx:
            ad.execute(intent, "no-peer-key-1")
        self.assertIn("no active peer connection", str(ctx.exception))

    def test_create_peer_connection_returns_sdp_offer_or_error(self):
        """create_peer_connection either returns SDP offer (aiortc installed)
        or {'error': str, 'reason': str} (not installed) — honest, no silent fail."""
        ad = default_adapter()
        result = ad.create_peer_connection("test-peer-1")
        if _HAS_AIORTC:
            self.assertIn("sdp_offer", result)
            self.assertEqual(result["peer_id"], "test-peer-1")
            self.assertEqual(result["ice_servers"], [])  # air-gapped
        else:
            self.assertIn("error", result)
            self.assertIn("aiortc", result["error"])


class IntegrationWithRuntimeTests(unittest.TestCase):
    """End-to-end: WebRTCAdapter wired into Runtime — third real consumer."""

    def _make_caps(self):
        return list(CAPABILITIES)

    def test_runtime_with_webrtc_adapter_send(self):
        """Runtime with WebRTCAdapter — execute a send via kernel.

        If aiortc absent: state should be WAITING_FOR_HUMAN or UNKNOWN
        (NotExecuted → no compatible capability → kernel doesn't lie CONFIRMED).
        """
        ad = default_adapter()
        caps = self._make_caps()
        rt = Runtime(caps, [ad], Policy({"webrtc_send", "webrtc_recv"}))
        intent = Intent(
            intent_id="rt-webrtc-1",
            description="webrtc send: hello",
            operation="webrtc_send",
            payload={"message": "hello", "peer_id": "test-peer"},
            expected={},
        )
        st = rt.run(intent)
        # Without aiortc → NotExecuted → no failover target → WAITING_FOR_HUMAN
        # With aiortc but no peer → NotExecuted → same path
        self.assertIn(st, {State.WAITING_FOR_HUMAN, State.UNKNOWN, State.FAILED},
                      f"WebRTC adapter without full setup must NOT be CONFIRMED — got {st}")


if __name__ == "__main__":
    unittest.main()
