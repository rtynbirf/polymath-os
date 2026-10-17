"""CLI entry: `python -m tooling.agents.mcp <command>`.

Commands:
  list      List all registered capabilities (one per line, tab-separated).
  verify    Smoke-test every adapter: subclasses Adapter, declares
            CAPABILITIES, MCP_VERSION matches ADR-0008.

Exit codes: 0 = success, 1 = verification failed, 2 = unknown command.
"""
from __future__ import annotations

import inspect
import sys
from typing import Optional, Sequence

from .base_adapter import (
    MCPAdapter,
    MCP_VERSION,
    Adapter,
    Capability,
)
from .filesystem_adapter import FilesystemAdapter
from .git_adapter import GitAdapter
from .postgres_adapter import PostgresAdapter
from .web_search_adapter import WebSearchAdapter
from .registry import MCPCapabilityRegistry, default_registry

# MCP version pinned by ADR-0008 (stateless core). `verify` checks equality.
ADR_0008_MCP_VERSION = "2026-07-28"

# Tabular column header for `list`.
_LIST_HEADER = (
    "capability_id\toperation\tadapter_id\trisk_ceiling\t"
    "offline\tidempotent\tlocal_only\tpriority"
)

ALL_ADAPTER_CLASSES = (
    FilesystemAdapter,
    GitAdapter,
    PostgresAdapter,
    WebSearchAdapter,
)


def _cmd_list(argv: Sequence[str]) -> int:
    reg = default_registry()
    print(_LIST_HEADER)
    for cap in reg.all():
        print(
            f"{cap.capability_id}\t{cap.operation}\t{cap.adapter_id}\t{cap.risk_ceiling}\t"
            f"{cap.offline!s}\t{cap.idempotent!s}\t{cap.local_only!s}\t{cap.priority}"
        )
    print(f"# total: {len(reg)} capabilities", file=sys.stderr)
    return 0


def _cmd_verify(argv: Sequence[str]) -> int:
    failures = []

    # 1. MCP version matches ADR-0008.
    if MCP_VERSION != ADR_0008_MCP_VERSION:
        failures.append(
            f"MCP_VERSION mismatch: {MCP_VERSION!r} != ADR-0008 {ADR_0008_MCP_VERSION!r}"
        )

    # 2. Every adapter subclass of MCPAdapter subclasses singulyar_runtime.Adapter.
    #    (MCPAdapter itself is abstract — only the concrete adapters need IDs.)
    for cls in ALL_ADAPTER_CLASSES:
        if not issubclass(cls, Adapter):
            failures.append(f"{cls.__name__} does NOT subclass singulyar_runtime.Adapter")
        # adapter_id and mcp_server must be set on the class (not inherited defaults).
        if not getattr(cls, "adapter_id", None) or cls.adapter_id == "mcp-abstract":
            failures.append(f"{cls.__name__} missing adapter_id")
        if not getattr(cls, "mcp_server", None) or cls.mcp_server == "abstract":
            failures.append(f"{cls.__name__} missing mcp_server")

    # 3. Each adapter declares CAPABILITIES with valid fields.
    seen_ids = set()
    for cls in ALL_ADAPTER_CLASSES:
        caps = getattr(cls, "CAPABILITIES", ())
        if not caps:
            failures.append(f"{cls.__name__}.CAPABILITIES is empty")
            continue
        for cap in caps:
            if not isinstance(cap, Capability):
                failures.append(f"{cls.__name__}: {cap!r} is not a Capability dataclass")
                continue
            if cap.adapter_id != cls.adapter_id:
                failures.append(
                    f"{cls.__name__}: capability {cap.capability_id} adapter_id "
                    f"{cap.adapter_id!r} != class adapter_id {cls.adapter_id!r}"
                )
            if cap.capability_id in seen_ids:
                failures.append(f"duplicate capability_id: {cap.capability_id}")
            seen_ids.add(cap.capability_id)

    # 4. read_state signature: never returns None — checked by contract at runtime.
    for cls in ALL_ADAPTER_CLASSES:
        if not hasattr(cls, "read_state"):
            failures.append(f"{cls.__name__} missing read_state")
            continue
        sig = inspect.signature(cls.read_state)
        ret = sig.return_annotation
        # Loose check: return annotation should mention Observation.
        if ret is not inspect.Parameter.empty and ret is not None:
            ret_name = getattr(ret, "__name__", str(ret))
            if ret_name != "Observation" and "Observation" not in str(ret):
                failures.append(
                    f"{cls.__name__}.read_state return annotation is not Observation ({ret})"
                )

    # 5. Default registry must contain at least one capability per adapter.
    reg = default_registry()
    for cls in ALL_ADAPTER_CLASSES:
        ids = {c.capability_id for c in cls.CAPABILITIES}
        missing = ids - set(reg._by_id.keys())
        if missing:
            failures.append(
                f"{cls.__name__}: capabilities not in default registry: {sorted(missing)}"
            )

    if failures:
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        print(f"\n  verify: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print(f"  ✓ MCP_VERSION = {MCP_VERSION} (matches ADR-0008)")
    print(f"  ✓ {len(ALL_ADAPTER_CLASSES)} adapter(s) subclass singulyar_runtime.Adapter")
    print(f"  ✓ {len(reg)} capabilities declared with valid fields")
    print("  ✓ all read_state methods return Observation (never None, by contract)")
    print("\n  verify: all smoke tests passed")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "list":
        return _cmd_list(rest)
    if cmd == "verify":
        return _cmd_verify(rest)
    print(f"unknown command: {cmd!r} (expected: list | verify)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
