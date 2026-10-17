"""runtime/tests/test_agent_mesh.py — Tests for Decree-Enforced Multi-Agent Communication (ADR-0024)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_card import SINGULYAR_EIR_CARD, POLYMATH_OS_BROWSER_CARD, CELL65_LLM_CARD, AgentCard
from agent_mesh import (
    AgentMesh, IntentRequest, IntentResponse, DecreeBlockResponse,
    DECREE_BLOCK_ERROR_CODE,
)
from decree_log import DecreeLog


class _FakeExecute:
    """Test helper — captures intents and returns a canned response."""
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {"state": "CONFIRMED"}

    def __call__(self, request):
        self.calls.append(request)
        return self.response


class AgentMeshRegistrationTests(unittest.TestCase):
    def test_register_and_list(self):
        mesh = AgentMesh()
        mesh.register(SINGULYAR_EIR_CARD, _FakeExecute())
        agents = mesh.list_agents()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].id, "singulyar-eir.local")

    def test_duplicate_register_rejected(self):
        mesh = AgentMesh()
        mesh.register(SINGULYAR_EIR_CARD, _FakeExecute())
        with self.assertRaises(ValueError):
            mesh.register(SINGULYAR_EIR_CARD, _FakeExecute())

    def test_unregister(self):
        mesh = AgentMesh()
        mesh.register(SINGULYAR_EIR_CARD, _FakeExecute())
        self.assertTrue(mesh.unregister("singulyar-eir.local"))
        self.assertEqual(len(mesh.list_agents()), 0)
        self.assertFalse(mesh.unregister("singulyar-eir.local"))  # already gone

    def test_discover_by_capability(self):
        mesh = AgentMesh()
        mesh.register(SINGULYAR_EIR_CARD, _FakeExecute())
        mesh.register(CELL65_LLM_CARD, _FakeExecute())
        # Singulyar has "intent.execute", cell65-llm doesn't
        exec_agents = mesh.discover("intent.execute")
        self.assertEqual(len(exec_agents), 1)
        self.assertEqual(exec_agents[0].id, "singulyar-eir.local")
        # cell65 has "llm.generate"
        llm_agents = mesh.discover("llm.generate")
        self.assertEqual(len(llm_agents), 1)
        self.assertEqual(llm_agents[0].id, "cell65-host.llm")


class AgentMeshRoutingNoDecreeLogTests(unittest.TestCase):
    """When no decree_log is attached, mesh just forwards (no enforcement)."""

    def test_send_no_decree_log_no_decree_check(self):
        mesh = AgentMesh(decree_log=None)
        exec_fn = _FakeExecute({"state": "CONFIRMED"})
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)

        req = IntentRequest(
            id="r-1",
            params={"intent_id": "i-1", "description": "anything goes here", "operation": "send"},
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertFalse(resp.is_blocked())
        self.assertEqual(resp.result.get("state"), "CONFIRMED")
        self.assertEqual(len(exec_fn.calls), 1)

    def test_send_unknown_agent_returns_error(self):
        mesh = AgentMesh()
        req = IntentRequest(id="r-1", params={"description": "x"})
        resp = mesh.send("nonexistent.local", req)
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.code, -32602)


class AgentMeshDecreeEnforcementTests(unittest.TestCase):
    """Core tests — decree gate fires BEFORE execution."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        # Issue a few prohibition decrees
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")
        self.dl.issue("never use Chrome Firefox Edge Safari", category="prohibition", scope="polymath-os")

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    def test_compliant_intent_passes_through(self):
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute({"state": "CONFIRMED"})
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)

        req = IntentRequest(
            id="r-1",
            params={
                "intent_id": "i-1",
                "description": "publish note about default-deny",  # no decree violation
                "operation": "send",
            },
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertFalse(resp.is_blocked(), f"Should pass: {resp.to_dict()}")
        self.assertEqual(resp.result.get("state"), "CONFIRMED")
        self.assertEqual(len(exec_fn.calls), 1)

    def test_decree_blocks_intent_before_execution(self):
        """Core test — DECREE_BLOCK fires BEFORE execute_fn is called."""
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute({"state": "CONFIRMED"})
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)

        req = IntentRequest(
            id="r-2",
            params={
                "intent_id": "i-2",
                "description": "send data to Google API",  # decree #1 blocks 'google'
                "operation": "send",
            },
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.code, DECREE_BLOCK_ERROR_CODE)
        self.assertIn("DECREE_BLOCK", resp.error.message)
        self.assertIn("google", resp.error.message)
        self.assertEqual(resp.error.data["decree_seq"], 1)
        self.assertEqual(resp.error.data["matched_term"], "google")
        # CRITICAL — execute_fn must NOT have been called
        self.assertEqual(len(exec_fn.calls), 0, "execute_fn must not be called when decree blocks")

    def test_cloudflare_blocked(self):
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute()
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)
        req = IntentRequest(
            id="r-3",
            params={"description": "use Cloudflare for CDN"},
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.data["matched_term"], "cloudflare")
        self.assertEqual(len(exec_fn.calls), 0)

    def test_scope_filter_only_matching_decrees(self):
        """decree_scope filters which decrees apply.

        Chrome decree has scope='polymath-os'. Singulyar agent has scope='all'.
        When sending to polymath-os agent, Chrome decree applies.
        When sending to singulyar agent, Chrome decree applies (scope=all).
        Wait — the singulyar agent is scope=all, so ALL decrees apply,
        including the Chrome decree (scope=polymath-os, but mesh logic is
        'apply if decree_scope == "all" OR decree_scope == scope').
        """
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute()
        mesh.register(POLYMATH_OS_BROWSER_CARD, exec_fn)
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)

        # Send "install Chrome" to polymath-os browser agent.
        # Browser agent has decree_scope=polymath-os, so Chrome decree applies.
        req = IntentRequest(
            id="r-4",
            params={"description": "install Chrome as default browser"},
        )
        resp = mesh.send("polymath-os.browser", req)
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.data["matched_term"], "chrome")
        self.assertEqual(len(exec_fn.calls), 0)

    def test_caller_can_override_decree_scope(self):
        """Caller can pass decree_scope in params to override agent's default."""
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute({"state": "CONFIRMED"})
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)  # scope=all by default

        # Override scope to 'polymath-os' — should still apply Chrome decree
        req = IntentRequest(
            id="r-5",
            params={
                "description": "install Chrome",
                "decree_scope": "polymath-os",
            },
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.data["matched_term"], "chrome")

    def test_decree_block_events_recorded(self):
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute()
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)
        req = IntentRequest(
            id="r-6",
            params={"description": "send data to Google"},
        )
        mesh.send("singulyar-eir.local", req)
        events = mesh.events()
        # Should have: AGENT_REGISTERED, DECREE_BLOCK
        event_types = [e["event"] for e in events]
        self.assertIn("AGENT_REGISTERED", event_types)
        self.assertIn("DECREE_BLOCK", event_types)
        # Check DECREE_BLOCK event content
        block_events = [e for e in events if e["event"] == "DECREE_BLOCK"]
        self.assertEqual(len(block_events), 1)
        self.assertEqual(block_events[0]["agent_id"], "singulyar-eir.local")
        self.assertEqual(block_events[0]["decree_scope"], "all")

    def test_intent_executed_event_recorded_on_success(self):
        mesh = AgentMesh(decree_log=self.dl)
        exec_fn = _FakeExecute({"state": "CONFIRMED"})
        mesh.register(SINGULYAR_EIR_CARD, exec_fn)
        req = IntentRequest(
            id="r-7",
            params={"description": "publish note about default-deny"},
        )
        mesh.send("singulyar-eir.local", req)
        events = mesh.events()
        event_types = [e["event"] for e in events]
        self.assertIn("INTENT_EXECUTED", event_types)

    def test_agent_exception_returns_error_response(self):
        mesh = AgentMesh(decree_log=self.dl)

        def boom(req):
            raise RuntimeError("agent exploded")
        mesh.register(SINGULYAR_EIR_CARD, boom)
        req = IntentRequest(
            id="r-8",
            params={"description": "publish note about default-deny"},
        )
        resp = mesh.send("singulyar-eir.local", req)
        self.assertTrue(resp.is_blocked())
        self.assertIn("AGENT_ERROR", resp.error.message)
        self.assertEqual(resp.error.data["exception_type"], "RuntimeError")


class AgentMeshMultiAgentTests(unittest.TestCase):
    """Multi-agent scenarios — two agents collaborating."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    def test_agent_a_calls_agent_b_via_mesh(self):
        """Agent A composes an Intent that targets Agent B.

        The mesh checks the Intent against Agent B's decree_scope before
        forwarding to Agent B's execute_fn. This is the unique СИНГУЛЯР
        property — agents cannot bypass the decree gate.
        """
        mesh = AgentMesh(decree_log=self.dl)

        # Agent B (cell65 LLM) — has scope=singulyar
        llm_calls = []
        def llm_execute(req):
            llm_calls.append(req)
            return {"state": "CONFIRMED", "answer": "42"}
        mesh.register(CELL65_LLM_CARD, llm_execute)

        # Agent A composes a clean Intent — passes decree gate
        req = IntentRequest(
            id="r-multi-1",
            params={
                "intent_id": "i-multi-1",
                "description": "ask the LLM about default-deny patterns",
                "operation": "llm.answer",
                "payload": {"prompt": "explain default-deny"},
            },
        )
        resp = mesh.send("cell65-host.llm", req)
        self.assertFalse(resp.is_blocked())
        self.assertEqual(resp.result.get("answer"), "42")
        self.assertEqual(len(llm_calls), 1)

    def test_agent_a_blocked_when_calling_agent_b_with_prohibited_intent(self):
        """Agent A tries to use Agent B to send data to Google — blocked by decree."""
        mesh = AgentMesh(decree_log=self.dl)

        # Agent B (storage adapter) — would happily store data
        storage_calls = []
        def storage_execute(req):
            storage_calls.append(req)
            return {"state": "CONFIRMED"}
        storage_card = AgentCard(
            id="storage.adapter.local",
            name="Storage Adapter",
            description="Stores data to disk/S3",
            version="v0.1",
            capabilities=["storage.write", "storage.read"],
            decree_scope="all",
        )
        mesh.register(storage_card, storage_execute)

        # Agent A issues Intent that mentions Google (decree #1 prohibits)
        req = IntentRequest(
            id="r-multi-2",
            params={
                "intent_id": "i-multi-2",
                "description": "store user data to Google Cloud Storage bucket",
                "operation": "storage.write",
                "payload": {"data": "sensitive"},
            },
        )
        resp = mesh.send("storage.adapter.local", req)

        # CRITICAL — decree gate fires BEFORE storage_execute
        self.assertTrue(resp.is_blocked())
        self.assertEqual(resp.error.code, DECREE_BLOCK_ERROR_CODE)
        self.assertIn("google", resp.error.message)
        # storage_execute must NOT have been called
        self.assertEqual(len(storage_calls), 0,
                         "storage_execute must not be called — decree gate blocks BEFORE execution")


if __name__ == "__main__":
    unittest.main()
