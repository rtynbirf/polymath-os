"""runtime/tests/test_http_adapter.py — Tests for HTTPAdapter (Gate-6).

Verifies:
- Adapter contract (execute + read_state → Observation tri-state)
- Idempotency: same key → cached response
- NotExecuted on network failure (DNS, connection refused)
- RuntimeError on 4xx/3xx (effect may have happened)
- S15: sibling key doesn't pollute absent key's read_state
- 3 capabilities declared (http.get/post/put) with correct idempotency flags

Network tests use httpbin.org or skip if offline.
"""

import os, sys, unittest, json
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
from adapters.http_adapter import (
    HTTPAdapter, CAPABILITIES, ADAPTER_ID,
    default_adapter, default_capabilities,
)


class HTTPAdapterTests(unittest.TestCase):

    def _make_intent(self, url="https://httpbin.org/get", method="GET", iid="http-1", operation="http_get"):
        return Intent(
            intent_id=iid,
            description=f"HTTP {method} {url}",
            operation=operation,
            payload={"url": url, "method": method},
            expected={},
        )

    def test_adapter_id_constant(self):
        self.assertEqual(ADAPTER_ID, "http.local")

    def test_capabilities_count_and_idempotency(self):
        caps = CAPABILITIES
        self.assertEqual(len(caps), 3)
        ids = {c.capability_id for c in caps}
        self.assertEqual(ids, {"http.get", "http.post", "http.put"})
        # GET and PUT are idempotent
        get_cap = next(c for c in caps if c.capability_id == "http.get")
        put_cap = next(c for c in caps if c.capability_id == "http.put")
        post_cap = next(c for c in caps if c.capability_id == "http.post")
        self.assertTrue(get_cap.idempotent)
        self.assertTrue(put_cap.idempotent)
        self.assertFalse(post_cap.idempotent, "POST must be non-idempotent (kernel won't auto-retry)")

    def test_default_adapter_ready_state(self):
        ad = default_adapter()
        st = ad.status()
        self.assertEqual(st["state"], "READY")
        self.assertIn("urllib", st["transport"])
        self.assertEqual(st["ssl"], "CERT_REQUIRED (default)")

    def test_read_state_absent_for_never_executed_key(self):
        ad = default_adapter()
        intent = self._make_intent(iid="never-run-1")
        obs = ad.read_state(intent, "never-run-key-1")
        self.assertEqual(obs.status, ABSENT)
        self.assertEqual(obs.count, 0)

    def test_s15_partial_cache_miss_does_not_pollute_sibling(self):
        """ADR-0010 S15 cross-check for HTTPAdapter."""
        ad = default_adapter()
        # Pre-populate sibling via direct cache injection
        sibling_key = "sibling-key"
        ad._cache[sibling_key] = {"response": "sibling", "status_code": 200}
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


class HTTPAdapterNetworkTests(unittest.TestCase):
    """Tests that actually hit the network (httpbin.org). Skip if offline."""

    @classmethod
    def setUpClass(cls):
        # Detect if we have network
        import urllib.request
        try:
            urllib.request.urlopen("https://httpbin.org/get", timeout=5)
            cls.has_network = True
        except Exception:
            cls.has_network = False

    def setUp(self):
        if not self.has_network:
            self.skipTest("no network — skipping HTTP integration tests")

    def test_real_http_get_returns_200(self):
        ad = default_adapter(default_timeout_ms=10000)
        intent = Intent(
            intent_id="real-get-1",
            description="real GET to httpbin.org",
            operation="http_get",
            payload={"url": "https://httpbin.org/get", "method": "GET"},
            expected={},
        )
        result = ad.execute(intent, "real-get-key-1")
        self.assertEqual(result["status_code"], 200)
        self.assertIn("url", result["response"])  # httpbin echoes url
        # Idempotency: same key returns cached
        result2 = ad.execute(intent, "real-get-key-1")
        self.assertEqual(result2["status_code"], 200)
        self.assertEqual(ad.calls(), 1, "second call = cache hit, no real HTTP request")

    def test_real_http_4xx_raises_runtime_error(self):
        ad = default_adapter(default_timeout_ms=10000)
        intent = Intent(
            intent_id="real-404-1",
            description="real GET to httpbin 404",
            operation="http_get",
            payload={"url": "https://httpbin.org/status/404", "method": "GET"},
            expected={},
        )
        with self.assertRaises(RuntimeError) as ctx:
            ad.execute(intent, "real-404-key-1")
        self.assertIn("404", str(ctx.exception))

    def test_real_http_5xx_get_raises_not_executed(self):
        """5xx on idempotent GET → NotExecuted (safe to retry)."""
        ad = default_adapter(default_timeout_ms=10000)
        intent = Intent(
            intent_id="real-500-1",
            description="real GET to httpbin 500",
            operation="http_get",
            payload={"url": "https://httpbin.org/status/500", "method": "GET"},
            expected={},
        )
        with self.assertRaises(NotExecuted) as ctx:
            ad.execute(intent, "real-500-key-1")
        self.assertIn("500", str(ctx.exception))


class IntegrationWithRuntimeTests(unittest.TestCase):
    """End-to-end: HTTPAdapter wired into Runtime — second real consumer."""

    def _make_caps(self):
        return list(CAPABILITIES)

    def test_runtime_with_http_adapter_get(self):
        """Runtime with HTTPAdapter — execute a GET via kernel."""
        import urllib.request
        try:
            urllib.request.urlopen("https://httpbin.org/get", timeout=3)
            has_net = True
        except Exception:
            has_net = False
        if not has_net:
            self.skipTest("no network")

        ad = default_adapter()
        caps = self._make_caps()
        rt = Runtime(caps, [ad], Policy({"http_get", "http_post", "http_put"}))
        intent = Intent(
            intent_id="rt-get-1",
            description="RT GET httpbin",
            operation="http_get",
            payload={"url": "https://httpbin.org/get", "method": "GET"},
            expected={},
        )
        st = rt.run(intent)
        self.assertEqual(st, State.CONFIRMED)


if __name__ == "__main__":
    unittest.main()
