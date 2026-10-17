"""runtime/src/agent_mesh.py — Decree-Enforced Multi-Agent Communication (per ADR-0024).

The AgentMesh is the local registry of agents and the decree-enforced
routing layer. When Agent A sends an Intent to Agent B, the mesh:

1. Looks up Agent B's decree_scope (from its Agent Card)
2. Calls `decree_log.check_compliance(intent.description, scope=agent_b.decree_scope)`
3. If decree violations → returns DECREE_BLOCK response (no execution)
4. Otherwise → forwards the Intent to Agent B's execute method
5. Records all events in the Evidence Ledger

This is the **unique emergent СИНГУЛЯР property** of Polymath OS:
no other agent system has decree-enforced multi-agent communication.
Standard A2A (Google) and MCP (Anthropic) trust agents; Polymath-OS
treats the human's decrees as supreme law above agent autonomy.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agent_card import AgentCard


# Pre-defined response codes (A2A-style, JSON-RPC 2.0 error codes).
DECREE_BLOCK_ERROR_CODE = -32603  # standard JSON-RPC "internal error" — we repurpose
DECREE_BLOCK_ERROR_MESSAGE = "DECREE_BLOCK: intent violates decree #{seq} '{decree}' (matched term: {term})"


@dataclass
class DecreeBlockResponse:
    """Response when an Intent is blocked by a decree.

    Per ADR-0024 — the standard A2A error format, extended with
    decree-specific fields in `data`.
    """
    code: int = DECREE_BLOCK_ERROR_CODE
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


@dataclass
class IntentRequest:
    """An Intent being routed through the mesh.

    Per ADR-0024 — JSON-RPC 2.0 style request.
    """
    jsonrpc: str = "2.0"
    method: str = "intent.execute"
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    # Convenience accessors for params.
    @property
    def intent_id(self) -> str:
        return self.params.get("intent_id", "")

    @property
    def description(self) -> str:
        return self.params.get("description", "")

    @property
    def operation(self) -> str:
        return self.params.get("operation", "")

    @property
    def payload(self) -> Dict[str, Any]:
        return self.params.get("payload", {})

    @property
    def decree_scope_override(self) -> Optional[str]:
        """Caller can override the target agent's decree_scope.

        Use with caution — typically None (use agent's default scope).
        """
        return self.params.get("decree_scope")


@dataclass
class IntentResponse:
    """Response to an IntentRequest — either success or DECREE_BLOCK."""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[DecreeBlockResponse] = None
    id: str = ""

    def is_blocked(self) -> bool:
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result or {}
        return d


class AgentMesh:
    """Local registry of agents + decree-enforced routing.

    Per ADR-0024. The mesh is the single point through which all
    inter-agent communication flows. This is what makes Polymath OS
    singular — no agent can bypass the decree gate.

    Usage:
        mesh = AgentMesh(decree_log=dl)
        mesh.register(SINGULYAR_EIR_CARD, execute_fn=lambda intent: {"state": "CONFIRMED"})
        response = mesh.send("singulyar-eir.local", IntentRequest(
            id="req-1",
            params={"intent_id": "i-1", "description": "publish note", "operation": "send"}
        ))
        if response.is_blocked():
            print("decree blocked:", response.error.message)
    """

    def __init__(self, decree_log=None, ledger=None):
        """Initialize the mesh.

        Args:
            decree_log: DecreeLog instance (or None — no decree enforcement)
            ledger: optional EvidenceLedger for audit trail
        """
        self.decree_log = decree_log
        self.ledger = ledger
        # agent_id -> (AgentCard, execute_fn)
        self._agents: Dict[str, tuple] = {}
        # event log for the mesh itself (for testing without external ledger)
        self._events: List[Dict[str, Any]] = []

    def register(self, card: AgentCard, execute_fn: Callable[[IntentRequest], Dict[str, Any]]) -> None:
        """Register an agent with its card and execute function.

        Args:
            card: AgentCard describing the agent
            execute_fn: function called with IntentRequest when intent passes decree gate.
                        Must return dict with at least {"state": "CONFIRMED"|"WAITING_FOR_HUMAN"|...}.
        """
        if card.id in self._agents:
            raise ValueError(f"Agent {card.id} already registered")
        self._agents[card.id] = (card, execute_fn)
        self._emit("AGENT_REGISTERED", {"agent_id": card.id, "decree_scope": card.decree_scope})

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the mesh."""
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        self._emit("AGENT_UNREGISTERED", {"agent_id": agent_id})
        return True

    def list_agents(self) -> List[AgentCard]:
        """List all registered agents."""
        return [card for card, _ in self._agents.values()]

    def discover(self, capability: str) -> List[AgentCard]:
        """Find all agents that advertise a given capability."""
        return [card for card, _ in self._agents.values() if capability in card.capabilities]

    def send(self, agent_id: str, request: IntentRequest) -> IntentResponse:
        """Route an Intent to an agent with decree enforcement.

        This is the core of ADR-0024 — every inter-agent message is
        checked against the human's decrees BEFORE execution.

        Args:
            agent_id: target agent id (must be registered)
            request: IntentRequest with description, operation, payload

        Returns:
            IntentResponse — either successful result or DECREE_BLOCK error
        """
        # Validate agent is registered.
        if agent_id not in self._agents:
            return IntentResponse(
                jsonrpc="2.0",
                error=DecreeBlockResponse(
                    code=-32602,  # JSON-RPC "method not found" — repurposed for unknown agent
                    message=f"AGENT_NOT_FOUND: no agent with id '{agent_id}' registered in mesh",
                ),
                id=request.id,
            )

        card, execute_fn = self._agents[agent_id]

        # Determine decree scope: caller override OR agent's default.
        scope = request.decree_scope_override or card.decree_scope

        # DECREE GATE — check compliance BEFORE calling execute_fn.
        # This is the unique emergent property of Polymath-OS.
        if self.decree_log is not None:
            compliance = self.decree_log.check_compliance(
                request.description, scope=scope
            )
            if not compliance.get("compliant", True):
                violations = compliance.get("violations", [])
                if violations:
                    v = violations[0]
                    error_msg = DECREE_BLOCK_ERROR_MESSAGE.format(
                        seq=v.get("decree_seq", "?"),
                        decree=v.get("decree_text", "")[:80],
                        term=v.get("matched_term", "?"),
                    )
                    block_response = DecreeBlockResponse(
                        code=DECREE_BLOCK_ERROR_CODE,
                        message=error_msg,
                        data={
                            "agent_id": agent_id,
                            "decree_seq": v.get("decree_seq"),
                            "decree_text": v.get("decree_text"),
                            "matched_term": v.get("matched_term"),
                            "violation": v.get("violation"),
                            "laws_checked": compliance.get("laws_checked", 0),
                            "all_violations": violations,
                        },
                    )
                    self._emit("DECREE_BLOCK", {
                        "agent_id": agent_id,
                        "intent_id": request.intent_id,
                        "description": request.description,
                        "decree_scope": scope,
                        "block": block_response.to_dict(),
                    })
                    return IntentResponse(
                        jsonrpc="2.0",
                        error=block_response,
                        id=request.id,
                    )

        # Decree gate passed — forward to execute_fn.
        try:
            result = execute_fn(request)
            self._emit("INTENT_EXECUTED", {
                "agent_id": agent_id,
                "intent_id": request.intent_id,
                "description": request.description,
                "decree_scope": scope,
                "result": result,
            })
            return IntentResponse(
                jsonrpc="2.0",
                result=result,
                id=request.id,
            )
        except Exception as e:
            # Agent execution raised — record and return error.
            self._emit("INTENT_ERROR", {
                "agent_id": agent_id,
                "intent_id": request.intent_id,
                "error": str(e),
            })
            return IntentResponse(
                jsonrpc="2.0",
                error=DecreeBlockResponse(
                    code=-32603,
                    message=f"AGENT_ERROR: {type(e).__name__}: {e}",
                    data={"agent_id": agent_id, "exception_type": type(e).__name__},
                ),
                id=request.id,
            )

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an event to the mesh log AND external ledger if attached."""
        event = {
            "event": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **payload,
        }
        self._events.append(event)
        # Also append to external ledger if attached (for production audit trail).
        if self.ledger is not None:
            try:
                self.ledger.append(event_type, payload)
            except Exception:
                pass  # don't fail the mesh if ledger fails

    def events(self) -> List[Dict[str, Any]]:
        """Return all events emitted by this mesh (for testing/debugging)."""
        return list(self._events)

    def reset_events(self) -> None:
        """Clear the mesh's internal event log."""
        self._events.clear()
