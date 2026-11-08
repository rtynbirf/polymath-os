"""MCP adapters bridging Model Context Protocol server tools to the SINGULYAR EIR
`Adapter` interface (ADR-0008 + ADR-0012).

This package is a *thin internal adapter layer*: MCP server tools are not a direct
dependency of business logic. Each MCP server (filesystem, git, postgres, web-search,
...) is wrapped in an `MCPAdapter` subclass that declares the SINGULYAR `Capability`
contract for the kernel's planner and implements `execute()` / `read_state()` against
the MCP tool.

MCP version is pinned per ADR-0008 (`MCP_VERSION = "2026-07-28"`, stateless core).
Updating the version is a quarterly review with a migration ADR — see
`docs/adr/0008-mcp-version-pin.md`.

Public symbols:

    MCPAdapter            — abstract bridge: MCP tool ⇄ SINGULYAR Adapter
    FilesystemAdapter     — local FS operations (create/write/read/delete/list/append)
    GitAdapter            — git operations (commit/push/branch/checkout/merge)
    PostgresAdapter       — Postgres operations (query/migration/upsert)
    WebSearchAdapter      — web search + URL fetch
    MCPCapabilityRegistry — capability lookup used by SINGULYAR EIR planner
    MCP_VERSION           — pinned MCP spec revision (ADR-0008)

Scaffolds only: stdlib + lightweight MCP SDK pattern, no PyPI deps.
"""
from __future__ import annotations

from .base_adapter import MCPAdapter, MCP_VERSION
from .filesystem_adapter import FilesystemAdapter
from .git_adapter import GitAdapter
from .postgres_adapter import PostgresAdapter
from .web_search_adapter import WebSearchAdapter
from .registry import MCPCapabilityRegistry, default_registry

__all__ = [
    "MCPAdapter",
    "MCP_VERSION",
    "FilesystemAdapter",
    "GitAdapter",
    "PostgresAdapter",
    "WebSearchAdapter",
    "MCPCapabilityRegistry",
    "default_registry",
]
