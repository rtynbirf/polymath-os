"""runtime/tests/test_decree_aware_agent.py — Tests for Decree-Aware Agent Behavior (ADR-0033).

Verifies that when an AI agent's Intent gets DECREE_BLOCKed by the
AgentMesh decree gate (ADR-0024), the DecreeAwareAgent:

1. Passes compliant intents through unchanged (no adaptation, no
   violation recorded).
2. Records the violation when a decree blocks the intent, and produces
   an adaptation (simple-replacement fallback when no LLM is attached).
3. Produces an adapted description that does NOT contain the matched
   term (the core correctness invariant).
4. Retries the adapted description through the decree gate, eventually
   passing on the second attempt and producing a full adaptation_history.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_card import SINGULYAR_EIR_CARD
from agent_mesh import AgentMesh
from decree_log import DecreeLog
from decree_aware_agent import DecreeAwareAgent


class _FakeExecute:
    """Test helper — captures intents and returns a canned response.

    Mirrors the same helper in test_agent_mesh.py so the test fixtures
    look familiar.
    """
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {"state": "CONFIRMED"}

    def __call__(self, request):
        self.calls.append(request)
        return self.response


class DecreeAwareAgentTests(unittest.TestCase):
    """ADR-0033 tests — DecreeAwareAgent wraps AgentMesh with adaptation.

    Setup matches test_agent_mesh.py's AgentMeshDecreeEnforcementTests
    fixtures: three prohibition decrees (Google DNS, Cloudflare, browser
    list), one registered SINGULYAR_EIR_CARD agent with a _FakeExecute.
    The DecreeAwareAgent under test has NO llm_adapter — it uses the
    no-LLM simple-replacement path. This keeps the tests deterministic
    and free of external dependencies (per ADR-0002 Tier 1).
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dl = DecreeLog(str(Path(self.tmpdir.name) / "decrees.db"))
        # Issue a few prohibition decrees — same shape as test_agent_mesh.py.
        self.dl.issue("never use Google DNS", category="prohibition", scope="all")
        self.dl.issue("never use Cloudflare", category="prohibition", scope="all")
        self.dl.issue("never use Chrome Firefox Edge Safari",
                      category="prohibition", scope="polymath-os")

        self.mesh = AgentMesh(decree_log=self.dl)
        self.exec_fn = _FakeExecute({"state": "CONFIRMED"})
        self.mesh.register(SINGULYAR_EIR_CARD, self.exec_fn)

        # No llm_adapter — exercises the no-LLM simple-replacement path.
        # This is the path that's deterministic and free of external deps.
        self.agent = DecreeAwareAgent(
            self.mesh, "singulyar-eir.local", llm_adapter=None
        )

    def tearDown(self):
        self.dl.close()
        self.tmpdir.cleanup()

    # ─── Test 1: compliant intent passes through ──────────────────────

    def test_propose_passes_when_compliant(self):
        """A clean intent that doesn't violate any decree must pass through
        the decree gate unchanged. No violation recorded, no adaptation
        produced, execute_fn called exactly once, and the result state
        matches what execute_fn returned (CONFIRMED)."""
        result = self.agent.propose(
            description="publish a note about default-deny",
            operation="send",
            payload={"topic": "default-deny"},
        )

        # Decree gate passed — not blocked.
        self.assertFalse(
            result["blocked"],
            f"compliant intent must not be blocked. Got: {result}",
        )
        # State reflects execute_fn's response.
        self.assertEqual(result["state"], "CONFIRMED")
        # No violations, no adaptations produced.
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["adaptations"], [])
        # execute_fn was called exactly once (decree gate passed → forwarded).
        self.assertEqual(len(self.exec_fn.calls), 1)
        # No violation recorded in the persistent history.
        self.assertEqual(len(self.agent.violation_history), 0)
        self.assertEqual(len(self.agent.adaptation_history), 0)

    # ─── Test 2: prohibited intent records violation + suggests adaptation ─

    def test_propose_blocked_records_violation(self):
        """When the decree gate blocks the intent, the agent must:
        - return {blocked: True, state: "DECREE_BLOCKED"}
        - record the violation with correct matched_term and decree_seq
        - produce an adaptation (simple-replacement when no LLM)
        - NOT call execute_fn (the decree gate blocked before execution)
        - persist the violation in agent.violation_history
        """
        result = self.agent.propose(
            description="send data to Google Cloud Storage",
            operation="storage.write",
            payload={"data": "sensitive"},
        )

        # Blocked.
        self.assertTrue(result["blocked"])
        self.assertEqual(result["state"], "DECREE_BLOCKED")

        # Exactly one violation recorded.
        self.assertEqual(len(result["violations"]), 1)
        v = result["violations"][0]
        # The first prohibition decree blocks on the term 'google'.
        # Decree #1 was 'never use Google DNS' — matched_term='google'.
        self.assertEqual(v["matched_term"], "google")
        self.assertEqual(v["decree_seq"], 1)
        # block_message is the full DECREE_BLOCK:... string from AgentMesh.
        self.assertIn("DECREE_BLOCK", v["block_message"])
        self.assertIn("google", v["block_message"])

        # An adaptation was produced (simple-replacement, no LLM).
        self.assertEqual(len(result["adaptations"]), 1)
        adapted = result["adaptations"][0]
        # The adaptation must NOT contain the prohibited term.
        self.assertNotIn("google", adapted.lower())

        # execute_fn must NOT have been called — decree gate blocked
        # BEFORE execution (this is the ADR-0024 invariant; ADR-0033
        # preserves it — adaptation is a separate retry, not a bypass).
        self.assertEqual(
            len(self.exec_fn.calls), 0,
            "execute_fn must not be called when decree blocks the intent",
        )

        # Persistent history also recorded the violation.
        self.assertEqual(len(self.agent.violation_history), 1)
        self.assertEqual(self.agent.violation_history[0]["matched_term"], "google")
        self.assertEqual(len(self.agent.adaptation_history), 1)
        self.assertEqual(
            self.agent.adaptation_history[0]["original"],
            "send data to Google Cloud Storage",
        )

    # ─── Test 3: adapt() removes the prohibited term ─────────────────

    def test_adapt_removes_prohibited_term(self):
        """Direct unit test of the adapt() method. Given a description
        that contains the matched_term, the adapted description must NOT
        contain the matched_term (case-insensitive). This is the core
        correctness invariant of the no-LLM path — every adaptation
        removes at least the prohibited slot.

        We pass a synthetic violation (not produced by a real propose()
        call) to isolate adapt()'s logic from mesh.send()'s behavior.
        """
        violation = {
            "decree_seq": 1,
            "decree_text": "never use Google DNS",
            "matched_term": "google",
            "violation": "intent contains prohibited term: google",
            "block_message": "DECREE_BLOCK: intent violates decree #1",
            "all_violations": [],
        }

        adapted = self.agent.adapt(
            original_description="send data to Google Cloud Storage",
            violations=[violation],
        )

        # Must be a non-empty string.
        self.assertIsInstance(adapted, str)
        self.assertTrue(adapted.strip(), "adapted description must be non-empty")

        # Must NOT contain the matched_term 'google' (case-insensitive).
        # This is the core invariant — adaptation must produce a
        # description that re-passes the decree gate.
        self.assertNotIn(
            "google", adapted.lower(),
            f"adapted description must not contain the matched_term 'google'. "
            f"Got: {adapted!r}",
        )

        # Sanity: the adapted description should differ from the original
        # (something was changed — at minimum, 'google' was replaced).
        self.assertNotEqual(
            adapted.lower(), "send data to google cloud storage",
            "adapted description must differ from the original (at minimum, "
            "the matched_term must be replaced)",
        )

    # ─── Test 4: propose_with_adaptation retries until passing ───────

    def test_propose_with_adaptation_retries(self):
        """Full adaptation loop. Original description is blocked on
        'google'; the agent adapts (removes 'google' → '[redacted]');
        the adapted description passes the decree gate on the second
        attempt.

        Verifies:
        - Final result is NOT blocked (adaptation succeeded).
        - attempts == 2 (original blocked, adapted passed).
        - adaptation_history has 2 entries, in order:
            [0]: attempt=1, original description, blocked=True
            [1]: attempt=2, adapted description,  blocked=False
        - final_description is the adapted description that passed.
        - execute_fn was called exactly once (only on the successful
          attempt — the blocked attempt was caught at the decree gate).
        """
        result = self.agent.propose_with_adaptation(
            description="send data to Google",
            operation="storage.write",
            payload={"data": "x"},
            max_retries=3,
        )

        # The adaptation succeeded — not blocked.
        self.assertFalse(
            result["blocked"],
            f"propose_with_adaptation should succeed after one adaptation. "
            f"Got: {result}",
        )
        self.assertNotEqual(result["state"], "DECREE_BLOCKED")

        # attempts == 2 (original blocked + adapted passed).
        self.assertEqual(result["attempts"], 2)

        # adaptation_history has 2 entries.
        self.assertEqual(len(result["adaptation_history"]), 2)

        # First attempt: original description, blocked.
        first = result["adaptation_history"][0]
        self.assertEqual(first["attempt"], 1)
        self.assertEqual(first["description"], "send data to Google")
        self.assertTrue(first["blocked"])
        self.assertEqual(first["state"], "DECREE_BLOCKED")
        self.assertEqual(len(first["violations"]), 1)
        self.assertEqual(first["violations"][0]["matched_term"], "google")

        # Second attempt: adapted description, NOT blocked.
        second = result["adaptation_history"][1]
        self.assertEqual(second["attempt"], 2)
        self.assertTrue(
            second["description"] != "send data to Google",
            "second attempt must use the ADAPTED description, not the original",
        )
        self.assertNotIn(
            "google", second["description"].lower(),
            "adapted description must not contain the matched_term 'google'",
        )
        self.assertFalse(second["blocked"])
        self.assertEqual(second["state"], "CONFIRMED")
        self.assertEqual(len(second["violations"]), 0)

        # final_description is the adapted description that passed.
        self.assertEqual(result["final_description"], second["description"])

        # execute_fn called exactly once — only on the successful attempt.
        # The blocked attempt was caught at the decree gate BEFORE execution
        # (ADR-0024 invariant; ADR-0033 preserves it — adaptation is a
        # separate retry, not a bypass).
        self.assertEqual(
            len(self.exec_fn.calls), 1,
            "execute_fn must be called exactly once (only on the successful "
            "adapted attempt). The blocked attempt must not reach execute_fn.",
        )


if __name__ == "__main__":
    unittest.main()
