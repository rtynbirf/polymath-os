"""Tests for MCPCapabilityRegistry (unittest, stdlib only — no pytest dep).

Run from the repo root:

    python -m unittest discover -s tooling/agents/mcp/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUNTIME_SRC = _REPO_ROOT / "runtime" / "src"
for _p in (str(_REPO_ROOT), str(_RUNTIME_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runtime.src.singulyar_runtime import Capability  # noqa: E402

from tooling.agents.mcp.registry import MCPCapabilityRegistry, default_registry  # noqa: E402
from tooling.agents.mcp.filesystem_adapter import FilesystemAdapter  # noqa: E402
from tooling.agents.mcp.git_adapter import GitAdapter  # noqa: E402
from tooling.agents.mcp.postgres_adapter import PostgresAdapter  # noqa: E402
from tooling.agents.mcp.web_search_adapter import WebSearchAdapter  # noqa: E402


def _cap(cid, op, adapter_id="x", risk="low", offline=False, idempotent=True,
         local_only=False, priority=100):
    return Capability(cid, op, adapter_id, risk, offline, idempotent,
                     local_only, priority)


class TestRegisterAndLookup(unittest.TestCase):
    def test_register_single_capability(self):
        r = MCPCapabilityRegistry()
        c = _cap("c1", "op1")
        r.register(c)
        self.assertEqual(len(r), 1)
        self.assertIn("c1", r)
        self.assertIs(r.by_id("c1"), c)

    def test_register_many(self):
        r = MCPCapabilityRegistry()
        caps = [_cap("c1", "op1", priority=10), _cap("c2", "op2", priority=20)]
        r.register_many(caps)
        self.assertEqual(len(r), 2)

    def test_duplicate_capability_id_raises(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("c1", "op1"))
        with self.assertRaises(ValueError):
            r.register(_cap("c1", "op_other"))

    def test_by_id_returns_none_for_unknown(self):
        r = MCPCapabilityRegistry()
        self.assertIsNone(r.by_id("nope"))

    def test_all_returns_sorted_by_operation_then_priority(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("b", "op2", priority=20))
        r.register(_cap("a", "op1", priority=10))
        r.register(_cap("c", "op1", priority=5))
        all_caps = r.all()
        self.assertEqual([c.capability_id for c in all_caps], ["c", "a", "b"])


class TestFindCompatible(unittest.TestCase):
    def test_returns_only_matching_operation(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("c1", "op1"))
        r.register(_cap("c2", "op2"))
        matched = r.find_compatible("op1")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "c1")

    def test_returns_empty_list_when_no_match(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("c1", "op1"))
        self.assertEqual(r.find_compatible("unknown_op"), [])

    def test_sorted_by_priority_ascending(self):
        """Lower priority = preferred first (per SINGULYAR kernel sort order)."""
        r = MCPCapabilityRegistry()
        r.register(_cap("high-prio", "op1", priority=100))
        r.register(_cap("low-prio", "op1", priority=5))
        r.register(_cap("mid-prio", "op1", priority=50))
        matched = r.find_compatible("op1")
        self.assertEqual(
            [c.capability_id for c in matched],
            ["low-prio", "mid-prio", "high-prio"],
        )

    def test_local_only_constraint_filters_non_local(self):
        """If intent requires local_only, only local_only capabilities qualify."""
        r = MCPCapabilityRegistry()
        r.register(_cap("local", "op1", local_only=True))
        r.register(_cap("remote", "op1", local_only=False))
        matched = r.find_compatible("op1", {"local_only": True})
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "local")

    def test_offline_constraint_filters_non_offline(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("offline", "op1", offline=True))
        r.register(_cap("online", "op1", offline=False))
        matched = r.find_compatible("op1", {"offline": True})
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "offline")

    def test_risk_floor_filters_lower_ceilings(self):
        """risk_floor=high → only high-ceiling capabilities qualify."""
        r = MCPCapabilityRegistry()
        r.register(_cap("low", "op1", risk="low"))
        r.register(_cap("med", "op1", risk="medium"))
        r.register(_cap("high", "op1", risk="high"))
        matched = r.find_compatible("op1", {"risk_floor": "high"})
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "high")

    def test_risk_floor_medium_keeps_medium_and_high(self):
        r = MCPCapabilityRegistry()
        r.register(_cap("low", "op1", risk="low"))
        r.register(_cap("med", "op1", risk="medium"))
        r.register(_cap("high", "op1", risk="high"))
        matched = r.find_compatible("op1", {"risk_floor": "medium"})
        self.assertEqual({c.capability_id for c in matched}, {"med", "high"})

    def test_idempotent_only_filter(self):
        """recover() uses idempotent_only=True to skip non-idempotent caps."""
        r = MCPCapabilityRegistry()
        r.register(_cap("idem", "op1", idempotent=True))
        r.register(_cap("non-idem", "op1", idempotent=False))
        matched = r.find_compatible("op1", {"idempotent_only": True})
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "idem")

    def test_combined_constraints(self):
        """local_only AND offline AND risk_floor all applied together."""
        r = MCPCapabilityRegistry()
        r.register(_cap("good", "op1", risk="high", offline=True, local_only=True))
        r.register(_cap("bad-local", "op1", risk="high", offline=True, local_only=False))
        r.register(_cap("bad-offline", "op1", risk="high", offline=False, local_only=True))
        r.register(_cap("bad-risk", "op1", risk="low", offline=True, local_only=True))
        matched = r.find_compatible("op1", {
            "local_only": True, "offline": True, "risk_floor": "high"
        })
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].capability_id, "good")

    def test_no_silent_downgrade_when_no_match(self):
        """Hard constraints are NEVER relaxed: empty result, not best-effort."""
        r = MCPCapabilityRegistry()
        r.register(_cap("only-online", "op1", offline=False))
        # Asking for offline when none qualify → empty list (not downgrade).
        matched = r.find_compatible("op1", {"offline": True})
        self.assertEqual(matched, [])


class TestDefaultRegistry(unittest.TestCase):
    def test_default_registry_has_all_builtin_caps(self):
        r = default_registry()
        total = (
            len(FilesystemAdapter.CAPABILITIES)
            + len(GitAdapter.CAPABILITIES)
            + len(PostgresAdapter.CAPABILITIES)
            + len(WebSearchAdapter.CAPABILITIES)
        )
        self.assertEqual(len(r), total)

    def test_default_registry_lookup_write_file(self):
        r = default_registry()
        matched = r.find_compatible("write_file")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].adapter_id, "mcp-filesystem")
        self.assertTrue(matched[0].idempotent)

    def test_default_registry_lookup_commit_returns_non_idempotent(self):
        r = default_registry()
        matched = r.find_compatible("commit")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].adapter_id, "mcp-git")
        self.assertFalse(matched[0].idempotent)

    def test_default_registry_filter_local_only_excludes_remote(self):
        """local_only=True filter must exclude git-push and postgres (which
        touch remote state)."""
        r = default_registry()
        matched = r.find_compatible("push", {"local_only": True})
        self.assertEqual(matched, [], "push touches remote — local_only filter excludes it")
        matched = r.find_compatible("upsert_row", {"local_only": True})
        self.assertEqual(matched, [], "postgres upsert touches remote DB")

    def test_default_registry_filter_offline_excludes_everything(self):
        """No built-in MCP adapter is offline (all require a server).
        Asking for offline must yield empty (no silent downgrade)."""
        r = default_registry()
        for op in ("write_file", "commit", "execute_query", "search"):
            with self.subTest(op=op):
                self.assertEqual(r.find_compatible(op, {"offline": True}), [])


class TestCapabilityValidation(unittest.TestCase):
    def test_register_rejects_empty_capability_id(self):
        r = MCPCapabilityRegistry()
        with self.assertRaises(ValueError):
            r.register(Capability("", "op", "x", "low", False, True, False, 10))

    def test_register_rejects_empty_operation(self):
        r = MCPCapabilityRegistry()
        with self.assertRaises(ValueError):
            r.register(Capability("c", "", "x", "low", False, True, False, 10))

    def test_register_rejects_invalid_risk_ceiling(self):
        r = MCPCapabilityRegistry()
        with self.assertRaises(ValueError):
            r.register(Capability("c", "op", "x", "extreme", False, True, False, 10))

    def test_register_rejects_negative_priority(self):
        r = MCPCapabilityRegistry()
        with self.assertRaises(ValueError):
            r.register(Capability("c", "op", "x", "low", False, True, False, -1))


if __name__ == "__main__":
    unittest.main()
