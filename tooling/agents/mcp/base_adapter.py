"""Base MCP adapter bridging MCP server tools to the SINGULYAR EIR `Adapter` interface.

Layering (ADR-0008, ADR-0012)::

    ┌──────────────────────────────────────────────────────────────┐
    │  SINGULYAR EIR (Layer 5) — Runtime / planner / verifier      │
    │      calls Adapter.execute(intent, key)                       │
    │             Adapter.read_state(intent, key) → Observation     │
    │      consults MCPCapabilityRegistry to pick Capability        │
    └──────────────────────────────────────────────────────────────┘
                            ↓ uses
    ┌──────────────────────────────────────────────────────────────┐
    │  MCPAdapter (this module) — thin internal adapter            │
    │      maps SINGULYAR operation → MCP tool name                 │
    │      dispatches JSON-RPC call to MCP server                   │
    │      translates MCP result → SINGULYAR Observation            │
    └──────────────────────────────────────────────────────────────┘
                            ↓ JSON-RPC (stdio/SSE/HTTP)
    ┌──────────────────────────────────────────────────────────────┐
    │  MCP server (filesystem / git / postgres / web-search)        │
    └──────────────────────────────────────────────────────────────┘

If MCP spec changes — only this adapter layer is touched, never business logic.

Scaffold semantics (per task 5-E):
  * stdlib only — `_call_mcp_tool` is an in-process stub simulating an MCP server.
  * Real implementation would dispatch `tools/call` JSON-RPC over stdio/SSE/HTTP
    (see https://modelcontextprotocol.io/specification).
  * `read_state` MUST return an `Observation` with status in
    {PRESENT, ABSENT, UNAVAILABLE} — never `None`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# --- sys.path bootstrap -----------------------------------------------------
# We import singulyar_runtime as a *namespace package* path
# `runtime.src.singulyar_runtime`. That requires:
#   1. the repo root on sys.path (so `runtime` resolves as a namespace pkg)
#   2. `runtime/src/` on sys.path (so the inner `from schema_validate import ...`
#      inside singulyar_runtime.py resolves).
# Both additions are idempotent and only affect the importing process.
_REPO_ROOT = Path(__file__).resolve().parents[3]  # tooling/agents/mcp → repo root
_RUNTIME_SRC = _REPO_ROOT / "runtime" / "src"
for _p in (str(_REPO_ROOT), str(_RUNTIME_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runtime.src.singulyar_runtime import (  # noqa: E402  (post-sys.path import)
    Adapter,
    Intent,
    Capability,
    Observation,
    PRESENT,
    ABSENT,
    UNAVAILABLE,
    NotExecuted,
)

# ---------------------------------------------------------------------------
# MCP version pin (ADR-0008 §2): the stateless-core spec revision that every
# adapter in this package is tested against. Bumping this requires a migration
# ADR per ADR-0008 §3.
# ---------------------------------------------------------------------------
MCP_VERSION = "2026-07-28"

# Risk ranking mirrors singulyar_runtime.Policy.RISK so the registry can refuse
# a capability whose ceiling is below the intent's risk without importing Policy.
RISK_RANK = {"low": 0, "medium": 1, "high": 2}


class MCPAdapter(Adapter):
    """Abstract bridge: SINGULYAR `Adapter` interface ⇄ MCP server tool.

    Subclasses MUST:
      * set `adapter_id` and `mcp_server` class attributes
      * declare `CAPABILITIES` (tuple of `Capability` dataclasses)
      * implement `_call_mcp_tool(tool_name, arguments, idempotency_key)`
        (or override `execute` and `read_state` entirely)

    The contract with SINGULYAR EIR is fixed:
      * `execute(intent, idempotency_key)` is called BEFORE the ledger's
        "ADAPTER_RETURN" event is written; side effects may have happened.
      * `read_state(intent, idempotency_key)` MUST return an `Observation`:
            - PRESENT  → effect exists with this key (verifier compares value/count)
            - ABSENT   → effect definitely did NOT happen (safe to retry if cap.idempotent)
            - UNAVAILABLE → cannot tell (treated as UNKNOWN; no blind retry)
        Returning `None` is forbidden — it would erase the ABSENT/UNAVAILABLE
        distinction that the verifier relies on (see singulyar_runtime.recover).
    """

    adapter_id = "mcp-abstract"
    mcp_server = "abstract"  # MCP server name (used to prefix tool names)
    CAPABILITIES: tuple = ()

    def __init__(self, mcp_endpoint: Optional[str] = None, *, available: bool = True):
        """`mcp_endpoint` is the URI of the MCP server (stdio://, http://, sse://).
        `available=False` simulates the server being down → `read_state` returns UNAVAILABLE.
        """
        self.mcp_endpoint = mcp_endpoint or f"stdio://{self.mcp_server}"
        self.available = available
        # In-memory record of effects written under each idempotency_key.
        # Real impl: the MCP server dedupes; we mirror it here for scaffolds.
        self._effects: Dict[str, Dict[str, Any]] = {}

    # -- contract: Adapter.execute -----------------------------------------
    def execute(self, intent: Intent, idempotency_key: str):
        if not self.available:
            raise NotExecuted(f"MCP server {self.mcp_server} not available")
        tool = self._tool_for_operation(intent.operation)
        args = dict(intent.payload)
        # SINGULYAR's idempotency key is passed to the MCP server as the dedupe key.
        # Per MCP stateless core, the server MUST return the same result for the
        # same key+args combination when the underlying operation is idempotent.
        args["_idempotency_key"] = idempotency_key
        try:
            result = self._call_mcp_tool(tool, args, idempotency_key)
        except NotExecuted:
            raise
        except Exception as exc:  # noqa: BLE001 — surface any MCP-side failure to the kernel
            # The kernel treats this as UNKNOWN (effect may or may not have happened).
            raise RuntimeError(f"MCP tool {tool} failed: {exc}") from exc
        # Record the effect locally so read_state can return PRESENT without
        # re-querying the server in the scaffold. Real impl queries the server.
        self._effects[idempotency_key] = result
        return {"accepted": True, "idempotency_key": idempotency_key, "result": result}

    # -- contract: Adapter.read_state -------------------------------------
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        if not self.available:
            return Observation(UNAVAILABLE)
        items = self._effects.get(idempotency_key)
        if not items:
            return Observation(ABSENT, None, 0)
        return Observation(PRESENT, dict(items), 1)

    # -- subclass hooks ----------------------------------------------------
    def _tool_for_operation(self, operation: str) -> str:
        """Map a SINGULYAR operation to an MCP tool name.

        Default convention: `<mcp_server>_<operation>` (e.g. `filesystem_write_file`).
        Subclasses may override to use the MCP server's actual tool names.
        """
        return f"{self.mcp_server}_{operation}"

    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Stub for the MCP `tools/call` JSON-RPC.

        Subclasses MUST override this (or override `execute` directly).
        Real implementation would do something like::

            async with stdio_client(server_params) as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()  # removed in stateless core
                    return await s.call_tool(tool_name, arguments)

        Returns the tool result as a dict (the MCP server's `content` payload).
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _call_mcp_tool "
            f"(tool={tool_name}, key={idempotency_key})"
        )
