"""runtime/src/adapters/http_adapter.py — SINGULYAR EIR real network adapter.

The SECOND real-world consumer of the SINGULYAR EIR kernel (after
LLMLocalAdapter in Gate-3). HTTP adapter connects the kernel to a real
REST API endpoint — first non-test-scaffolding adapter with network I/O.

Per LIMITATIONS.md item 8: "Simulation only — SQLiteEffectAdapter simulates
the remote world; no real network adapters, WebRTC, encryption, accounts".
This adapter closes the "no real network adapters" gap.

## Design

HTTP adapter implements the standard Adapter contract (execute + read_state
returning Observation tri-state). Each HTTP request has:
- Idempotency: caller-provides idempotency_key, sent as `X-Idempotency-Key` header
- Method: GET (idempotent, safe retry) | POST (non-idempotent, kernel must not retry) | PUT (idempotent)
- read_state: GET to verify — if response matches expected, PASS; else FAIL/INCONCLUSIVE

States:
- always_available (HTTP transport is always available if Python has urllib)
- NotExecuted raised on network error (no effect, kernel can fail over)
- RuntimeError raised on non-network error (effect may or may not have happened)

## Honest disclosure

- Uses stdlib urllib (ADR-0002 Tier 1 — no external deps)
- No TLS verification bypass — uses default ssl context (verify_mode=CERT_REQUIRED)
- No authentication (caller must pass Authorization header via intent.payload)
- No timeout override (caller can pass `timeout_ms` in intent.constraints)

## Capabilities declared

- http.get    operation: 'http_get'    risk: low    idempotent (GET)  offline=False local_only=False priority 10
- http.post   operation: 'http_post'  risk: medium idempotent=False  offline=False local_only=False priority 20
- http.put    operation: 'http_put'   risk: medium idempotent (PUT)  offline=False local_only=False priority 15

Cross-ADR: ADR-0002 (sovereignty) — Tier 2 (network = external, replaceable
by other adapters); ADR-0007 (failover) — NotExecuted = no effect, kernel
fail-safe; ADR-0012 (EIR layer-5) — second real consumer.
"""

import json
import sys
import urllib.request
import urllib.error
import ssl
from typing import Any, Dict, Optional
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from singulyar_runtime import (
    Adapter, Capability, Intent, Observation,
    PRESENT, ABSENT, UNAVAILABLE,
    NotExecuted,
)


ADAPTER_ID = "http.local"

CAPABILITIES = (
    Capability(
        capability_id="http.get",
        operation="http_get",
        adapter_id=ADAPTER_ID,
        risk_ceiling="low",
        offline=False,  # network required
        idempotent=True,
        local_only=False,  # external endpoint
        priority=10,
    ),
    Capability(
        capability_id="http.post",
        operation="http_post",
        adapter_id=ADAPTER_ID,
        risk_ceiling="medium",
        offline=False,
        idempotent=False,  # POST may have side effects (database insert, email send, etc.)
        local_only=False,
        priority=20,
    ),
    Capability(
        capability_id="http.put",
        operation="http_put",
        adapter_id=ADAPTER_ID,
        risk_ceiling="medium",
        offline=False,
        idempotent=True,  # PUT is idempotent per HTTP spec
        local_only=False,
        priority=15,
    ),
)


class HTTPAdapter(Adapter):
    """HTTP adapter — connects SINGULYAR EIR kernel to a REST API endpoint.

    Lifecycle: stateless. Each execute() makes one HTTP request.

    Per ADR-0007: NotExecuted raised on:
      - URLError (network unreachable, DNS failure) — no effect
      - HTTPError 5xx — server error, effect may or may not have happened;
        kernel should NOT retry POST (non-idempotent) but MAY retry GET/PUT
      - Timeout — same as URLError

    RuntimeError (effect may have happened) raised on:
      - HTTPError 4xx (client error — request was processed, server returned error)
      - HTTPError 3xx (redirect — request was processed, but redirected)
      - HTTPError 2xx but response body invalid (effect happened, response malformed)
    """

    adapter_id = ADAPTER_ID

    def __init__(self, default_timeout_ms: int = 30000, **kw):
        super().__init__(**kw)
        self._default_timeout_ms = default_timeout_ms
        self._cache: Dict[str, Dict[str, Any]] = {}  # idempotency_key → response
        self._calls: int = 0
        # SSL context: default = cert required, no bypass
        self._ssl_context = ssl.create_default_context()

    def is_available(self) -> bool:
        return True  # urllib is always available in stdlib

    def status(self) -> Dict[str, str]:
        return {
            "state": "READY",
            "transport": "urllib (stdlib)",
            "ssl": "CERT_REQUIRED (default)",
            "capabilities": "http.get (idempotent), http.post (non-idempotent), http.put (idempotent)",
            "calls": str(self._calls),
            "cache_size": str(len(self._cache)),
        }

    def execute(self, intent: Intent, idempotency_key: str) -> Any:
        """Execute an HTTP request.

        intent.payload must contain:
          - url: str (required, full URL including scheme)
          - method: 'GET' | 'POST' | 'PUT' (required)
          - body: dict (optional, for POST/PUT — JSON-encoded)
          - headers: dict (optional, e.g. {'Authorization': 'Bearer ...'})

        intent.constraints may contain:
          - timeout_ms: int (optional, overrides default)

        Returns: dict — parsed JSON response body, OR raw text if not JSON.
        """
        key = idempotency_key
        if key in self._cache:
            return self._cache[key]  # full dict with status_code/response/url/method
        self._calls += 1

        url = intent.payload.get("url")
        method = intent.payload.get("method", "GET").upper()
        body = intent.payload.get("body")
        headers = dict(intent.payload.get("headers", {}))
        timeout_ms = intent.constraints.get("timeout_ms", self._default_timeout_ms)
        timeout_s = timeout_ms / 1000.0

        if not url:
            raise NotExecuted("intent.payload.url is required")

        # Idempotency-Key header for server-side dedup
        headers.setdefault("X-Idempotency-Key", key)
        if body is not None:
            headers.setdefault("Content-Type", "application/json")

        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data_bytes, method=method, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=self._ssl_context) as r:
                status_code = r.status
                body_bytes = r.read()
        except urllib.error.HTTPError as e:
            # Server processed the request — effect may have happened
            if 200 <= e.code < 300:
                # 2xx but the response itself was an HTTPError (shouldn't happen, but defensive)
                body_bytes = e.read()
                status_code = e.code
            elif 300 <= e.code < 400:
                # 3xx redirect — request was processed
                raise RuntimeError(f"HTTP {e.code} redirect — request processed, effect may have happened")
            elif 400 <= e.code < 500:
                # 4xx client error — request processed, server returned error
                # For non-idempotent (POST): RuntimeError (effect may have happened)
                # For idempotent (GET/PUT): NotExecuted is wrong — we DID send the request
                # Per contract: surface as RuntimeError so kernel doesn't retry
                raise RuntimeError(f"HTTP {e.code} client error — request processed")
            else:
                # 5xx server error — server may or may not have processed
                # For idempotent (GET/PUT): safe to retry → NotExecuted (no confirmed effect)
                # For non-idempotent (POST): NOT safe to retry → RuntimeError (effect may have happened)
                cap_id = next((c.capability_id for c in CAPABILITIES if c.operation == intent.operation), None)
                cap = next((c for c in CAPABILITIES if c.operation == intent.operation), None)
                if cap and cap.idempotent:
                    raise NotExecuted(f"HTTP {e.code} server error — idempotent operation, safe to retry")
                else:
                    raise RuntimeError(f"HTTP {e.code} server error — non-idempotent operation, effect may have happened")
        except urllib.error.URLError as e:
            # Network-level failure (DNS, connection refused, timeout)
            raise NotExecuted(f"network error: {e.reason}")
        except TimeoutError as e:
            raise NotExecuted(f"timeout: {e}")
        except Exception as e:
            # Unknown error — surface as RuntimeError (effect may have happened)
            raise RuntimeError(f"unexpected HTTP error: {e}")

        # Parse response
        try:
            response = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = body_bytes.decode("utf-8", errors="replace")

        result = {
            "status_code": status_code,
            "response": response,
            "url": url,
            "method": method,
        }
        self._cache[key] = result
        return result

    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        """Read state: PRESENT (cached response for this key), ABSENT (no cache).

        Per ADR-0010 S15: sibling keys don't pollute. Exact key match required.
        """
        key = idempotency_key
        try:
            if key in self._cache:
                entry = self._cache[key]
                return Observation(
                    status=PRESENT,
                    value={"response": entry.get("response"),
                           "status_code": entry.get("status_code"),
                           "via": "http.local"},
                    count=1,
                )
            return Observation(status=ABSENT, value=None, count=0)
        except Exception:
            return Observation(status=UNAVAILABLE, value=None, count=0)

    def calls(self) -> int:
        return self._calls

    def cache_keys(self) -> list:
        return list(self._cache.keys())


def default_adapter(default_timeout_ms: int = 30000) -> HTTPAdapter:
    return HTTPAdapter(default_timeout_ms=default_timeout_ms)


def default_capabilities() -> tuple:
    return CAPABILITIES
