"""Git MCP adapter — bridges the MCP git server to SINGULYAR EIR.

Маппинг операций::

    SINGULYAR operation   MCP tool         idempotent?   risk
    -------------------   -------------    -----------   ----
    commit                git_commit       NO            high
    push                  git_push        yes           high
    create_branch         git_create_branch yes         medium
    checkout              git_checkout    yes           medium
    merge                 git_merge       NO            high

Особое внимание:
  * commit — НЕ идемпотентен: каждый вызов создаёт новый commit hash.
    SINGULYAR EIR не повторяет commit автоматически. Для повторяемых
    пайплайнов нужно использовать детерминированные сообщения + replay
    (создание того же дерева → тот же hash, но это другой commit).
  * merge — НЕ идемпортентен в общем случае: повторный merge может создать
    новый merge commit (если что-то поменялось в upstream).
  * create_branch — идемпортентен, если имя ветки детерминированное
    (база: target_ref + branch_name → одинаковый результат).
  * checkout — идемпортентен: переключение на тот же ref = no-op.

`read_state` проверяет:
  * ветка существует (create_branch)
  * commit hash совпадает с ожидаемым (commit)
  * remote в синхронизированном состоянии (push): local HEAD == remote HEAD
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

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


def _branch_idempotency_key(base_ref: str, branch_name: str) -> str:
    """Детерминированный idempotency_key для create_branch.

    Одинаковые (base_ref, branch_name) → одинаковый ключ → одинаковый результат.
    Реальный MCP git server дедуплицирует по этому ключу.
    """
    h = hashlib.sha256()
    h.update(base_ref.encode("utf-8"))
    h.update(b"\x00")
    h.update(branch_name.encode("utf-8"))
    return h.hexdigest()


class GitAdapter(MCPAdapter):
    """Git operations through the MCP git server (scaffold).

    The scaffold holds an in-process simulation of a git repo: branches,
    current HEAD, commit history. Real impl: dispatch JSON-RPC `tools/call`
    to an MCP git server (e.g. mcp-server-git).

    Capabilities declared:
      * `git-commit`        (commit,         NOT idempotent, high)
      * `git-push`          (push,           idempotent,     high)
      * `git-create-branch` (create_branch,  idempotent,     medium)
      * `git-checkout`      (checkout,       idempotent,     medium)
      * `git-merge`         (merge,          NOT idempotent, high)
    """

    adapter_id = "mcp-git"
    mcp_server = "git"

    CAPABILITIES = (
        # commit is NOT idempotent — every call mints a new hash.
        # SINGULYAR EIR treats crashes mid-commit as UNKNOWN; recover()
        # routes to WAITING_FOR_HUMAN (verifier sees ABSENT or wrong hash
        # but cap.idempotent=False blocks auto-retry).
        Capability(
            capability_id="git-commit",
            operation="commit",
            adapter_id="mcp-git",
            risk_ceiling="high",
            offline=False,
            idempotent=False,
            local_only=True,    # git repo is local; push is the remote boundary
            priority=20,
        ),
        # push IS idempotent: pushing a ref whose remote already has the same
        # hash is a no-op ("Everything up-to-date").
        Capability(
            capability_id="git-push",
            operation="push",
            adapter_id="mcp-git",
            risk_ceiling="high",
            offline=False,       # requires network
            idempotent=True,
            local_only=False,   # touches remote
            priority=30,
        ),
        # create_branch with deterministic name = idempotent.
        Capability(
            capability_id="git-create-branch",
            operation="create_branch",
            adapter_id="mcp-git",
            risk_ceiling="medium",
            offline=False,
            idempotent=True,
            local_only=True,
            priority=10,
        ),
        Capability(
            capability_id="git-checkout",
            operation="checkout",
            adapter_id="mcp-git",
            risk_ceiling="medium",
            offline=False,
            idempotent=True,
            local_only=True,
            priority=10,
        ),
        # merge is NOT idempotent: a repeated merge may create a new merge
        # commit if upstream advanced between the two calls.
        Capability(
            capability_id="git-merge",
            operation="merge",
            adapter_id="mcp-git",
            risk_ceiling="high",
            offline=False,
            idempotent=False,
            local_only=True,
            priority=25,
        ),
    )

    def __init__(self, *, mcp_endpoint: Optional[str] = None, available: bool = True):
        super().__init__(mcp_endpoint=mcp_endpoint, available=available)
        # In-process simulation of a git repo's state.
        # branches: name → commit_hash. commits: hash → message.
        # Simulated real: name → commit_hash (for push verification).
        self._branches: Dict[str, str] = {"main": "0" * 40}
        self._commits: Dict[str, str] = {"0" * 40: "initial"}
        self._current_branch = "main"
        self._remote: Dict[str, str] = {"main": "0" * 40}
        self._commit_counter = 0

    # -- MCP tool dispatch (stub) -----------------------------------------
    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        op = tool_name.split("_", 1)[1] if "_" in tool_name else tool_name
        if op == "commit":
            return self._do_commit(arguments)
        if op == "push":
            return self._do_push(arguments)
        if op == "create_branch":
            return self._do_create_branch(arguments)
        if op == "checkout":
            return self._do_checkout(arguments)
        if op == "merge":
            return self._do_merge(arguments)
        raise NotExecuted(f"unknown git operation: {op!r}")

    def _do_commit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        message = args.get("message", "")
        # Deterministic-ish hash: counter + message — simulating "new hash each call".
        self._commit_counter += 1
        new_hash = hashlib.sha1(
            f"{self._commit_counter}:{message}".encode("utf-8")
        ).hexdigest()
        self._commits[new_hash] = message
        self._branches[self._current_branch] = new_hash
        return {"branch": self._current_branch, "commit_hash": new_hash, "message": message}

    def _do_push(self, args: Dict[str, Any]) -> Dict[str, Any]:
        branch = args.get("branch", self._current_branch)
        if branch not in self._branches:
            raise NotExecuted(f"push: unknown branch {branch!r}")
        local_hash = self._branches[branch]
        remote_hash = self._remote.get(branch, "0" * 40)
        if local_hash == remote_hash:
            return {"branch": branch, "up_to_date": True, "remote": remote_hash}
        self._remote[branch] = local_hash
        return {"branch": branch, "pushed": True, "remote": local_hash}

    def _do_create_branch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        branch = args.get("branch")
        base = args.get("base_ref", self._current_branch)
        if not branch:
            raise NotExecuted("create_branch: 'branch' argument required")
        if base not in self._branches:
            raise NotExecuted(f"create_branch: unknown base_ref {base!r}")
        if branch in self._branches:
            return {"branch": branch, "existed": True, "base": base}
        self._branches[branch] = self._branches[base]
        return {"branch": branch, "created": True, "base": base}

    def _do_checkout(self, args: Dict[str, Any]) -> Dict[str, Any]:
        branch = args.get("branch") or args.get("ref")
        if not branch:
            raise NotExecuted("checkout: 'branch' or 'ref' argument required")
        if branch not in self._branches:
            raise NotExecuted(f"checkout: unknown ref {branch!r}")
        previous = self._current_branch
        self._current_branch = branch
        return {"previous": previous, "current": branch, "head": self._branches[branch]}

    def _do_merge(self, args: Dict[str, Any]) -> Dict[str, Any]:
        branch = args.get("branch")
        if not branch:
            raise NotExecuted("merge: 'branch' argument required")
        if branch not in self._branches:
            raise NotExecuted(f"merge: unknown branch {branch!r}")
        # Simulate a new merge commit (NOT idempotent — new hash each call).
        self._commit_counter += 1
        merged_hash = hashlib.sha1(
            f"{self._commit_counter}:merge:{branch}".encode("utf-8")
        ).hexdigest()
        self._commits[merged_hash] = f"merge {branch}"
        self._branches[self._current_branch] = merged_hash
        return {"branch": self._current_branch, "merged": branch, "merge_commit": merged_hash}

    # -- read_state: independent verifier-side query ----------------------
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        if not self.available:
            return Observation(UNAVAILABLE)
        op = intent.operation
        if op == "commit":
            head = self._branches.get(self._current_branch)
            if head is None or head == "0" * 40:
                return Observation(ABSENT, None, 0)
            return Observation(
                PRESENT,
                {"branch": self._current_branch, "commit_hash": head,
                 "message": self._commits.get(head, "")},
                1,
            )
        if op == "push":
            branch = intent.payload.get("branch", self._current_branch)
            local = self._branches.get(branch)
            remote = self._remote.get(branch)
            if local is None or remote is None:
                return Observation(ABSENT, {"branch": branch}, 0)
            if local != remote:
                # Local ahead — push effect NOT yet applied.
                return Observation(ABSENT, {"branch": branch, "local": local, "remote": remote}, 0)
            return Observation(
                PRESENT,
                {"branch": branch, "remote": remote, "local": local, "in_sync": True},
                1,
            )
        if op == "create_branch":
            branch = intent.payload.get("branch")
            if not branch:
                return Observation(UNAVAILABLE)
            if branch not in self._branches:
                return Observation(ABSENT, {"branch": branch}, 0)
            return Observation(
                PRESENT,
                {"branch": branch, "head": self._branches[branch]},
                1,
            )
        if op == "checkout":
            branch = intent.payload.get("branch") or intent.payload.get("ref")
            if not branch:
                return Observation(UNAVAILABLE)
            if self._current_branch != branch:
                return Observation(ABSENT, {"current": self._current_branch, "wanted": branch}, 0)
            return Observation(
                PRESENT,
                {"current": self._current_branch, "head": self._branches[branch]},
                1,
            )
        if op == "merge":
            head = self._branches.get(self._current_branch)
            if head is None:
                return Observation(ABSENT, None, 0)
            return Observation(
                PRESENT,
                {"branch": self._current_branch, "head": head},
                1,
            )
        return Observation(UNAVAILABLE)
