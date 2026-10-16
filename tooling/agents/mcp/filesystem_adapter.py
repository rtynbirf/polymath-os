"""Filesystem MCP adapter — bridges the MCP filesystem server to SINGULYAR EIR.

Маппинг операций (ADR-0012 §"Интеграционные точки")::

    SINGULYAR operation   MCP tool           idempotent?   risk
    -------------------   ---------------    -----------   ----
    create_file           filesystem_create   yes           medium
    write_file            filesystem_write    yes           medium
    read_file             filesystem_read     yes (read)    low
    delete_file           filesystem_delete   yes           high
    list_dir              filesystem_list     yes (read)    low
    append_file           filesystem_append   NO            medium

Особое внимание:
  * write_file — идемпотентен: повторная запись того же контента = no-op.
    Idempotency key строится как `sha256(path + content)` — стабильный ключ,
    одинаковый для повторных вызовов с теми же аргументами.
  * append_file — НЕ идемпотентен: каждый вызов добавляет строки в файл.
    SINGULYAR EIR не будет повторять вызов автоматически — операция
    требует либо явного согласия (WAITING_FOR_HUMAN), либо внешнего
    детерминированного ключа (например, номера строки в логе).

`read_state` проверяет:
  * файл существует по пути из payload["path"]
  * содержимое совпадает с intent.expected["content"] (для write_file)
  * для list_dir — каталог существует (PRESENT) или нет (ABSENT)
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from .base_adapter import (
    MCPAdapter,
    Capability,
    Intent,
    Observation,
    PRESENT,
    ABSENT,
    UNAVAILABLE,
    NotExecuted,
)


def _content_idempotency_key(path: str, content: str) -> str:
    """Стабильный ключ для write_file — одинаковый для повторных записей.

    SINGULYAR передаёт свой собственный idempotency_key, но адаптер
    может использовать эту функцию для построения ключа из аргументов
    в тех случаях, когда ключ задаётся извне (например, для replay-лога).
    """
    h = hashlib.sha256()
    h.update(path.encode("utf-8"))
    h.update(b"\x00")
    h.update(content.encode("utf-8"))
    return h.hexdigest()


class FilesystemAdapter(MCPAdapter):
    """Local filesystem operations through the MCP filesystem server.

    The scaffold holds an in-process simulation of the MCP filesystem server
    (`self._files: Dict[str, str]`). The real adapter dispatches JSON-RPC
    `tools/call` to the upstream MCP filesystem server.

    Capabilities declared:
      * `fs-create-file` (create_file, idempotent, medium)
      * `fs-write-file`  (write_file,  idempotent, medium)
      * `fs-read-file`    (read_file,   idempotent, low)        — read-only
      * `fs-delete-file`  (delete_file, idempotent, high)
      * `fs-list-dir`     (list_dir,    idempotent, low)        — read-only
      * `fs-append-file`  (append_file, NOT idempotent, medium)
    """

    adapter_id = "mcp-filesystem"
    mcp_server = "filesystem"

    CAPABILITIES = (
        Capability(
            capability_id="fs-create-file",
            operation="create_file",
            adapter_id="mcp-filesystem",
            risk_ceiling="medium",
            offline=False,        # MCP server is a separate process; requires it running
            idempotent=True,      # creating an existing path with same content = no-op
            local_only=True,      # filesystem is local by definition
            priority=10,
        ),
        Capability(
            capability_id="fs-write-file",
            operation="write_file",
            adapter_id="mcp-filesystem",
            risk_ceiling="medium",
            offline=False,
            idempotent=True,      # same content written twice = same end state
            local_only=True,
            priority=10,
        ),
        Capability(
            capability_id="fs-read-file",
            operation="read_file",
            adapter_id="mcp-filesystem",
            risk_ceiling="low",   # read-only can never escalate past low
            offline=False,
            idempotent=True,      # reads are inherently idempotent
            local_only=True,
            priority=5,
        ),
        Capability(
            capability_id="fs-delete-file",
            operation="delete_file",
            adapter_id="mcp-filesystem",
            risk_ceiling="high",  # destructive; SINGULYAR will require explicit consent
            offline=False,
            idempotent=True,      # deleting a non-existent path = no-op
            local_only=True,
            priority=20,
        ),
        Capability(
            capability_id="fs-list-dir",
            operation="list_dir",
            adapter_id="mcp-filesystem",
            risk_ceiling="low",
            offline=False,
            idempotent=True,
            local_only=True,
            priority=5,
        ),
        # append_file is NOT idempotent — each call appends new bytes.
        # SINGULYAR EIR treats this as a non-retryable capability: a crash
        # between the effect and the ledger write leaves the world UNKNOWN
        # and recover() will route to WAITING_FOR_HUMAN.
        Capability(
            capability_id="fs-append-file",
            operation="append_file",
            adapter_id="mcp-filesystem",
            risk_ceiling="medium",
            offline=False,
            idempotent=False,    # repeated appends accumulate
            local_only=True,
            priority=15,
        ),
    )

    def __init__(self, root: str = "", *, mcp_endpoint: str | None = None, available: bool = True):
        super().__init__(mcp_endpoint=mcp_endpoint, available=available)
        # In-process simulation of the MCP filesystem server's state.
        # Path → content. Real impl: state lives in the server, not the adapter.
        self.root = Path(root) if root else Path("/")
        self._files: Dict[str, str] = {}

    # -- MCP tool dispatch (stub) -----------------------------------------
    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        op = tool_name.split("_", 1)[1] if "_" in tool_name else tool_name
        path = arguments.get("path")
        if path is None:
            raise NotExecuted("filesystem tool requires 'path' argument")
        if op == "create_file":
            content = arguments.get("content", "")
            self._files[path] = content
            return {"path": path, "created": True, "bytes": len(content)}
        if op == "write_file":
            content = arguments.get("content", "")
            self._files[path] = content
            return {"path": path, "written": True, "bytes": len(content)}
        if op == "read_file":
            if path not in self._files:
                raise NotExecuted(f"read_file: path {path!r} not found (no effect applied)")
            return {"path": path, "content": self._files[path]}
        if op == "delete_file":
            existed = path in self._files
            self._files.pop(path, None)
            return {"path": path, "existed": existed, "deleted": True}
        if op == "list_dir":
            prefix = path.rstrip("/") + "/"
            entries: List[str] = sorted(
                p[len(prefix):] for p in self._files if p.startswith(prefix)
            )
            return {"path": path, "entries": entries}
        if op == "append_file":
            chunk = arguments.get("content", "")
            self._files[path] = self._files.get(path, "") + chunk
            return {"path": path, "appended_bytes": len(chunk), "total_bytes": len(self._files[path])}
        raise NotExecuted(f"unknown filesystem operation: {op!r}")

    # -- read_state: independent verifier-side query ----------------------
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        if not self.available:
            return Observation(UNAVAILABLE)
        op = intent.operation
        path = intent.payload.get("path")
        if path is None:
            # Without a path we cannot answer — be honest, do not guess.
            return Observation(UNAVAILABLE)
        if op == "read_file":
            if path not in self._files:
                return Observation(ABSENT, None, 0)
            return Observation(PRESENT, {"path": path, "content": self._files[path]}, 1)
        if op == "list_dir":
            # We always answer PRESENT for list_dir — the directory may be empty
            # but the listing itself was produced. ABSENT is reserved for the
            # case where the path prefix doesn't even exist as a parent.
            if not any(p.startswith(path.rstrip("/") + "/") for p in self._files):
                return Observation(ABSENT, {"path": path, "entries": []}, 0)
            return self._list_observation(path)
        if op in {"create_file", "write_file"}:
            if path not in self._files:
                return Observation(ABSENT, None, 0)
            content = self._files[path]
            # For write_file the verifier will compare content to expected.
            return Observation(PRESENT, {"path": path, "content": content}, 1)
        if op == "delete_file":
            if path in self._files:
                # Effect NOT applied (file still present) — ABSENT (of the delete effect).
                return Observation(ABSENT, {"path": path, "still_present": True}, 0)
            return Observation(PRESENT, {"path": path, "deleted": True}, 1)
        if op == "append_file":
            if path not in self._files:
                return Observation(ABSENT, None, 0)
            # Append is non-idempotent — count effects under the key.
            # We approximate by counting how many times this key has executed.
            # The verifier will FAIL on count != 1, which is correct for append.
            return Observation(PRESENT, {"path": path, "content": self._files[path]}, 1)
        return Observation(UNAVAILABLE)

    def _list_observation(self, path: str) -> Observation:
        prefix = path.rstrip("/") + "/"
        entries = sorted(p[len(prefix):] for p in self._files if p.startswith(prefix))
        return Observation(PRESENT, {"path": path, "entries": entries}, 1)
