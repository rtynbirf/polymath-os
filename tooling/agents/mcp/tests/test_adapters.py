"""Tests for MCP adapter scaffolds (unittest, stdlib only — no pytest dep).

Run from the repo root:

    python -m unittest discover -s tooling/agents/mcp/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Make the repo root importable so `tooling.agents.mcp.*` resolves
# (namespace packages — see PEP 420). And add runtime/src to sys.path
# so the inner `from schema_validate import ...` in singulyar_runtime works.
_REPO_ROOT = Path(__file__).resolve().parents[4]  # tooling/agents/mcp/tests → repo root
_RUNTIME_SRC = _REPO_ROOT / "runtime" / "src"
for _p in (str(_REPO_ROOT), str(_RUNTIME_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runtime.src.singulyar_runtime import (  # noqa: E402
    Adapter,
    Capability,
    Intent,
    Observation,
    PRESENT,
    ABSENT,
    UNAVAILABLE,
)

from tooling.agents.mcp.base_adapter import MCPAdapter, MCP_VERSION  # noqa: E402
from tooling.agents.mcp.filesystem_adapter import FilesystemAdapter  # noqa: E402
from tooling.agents.mcp.git_adapter import GitAdapter  # noqa: E402
from tooling.agents.mcp.postgres_adapter import PostgresAdapter  # noqa: E402
from tooling.agents.mcp.web_search_adapter import WebSearchAdapter  # noqa: E402


# ---------------------------------------------------------------------------
# MCP version pin (ADR-0008)
# ---------------------------------------------------------------------------
class TestMCPVersionPin(unittest.TestCase):
    def test_mcp_version_matches_adr_0008(self):
        """ADR-0008 §2 pins MCP spec to 2026-07-28 (stateless core)."""
        self.assertEqual(MCP_VERSION, "2026-07-28")

    def test_mcp_version_is_string(self):
        self.assertIsInstance(MCP_VERSION, str)
        self.assertTrue(MCP_VERSION, "MCP_VERSION must be non-empty")


# ---------------------------------------------------------------------------
# Adapter interface contract
# ---------------------------------------------------------------------------
class TestAdapterInterface(unittest.TestCase):
    ADAPTER_CLASSES = (
        MCPAdapter,
        FilesystemAdapter,
        GitAdapter,
        PostgresAdapter,
        WebSearchAdapter,
    )

    def test_all_adapters_subclass_singulyar_adapter(self):
        """Every MCP adapter MUST subclass singulyar_runtime.Adapter."""
        for cls in self.ADAPTER_CLASSES:
            with self.subTest(adapter=cls.__name__):
                self.assertTrue(
                    issubclass(cls, Adapter),
                    f"{cls.__name__} must subclass singulyar_runtime.Adapter",
                )

    def test_concrete_adapters_have_adapter_id(self):
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            with self.subTest(adapter=cls.__name__):
                self.assertTrue(getattr(cls, "adapter_id", None))
                self.assertNotEqual(cls.adapter_id, "mcp-abstract")

    def test_concrete_adapters_have_mcp_server(self):
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            with self.subTest(adapter=cls.__name__):
                self.assertTrue(getattr(cls, "mcp_server", None))
                self.assertNotEqual(cls.mcp_server, "abstract")

    def test_each_adapter_has_capabilities_tuple(self):
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            with self.subTest(adapter=cls.__name__):
                caps = getattr(cls, "CAPABILITIES", None)
                self.assertIsNotNone(caps, f"{cls.__name__} must declare CAPABILITIES")
                self.assertIsInstance(caps, tuple)
                self.assertGreater(len(caps), 0, f"{cls.__name__}.CAPABILITIES empty")

    def test_adapter_instantiation(self):
        """Each adapter can be instantiated and exposes execute/read_state."""
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            with self.subTest(adapter=cls.__name__):
                inst = cls()
                self.assertTrue(hasattr(inst, "execute"))
                self.assertTrue(hasattr(inst, "read_state"))
                self.assertTrue(callable(inst.execute))
                self.assertTrue(callable(inst.read_state))


# ---------------------------------------------------------------------------
# Capability field validation (mirrors capability.schema.json)
# ---------------------------------------------------------------------------
class TestCapabilityFields(unittest.TestCase):
    def _all_caps(self):
        out = []
        out.extend(FilesystemAdapter.CAPABILITIES)
        out.extend(GitAdapter.CAPABILITIES)
        out.extend(PostgresAdapter.CAPABILITIES)
        out.extend(WebSearchAdapter.CAPABILITIES)
        return out

    def test_all_caps_are_capability_dataclass(self):
        for c in self._all_caps():
            self.assertIsInstance(c, Capability)

    def test_all_caps_have_required_fields(self):
        """Each Capability must have (operation, adapter_id, risk_ceiling,
        offline, idempotent, local_only, priority) fields per the schema."""
        required = {
            "capability_id", "operation", "adapter_id", "risk_ceiling",
            "offline", "idempotent", "local_only", "priority",
        }
        for c in self._all_caps():
            fields = set(c.__dataclass_fields__.keys())
            self.assertEqual(
                required, fields,
                f"Capability {c.capability_id} fields mismatch: {fields}",
            )

    def test_capability_ids_are_unique(self):
        ids = [c.capability_id for c in self._all_caps()]
        duplicates = {i for i in ids if ids.count(i) > 1}
        self.assertFalse(duplicates, f"duplicate capability_ids: {duplicates}")

    def test_risk_ceiling_is_valid_enum(self):
        for c in self._all_caps():
            self.assertIn(c.risk_ceiling, {"low", "medium", "high"})

    def test_offline_idempotent_local_only_are_bool(self):
        for c in self._all_caps():
            self.assertIsInstance(c.offline, bool)
            self.assertIsInstance(c.idempotent, bool)
            self.assertIsInstance(c.local_only, bool)

    def test_priority_is_non_negative_int(self):
        for c in self._all_caps():
            self.assertIsInstance(c.priority, int)
            self.assertGreaterEqual(c.priority, 0)

    def test_adapter_id_matches_class(self):
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            for cap in cls.CAPABILITIES:
                self.assertEqual(
                    cap.adapter_id, cls.adapter_id,
                    f"{cls.__name__}: capability {cap.capability_id} adapter_id "
                    f"{cap.adapter_id!r} != class {cls.adapter_id!r}",
                )

    def test_capability_id_strings_non_empty(self):
        for c in self._all_caps():
            self.assertTrue(c.capability_id, "capability_id must be non-empty")
            self.assertTrue(c.operation, "operation must be non-empty")
            self.assertTrue(c.adapter_id, "adapter_id must be non-empty")


# ---------------------------------------------------------------------------
# Idempotency semantics (per ADR-0012 + task 5-E spec)
# ---------------------------------------------------------------------------
class TestIdempotencySemantics(unittest.TestCase):
    """Idempotency must match operation semantics exactly.

    SINGULYAR EIR uses `cap.idempotent` to decide whether `recover()` may
    auto-retry on ABSENT — declaring the wrong flag risks double effects
    (False positive) or stuck intents (False negative).
    """

    def _find(self, cls, operation):
        for c in cls.CAPABILITIES:
            if c.operation == operation:
                return c
        self.fail(f"{cls.__name__} missing operation {operation!r}")

    # filesystem
    def test_write_file_is_idempotent(self):
        self.assertTrue(self._find(FilesystemAdapter, "write_file").idempotent)

    def test_create_file_is_idempotent(self):
        self.assertTrue(self._find(FilesystemAdapter, "create_file").idempotent)

    def test_delete_file_is_idempotent(self):
        self.assertTrue(self._find(FilesystemAdapter, "delete_file").idempotent)

    def test_read_file_is_idempotent(self):
        self.assertTrue(self._find(FilesystemAdapter, "read_file").idempotent)

    def test_list_dir_is_idempotent(self):
        self.assertTrue(self._find(FilesystemAdapter, "list_dir").idempotent)

    def test_append_file_is_NOT_idempotent(self):
        """Repeated appends accumulate — must NOT be retried by the kernel."""
        self.assertFalse(self._find(FilesystemAdapter, "append_file").idempotent)

    # git
    def test_git_commit_is_NOT_idempotent(self):
        """Each commit mints a new hash — must NOT be auto-retried."""
        self.assertFalse(self._find(GitAdapter, "commit").idempotent)

    def test_git_push_is_idempotent(self):
        self.assertTrue(self._find(GitAdapter, "push").idempotent)

    def test_git_create_branch_is_idempotent(self):
        self.assertTrue(self._find(GitAdapter, "create_branch").idempotent)

    def test_git_checkout_is_idempotent(self):
        self.assertTrue(self._find(GitAdapter, "checkout").idempotent)

    def test_git_merge_is_NOT_idempotent(self):
        self.assertFalse(self._find(GitAdapter, "merge").idempotent)

    # postgres
    def test_execute_query_is_idempotent(self):
        self.assertTrue(self._find(PostgresAdapter, "execute_query").idempotent)

    def test_execute_migration_is_idempotent(self):
        self.assertTrue(self._find(PostgresAdapter, "execute_migration").idempotent)

    def test_upsert_row_is_idempotent(self):
        self.assertTrue(self._find(PostgresAdapter, "upsert_row").idempotent)

    # websearch
    def test_search_is_idempotent(self):
        self.assertTrue(self._find(WebSearchAdapter, "search").idempotent)

    def test_fetch_url_is_idempotent(self):
        self.assertTrue(self._find(WebSearchAdapter, "fetch_url").idempotent)


# ---------------------------------------------------------------------------
# read_state contract — MUST return Observation, never None
# ---------------------------------------------------------------------------
class TestReadStateContract(unittest.TestCase):
    def _intent(self, op, payload, expected=None, iid="t"):
        return Intent(iid, f"test {op}", op, dict(payload), dict(expected or {}))

    def test_read_state_unavailable_returns_observation_unavailable(self):
        """When the MCP server is unavailable, read_state MUST return
        Observation(UNAVAILABLE) — never None."""
        for cls in (FilesystemAdapter, GitAdapter, PostgresAdapter, WebSearchAdapter):
            with self.subTest(adapter=cls.__name__):
                inst = cls(available=False)
                # Use any payload — adapter should not even look at it.
                obs = inst.read_state(self._intent("write_file", {"path": "/x"}, {"content": "y"}), "k")
                self.assertIsInstance(obs, Observation)
                self.assertEqual(obs.status, UNAVAILABLE)

    def test_read_state_returns_observation_never_none(self):
        """For every (adapter, operation) pair, read_state on an empty store
        returns an Observation — ABSENT or UNAVAILABLE, never None."""
        for cls, ops in [
            (FilesystemAdapter, ["create_file", "write_file", "read_file",
                                 "delete_file", "list_dir", "append_file"]),
            (GitAdapter, ["commit", "push", "create_branch", "checkout", "merge"]),
            (PostgresAdapter, ["execute_query", "execute_migration", "upsert_row"]),
            (WebSearchAdapter, ["search", "fetch_url"]),
        ]:
            for op in ops:
                with self.subTest(adapter=cls.__name__, op=op):
                    inst = cls()
                    payload = {"path": "/x", "content": "y", "branch": "b",
                               "version": "v1", "table": "t", "row": {"id": 1},
                               "pk_column": "id", "query": "q", "url": "https://x"}
                    # Only keep keys relevant for the op (we don't know which).
                    obs = inst.read_state(self._intent(op, payload), "k1")
                    self.assertIsNotNone(obs, "read_state must never return None")
                    self.assertIsInstance(obs, Observation)
                    self.assertIn(obs.status, {PRESENT, ABSENT, UNAVAILABLE})

    def test_read_state_after_execute_returns_present(self):
        """Sanity: execute + read_state roundtrip returns PRESENT for the
        idempotent filesystem write_file operation."""
        fs = FilesystemAdapter()
        i = self._intent("write_file", {"path": "/tmp/a", "content": "hi"},
                         expected={"path": "/tmp/a", "content": "hi"})
        result = fs.execute(i, "k1")
        self.assertTrue(result.get("accepted"))
        obs = fs.read_state(i, "k1")
        self.assertEqual(obs.status, PRESENT)
        self.assertEqual(obs.value, {"path": "/tmp/a", "content": "hi"})
        self.assertEqual(obs.count, 1)


# ---------------------------------------------------------------------------
# Smoke: execute + read_state for each adapter on a representative op
# ---------------------------------------------------------------------------
class TestExecuteReadStateRoundtrip(unittest.TestCase):
    def _intent(self, op, payload, expected=None, iid="t"):
        return Intent(iid, f"test {op}", op, dict(payload), dict(expected or {}))

    def test_filesystem_write_then_read(self):
        fs = FilesystemAdapter()
        i = self._intent("write_file", {"path": "/p", "content": "hello"},
                         {"path": "/p", "content": "hello"})
        fs.execute(i, "k")
        obs = fs.read_state(i, "k")
        self.assertEqual(obs.status, PRESENT)
        self.assertEqual(obs.value["content"], "hello")

    def test_git_create_branch_then_read(self):
        g = GitAdapter()
        i = self._intent("create_branch", {"branch": "feat/x", "base_ref": "main"})
        g.execute(i, "k")
        obs = g.read_state(i, "k")
        self.assertEqual(obs.status, PRESENT)

    def test_postgres_migration_then_read(self):
        p = PostgresAdapter()
        i = self._intent("execute_migration",
                         {"version": "0001", "table": "users",
                          "columns": ["id", "email"]})
        p.execute(i, "k")
        obs = p.read_state(i, "k")
        self.assertEqual(obs.status, PRESENT)

    def test_websearch_search_then_read(self):
        w = WebSearchAdapter()
        i = self._intent("search", {"query": "polymath os"})
        w.execute(i, "k")
        obs = w.read_state(i, "k")
        self.assertEqual(obs.status, PRESENT)


if __name__ == "__main__":
    unittest.main()
