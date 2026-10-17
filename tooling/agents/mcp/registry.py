"""MCP capability registry — lookup table consulted by SINGULYAR EIR's planner.

SINGULYAR EIR (Layer 5) calls the registry to find a `Capability` for a given
operation subject to hard constraints (`local_only`, `offline`, risk ceiling).
The kernel's `Runtime._advance` already does this for in-process capabilities;
this registry is the *external* entry point — agents and AI workflows
register their MCP-backed capabilities here, and the kernel pulls them in.

Layering::

    AI workflow / agent
          │ registers Capability(operation, adapter_id, risk_ceiling, ...)
          ▼
    MCPCapabilityRegistry
          │ find_compatible(operation, constraints)
          ▼
    SINGULYAR EIR Runtime
          │ pick lowest-priority compatible Capability
          │ invoke Adapter.execute(intent, idempotency_key)
          ▼
    MCPAdapter subclass → MCP server

Hard constraints (per ADR-0012 §"Интеграционные точки" + singulyar_runtime.Policy):
  * `local_only=True` required → adapter MUST declare `local_only=True`
  * `offline=True`    required → adapter MUST declare `offline=True`
  * `risk_floor` floor → adapter's `risk_ceiling` MUST be >= intent's risk

Hard constraints are NEVER silently downgraded — if no capability satisfies,
`find_compatible` returns an empty list and the kernel blocks the intent
(WAITING_FOR_HUMAN), never auto-relaxes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .base_adapter import (
    Capability,
    RISK_RANK,
)
from .filesystem_adapter import FilesystemAdapter
from .git_adapter import GitAdapter
from .postgres_adapter import PostgresAdapter
from .web_search_adapter import WebSearchAdapter


class MCPCapabilityRegistry:
    """In-memory registry of `Capability` declarations.

    The registry is the SINGULYAR EIR planner's catalogue: it answers
    "given operation X with constraints Y, which adapters can serve it,
    and in what priority order?". Lookup is deterministic: capabilities
    are returned sorted by `priority` (lower = preferred).
    """

    def __init__(self, capabilities: Optional[Sequence[Capability]] = None):
        self._caps: List[Capability] = []
        self._by_id: Dict[str, Capability] = {}
        if capabilities:
            for c in capabilities:
                self.register(c)

    # -- mutation ---------------------------------------------------------
    def register(self, capability: Capability) -> None:
        """Add a Capability. Raises ValueError on duplicate capability_id."""
        if capability.capability_id in self._by_id:
            raise ValueError(
                f"capability_id already registered: {capability.capability_id}"
            )
        # Validate fields (cheap structural check; full schema lives in
        # runtime/schemas/capability.schema.json).
        _validate_capability(capability)
        self._caps.append(capability)
        self._by_id[capability.capability_id] = capability

    def register_many(self, capabilities: Sequence[Capability]) -> None:
        for c in capabilities:
            self.register(c)

    # -- queries ----------------------------------------------------------
    def find_compatible(
        self,
        operation: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[Capability]:
        """Return capabilities matching `operation` and not violating constraints.

        Hard constraints (never silently downgraded):
          * `local_only=True`  → cap.local_only must be True
          * `offline=True`     → cap.offline must be True
          * `risk_floor`       → cap.risk_ceiling rank >= risk_floor rank
          * `idempotent_only`  → cap.idempotent must be True (used by recover())

        Returns capabilities sorted by priority (ascending = first preferred).
        """
        c = constraints or {}
        require_local = bool(c.get("local_only", False))
        require_offline = bool(c.get("offline", False))
        risk_floor = c.get("risk_floor")  # one of "low"|"medium"|"high"
        idempotent_only = bool(c.get("idempotent_only", False))

        floor_rank = RISK_RANK.get(risk_floor, -1) if risk_floor else -1

        matched: List[Capability] = []
        for cap in self._caps:
            if cap.operation != operation:
                continue
            if require_local and not cap.local_only:
                continue
            if require_offline and not cap.offline:
                continue
            if idempotent_only and not cap.idempotent:
                continue
            if risk_floor and RISK_RANK[cap.risk_ceiling] < floor_rank:
                continue
            matched.append(cap)
        # Stable sort by priority (lower = preferred first).
        return sorted(matched, key=lambda cap: cap.priority)

    def all(self) -> List[Capability]:
        """All registered capabilities, sorted by (operation, priority)."""
        return sorted(self._caps, key=lambda c: (c.operation, c.priority))

    def by_id(self, capability_id: str) -> Optional[Capability]:
        return self._by_id.get(capability_id)

    def __len__(self) -> int:
        return len(self._caps)

    def __contains__(self, capability_id: object) -> bool:
        return capability_id in self._by_id


def _validate_capability(cap: Capability) -> None:
    """Cheap structural validation. Mirrors capability.schema.json constraints."""
    if not cap.capability_id:
        raise ValueError("capability_id must be non-empty")
    if not cap.operation:
        raise ValueError("operation must be non-empty")
    if not cap.adapter_id:
        raise ValueError("adapter_id must be non-empty")
    if cap.risk_ceiling not in RISK_RANK:
        raise ValueError(f"risk_ceiling must be one of {list(RISK_RANK)}, got {cap.risk_ceiling!r}")
    if not isinstance(cap.offline, bool):
        raise ValueError("offline must be bool")
    if not isinstance(cap.idempotent, bool):
        raise ValueError("idempotent must be bool")
    if not isinstance(cap.local_only, bool):
        raise ValueError("local_only must be bool")
    if not isinstance(cap.priority, int) or cap.priority < 0:
        raise ValueError("priority must be a non-negative int")


def default_registry() -> MCPCapabilityRegistry:
    """Registry pre-populated with all built-in MCP adapter capabilities.

    Convenience for `python -m tooling.agents.mcp list` and for tests
    that just want "the canonical set". Production code typically
    constructs its own registry from a config file.
    """
    r = MCPCapabilityRegistry()
    r.register_many(FilesystemAdapter.CAPABILITIES)
    r.register_many(GitAdapter.CAPABILITIES)
    r.register_many(PostgresAdapter.CAPABILITIES)
    r.register_many(WebSearchAdapter.CAPABILITIES)
    return r
