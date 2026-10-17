"""runtime/src/a2a_client.py — Decree-Driven A2A Client (per ADR-0025).

While AgentMesh (ADR-0024) handles INBOUND decree enforcement (when
other agents send Intents to polymath-os agents), A2AClient handles
OUTBOUND decree enforcement — when polymath-os agents send Intents
to external A2A-compatible agents.

The critical property: the decree gate fires BEFORE any network
request leaves the system. Sensitive data in an Intent that would
violate a decree (e.g. "never send PII to external services") never
reaches the wire.

Usage:
    from a2a_client import A2AClient, A2AClientError
    from decree_log import DecreeLog

    client = A2AClient(decree_log=dl)
    # Fetch the external agent's card (for context)
    card = client.discover("https://marketing-provider.external/.well-known/agent.json")
    # Send an Intent — outbound decree gate fires BEFORE network request
    response = client.send(
        agent_url="https://marketing-provider.external/agent",
        intent_request=IntentRequest(
            id="r-1",
            params={
                "intent_id": "i-1",
                "description": "send user email to marketing provider",
                "operation": "email.send",
                "payload": {"to": "user@example.com", "body": "..."},
            },
        ),
    )
    if response.is_blocked():
        print("Outbound decree blocked:", response.error.message)
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from agent_card import AgentCard, AgentCardError
from agent_mesh import (
    DecreeBlockResponse, IntentRequest, IntentResponse,
    DECREE_BLOCK_ERROR_CODE,
)


# Outbound decree scope — used when no explicit scope is passed.
# Allows the human to issue decrees that apply only to outbound traffic
# (e.g. "never send PII to external services" with scope="outbound").
DEFAULT_OUTBOUND_SCOPE = "outbound"

# JSON-RPC error code for outbound-specific blocks (same as inbound).
DECREE_BLOCK_OUTBOUND_ERROR_CODE = -32603


class A2AClientError(RuntimeError):
    """Raised when A2A client fails (network, parse, or other errors)."""
    pass


@dataclass
class OutboundBlockResponse:
    """Response when an outbound Intent is blocked by a decree BEFORE
    the network request is sent. Per ADR-0025."""
    code: int = DECREE_BLOCK_OUTBOUND_ERROR_CODE
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


class A2AClient:
    """Decree-Driven A2A Client — outbound decree enforcement (per ADR-0025).

    When polymath-os acts as a CLIENT to external A2A-compatible agents,
    this client checks the Intent against the human's decrees BEFORE
    sending any network request. Sensitive data that would violate a
    decree never leaves the system.

    Backward compatible: pass decree_log=None to skip outbound enforcement
    (just a plain HTTP POST A2A client).
    """

    def __init__(
        self,
        decree_log=None,
        default_scope: str = DEFAULT_OUTBOUND_SCOPE,
        user_agent: str = "polymath-os-a2a-client/v3.11.0",
        timeout: float = 30.0,
        ledger=None,
    ):
        """Initialize the A2A client.

        Args:
            decree_log: DecreeLog instance (or None — skip outbound enforcement)
            default_scope: default scope for outbound checks (default "outbound")
            user_agent: User-Agent header for HTTP requests
            timeout: HTTP request timeout in seconds
            ledger: optional EvidenceLedger for audit trail
        """
        self.decree_log = decree_log
        self.default_scope = default_scope
        self.user_agent = user_agent
        self.timeout = timeout
        self.ledger = ledger
        # Event log (for testing without external ledger)
        self._events: list = []

    def discover(self, agent_url: str) -> AgentCard:
        """Fetch an Agent Card from a `.well-known/agent.json` endpoint.

        Args:
            agent_url: full URL to the agent's discovery endpoint
                       (typically "https://host/.well-known/agent.json")

        Returns:
            AgentCard instance

        Raises:
            A2AClientError: if fetch fails or card invalid
        """
        try:
            req = urllib.request.Request(
                agent_url,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise A2AClientError(f"HTTP {e.code} fetching agent card from {agent_url}: {e.reason}")
        except urllib.error.URLError as e:
            raise A2AClientError(f"URL error fetching agent card from {agent_url}: {e.reason}")
        except Exception as e:
            raise A2AClientError(f"Error fetching agent card from {agent_url}: {e}")

        try:
            return AgentCard.from_json(body)
        except AgentCardError as e:
            raise A2AClientError(f"Agent card from {agent_url} is invalid: {e}")

    def check_outbound(self, intent_description: str, scope: Optional[str] = None) -> Dict[str, Any]:
        """Pre-check an Intent description against outbound decrees.

        Public method — callers can use this to verify BEFORE composing
        the full IntentRequest (e.g. to decide whether to ask the human
        for an override).

        Returns:
            Dict with 'compliant', 'violations', 'laws_checked' fields.
            If no decree_log attached, returns {'compliant': True, ...}.
        """
        if self.decree_log is None:
            return {"compliant": True, "violations": [], "laws_checked": 0}
        return self.decree_log.check_compliance(
            intent_description, scope=scope or self.default_scope
        )

    def send(self, agent_url: str, request: IntentRequest, scope: Optional[str] = None) -> IntentResponse:
        """Send an Intent to an external A2A agent.

        The outbound decree gate fires BEFORE the network request.
        If the decree blocks, returns IntentResponse with error set
        to OutboundBlockResponse — the network request is never sent.

        Args:
            agent_url: full URL to the agent's JSON-RPC endpoint
            request: IntentRequest to send
            scope: optional override for decree_scope
                    (default: self.default_scope = "outbound")

        Returns:
            IntentResponse — either success result or DECREE_BLOCK error.
            For network errors, returns IntentResponse with error set
            to a generic error response (not a decree block).
        """
        effective_scope = scope or request.decree_scope_override or self.default_scope

        # OUTBOUND DECREE GATE — ADR-0025 core.
        # Check BEFORE any network request.
        if self.decree_log is not None:
            compliance = self.decree_log.check_compliance(
                request.description, scope=effective_scope
            )
            if not compliance.get("compliant", True):
                violations = compliance.get("violations", [])
                if violations:
                    v = violations[0]
                    error_msg = (
                        f"OUTBOUND_DECREE_BLOCK: intent violates decree #{v.get('decree_seq', '?')} "
                        f"'{v.get('decree_text', '')[:80]}' "
                        f"(matched term: {v.get('matched_term', '?')})"
                    )
                    block_response = OutboundBlockResponse(
                        code=DECREE_BLOCK_OUTBOUND_ERROR_CODE,
                        message=error_msg,
                        data={
                            "direction": "outbound",
                            "agent_url": agent_url,
                            "decree_seq": v.get("decree_seq"),
                            "decree_text": v.get("decree_text"),
                            "matched_term": v.get("matched_term"),
                            "violation": v.get("violation"),
                            "laws_checked": compliance.get("laws_checked", 0),
                            "all_violations": violations,
                        },
                    )
                    self._emit("OUTBOUND_DECREE_BLOCK", {
                        "agent_url": agent_url,
                        "intent_id": request.intent_id,
                        "description": request.description,
                        "decree_scope": effective_scope,
                        "block": block_response.to_dict(),
                    })
                    # Return as IntentResponse with error field
                    return IntentResponse(
                        jsonrpc="2.0",
                        error=DecreeBlockResponse(
                            code=block_response.code,
                            message=block_response.message,
                            data=block_response.data,
                        ),
                        id=request.id,
                    )

        # Decree gate passed — send the actual network request.
        request_body = {
            "jsonrpc": "2.0",
            "method": request.method,
            "params": request.params,
            "id": request.id,
        }
        try:
            req = urllib.request.Request(
                agent_url,
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "User-Agent": self.user_agent,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                response_body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # Try to parse error response body
            try:
                body = e.read().decode("utf-8", errors="replace")
                parsed = json.loads(body) if body else {}
                error_data = parsed.get("error", {})
                return IntentResponse(
                    jsonrpc="2.0",
                    error=DecreeBlockResponse(
                        code=error_data.get("code", -32603),
                        message=error_data.get("message", f"HTTP {e.code}: {e.reason}"),
                        data={"agent_url": agent_url, "http_status": e.code, **error_data.get("data", {})},
                    ),
                    id=request.id,
                )
            except (json.JSONDecodeError, ValueError):
                return IntentResponse(
                    jsonrpc="2.0",
                    error=DecreeBlockResponse(
                        code=-32603,
                        message=f"HTTP {e.code} from {agent_url}: {e.reason}",
                        data={"agent_url": agent_url, "http_status": e.code},
                    ),
                    id=request.id,
                )
        except urllib.error.URLError as e:
            return IntentResponse(
                jsonrpc="2.0",
                error=DecreeBlockResponse(
                    code=-32603,
                    message=f"Network error reaching {agent_url}: {e.reason}",
                    data={"agent_url": agent_url, "exception_type": type(e).__name__},
                ),
                id=request.id,
            )

        # Parse successful response.
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as e:
            return IntentResponse(
                jsonrpc="2.0",
                error=DecreeBlockResponse(
                    code=-32700,
                    message=f"Invalid JSON response from {agent_url}: {e}",
                    data={"agent_url": agent_url, "response_excerpt": response_body[:200]},
                ),
                id=request.id,
            )

        # Check if remote returned an error.
        if "error" in parsed:
            remote_err = parsed["error"]
            return IntentResponse(
                jsonrpc="2.0",
                error=DecreeBlockResponse(
                    code=remote_err.get("code", -32603),
                    message=remote_err.get("message", "remote error"),
                    data={"agent_url": agent_url, **remote_err.get("data", {})},
                ),
                id=request.id,
            )

        # Success.
        self._emit("OUTBOUND_INTENT_SENT", {
            "agent_url": agent_url,
            "intent_id": request.intent_id,
            "description": request.description,
            "decree_scope": effective_scope,
            "result": parsed.get("result"),
        })
        return IntentResponse(
            jsonrpc="2.0",
            result=parsed.get("result", {}),
            id=request.id,
        )

    def federate_decrees(self, agent_url: str) -> list:
        """Fetch active laws from a remote AgentMeshServer instance.

        Per ADR-0029 (v3.16.0) — federation: remote instances expose
        ``decree.get_active_laws`` as a read-only JSON-RPC method on
        ``POST /agent/{agent_id}``. This method issues that call and
        returns the remote's active law decrees as a list.

        This is a READ-ONLY federation operation: it does NOT carry any
        intent/payload that could leak sensitive data, so the outbound
        decree gate is not consulted. The remote decree log's contents
        are the authoritative source — we trust the remote (the operator
        explicitly asked us to federate from it).

        Args:
            agent_url: full URL to the remote JSON-RPC endpoint
                       (e.g. ``http://peer.local:7654/agent/singulyar-eir.local``)

        Returns:
            List of active-law decree dicts (as returned by the remote's
            ``DecreeLog.get_active_laws()``). Empty list on any error
            (network failure, JSON parse error, remote JSON-RPC error)
            — keeps federation fail-soft so a flaky peer doesn't break
            local operations.
        """
        request_body = {
            "jsonrpc": "2.0",
            "method": "decree.get_active_laws",
            "params": {},
            "id": f"federate-{int(time.time() * 1000)}",
        }
        try:
            req = urllib.request.Request(
                agent_url,
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "User-Agent": self.user_agent,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                response_body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": f"HTTP {e.code}: {e.reason}",
            })
            return []
        except urllib.error.URLError as e:
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": f"URL error: {e.reason}",
            })
            return []
        except Exception as e:  # federation is fail-soft by design
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": f"{type(e).__name__}: {e}",
            })
            return []

        # Parse the JSON-RPC response envelope.
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as e:
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": f"invalid JSON: {e}",
            })
            return []

        if not isinstance(parsed, dict) or "error" in parsed:
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": parsed.get("error") if isinstance(parsed, dict) else "non-object response",
            })
            return []

        result = parsed.get("result", [])
        if not isinstance(result, list):
            self._emit("FEDERATE_DECREES_ERROR", {
                "agent_url": agent_url,
                "error": f"expected list result, got {type(result).__name__}",
            })
            return []

        self._emit("FEDERATE_DECREES_FETCHED", {
            "agent_url": agent_url,
            "count": len(result),
        })
        return result

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit event to internal log + optional external ledger."""
        event = {
            "event": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **payload,
        }
        self._events.append(event)
        if self.ledger is not None:
            try:
                self.ledger.append(event_type, payload)
            except Exception:
                pass

    def events(self):
        """Return event log (for testing/debugging)."""
        return list(self._events)

    def reset_events(self):
        """Clear event log."""
        self._events.clear()
