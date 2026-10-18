"""runtime/tests/test_incident_response.py — Tests for ADR-0035
AI-Assisted Incident Response (the `IncidentAnalyzer` class).

The analyser is a thin read-only consumer of the circuit breaker state
and the Evidence Ledger: it aggregates the last N DECREE_BLOCK events,
optionally asks an LLM for a remediation suggestion, and returns a
structured list of suggested actions for the human.

These four tests use the same `tempfile.TemporaryDirectory + DecreeLog
+ Runtime + MemoryAdapter` scaffolding as `test_circuit_breaker.py`:
  1. test_analyze_not_tripped                    — closed → {tripped: False}
  2. test_analyze_tripped_returns_analysis       — tripped → full report shape
  3. test_suggest_remediation_includes_resume    — pure function: always has "resume"
  4. test_rule_based_analysis_finds_most_common_term — no LLM; picks "google"

Per ADR-0035 Verification section: the analyser is rule-based in all 4
tests (no `llm_adapter`); the LLM path is exercised by a separate
test suite (TBD in a future task — kept out of scope here).
"""
import sys, tempfile, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from singulyar_runtime import Runtime, Policy, Capability, Intent, State, MemoryAdapter
from decree_log import DecreeLog
from incident_response import IncidentAnalyzer


def _setup(tmp: str, threshold: int = 3, window: int = 60):
    """Build a Runtime with a 'never use Google' prohibition decree
    attached, and configure the circuit breaker with the given
    threshold / window. Mirrors `test_circuit_breaker._setup` exactly
    so both test suites share the same incident scenario."""
    dl = DecreeLog(str(Path(tmp) / "decrees.db"))
    dl.issue("never use Google", category="prohibition")
    caps = [Capability("c1", "send", "memory", "low", True, True)]
    rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), redaction_key=b"k")
    rt.set_decree_log(dl)
    rt.set_circuit_breaker(threshold=threshold, window=window)
    return rt, dl


def _trip_breaker(rt, dl, *, n_violating: int = 4):
    """Helper: trip the breaker by issuing `n_violating` decree-violating
    Intents. Default 4 (one more than threshold=3) so the 4th Intent
    trips on entry to `_advance()` (the breaker sees 3 DECREE_BLOCKs
    already recorded → trips CLOSED→OPEN). After the trip, the ledger
    contains exactly 3 DECREE_BLOCK events (the tripping Intent is
    blocked by the breaker BEFORE the decree gate, so no new
    DECREE_BLOCK is recorded for it)."""
    for i in range(n_violating):
        it = Intent(f"trip{i}", f"send data to Google API #{i}", "send",
                    {"v": "x"}, {"v": "x"})
        rt.run(it)


class IncidentAnalyzerTests(unittest.TestCase):
    """Verify the ADR-0035 AI-Assisted Incident Response analyser."""

    # ---------------------------------------------------------------- 1
    def test_analyze_not_tripped(self):
        """When the breaker is CLOSED (no trip), the analyser returns
        `{tripped: False}` and does NOT read DECREE_BLOCK events from
        the ledger (no `analysis` / `suggestions` keys in the result)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Issue a couple of decree-violating Intents — 2 < threshold
            # of 3, so the breaker stays CLOSED. Each one is blocked
            # at the decree gate and records a DECREE_BLOCK event, but
            # the breaker does not trip.
            for i in range(2):
                it = Intent(f"b{i}", f"send data to Google API #{i}", "send",
                            {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertEqual(rt._cb_state, "closed",
                             "breaker must be CLOSED below threshold")
            # Sanity: the ledger has 2 DECREE_BLOCK events even though
            # the breaker hasn't tripped (they were recorded at the
            # decree gate, before any breaker check).
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "DECREE_BLOCK"]), 2)

            # The analyser must short-circuit on a non-tripped breaker.
            analyzer = IncidentAnalyzer(rt, dl)  # no LLM — rule-based
            result = analyzer.analyze_circuit_breaker_trip()
            self.assertEqual(result.get("tripped"), False,
                             "non-tripped breaker must report tripped=False")
            self.assertEqual(result.get("state"), "closed",
                             "non-tripped result must include state='closed'")
            self.assertNotIn("analysis", result,
                              "non-tripped result must NOT include analysis")
            self.assertNotIn("suggestions", result,
                              "non-tripped result must NOT include suggestions")
            dl.close()

    # ---------------------------------------------------------------- 2
    def test_analyze_tripped_returns_analysis(self):
        """When the breaker is OPEN (tripped), the analyser returns
        the full tripped report shape:
          {tripped: True, state: "open", block_count: int,
           analysis: {...}, suggestions: [...]}
        with the rule-based analysis (source="rule-based", no LLM here)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open",
                             "breaker must be OPEN after 4 violations")

            analyzer = IncidentAnalyzer(rt, dl)  # no LLM — rule-based
            result = analyzer.analyze_circuit_breaker_trip()

            # Top-level shape.
            self.assertEqual(result.get("tripped"), True)
            self.assertEqual(result.get("state"), "open")
            self.assertIsInstance(result.get("block_count"), int)
            self.assertGreater(result["block_count"], 0,
                               "block_count must be > 0 when tripped")
            # The ledger recorded 3 DECREE_BLOCK events (the tripping
            # 4th Intent was blocked by the breaker before the decree
            # gate, so it did NOT add a new DECREE_BLOCK).
            self.assertEqual(result["block_count"], 3)

            # analysis sub-dict must have all rule-based fields.
            analysis = result.get("analysis")
            self.assertIsInstance(analysis, dict)
            for key in (
                "decree_seq_counts",
                "matched_term_counts",
                "intent_ids",
                "unique_intent_count",
                "most_common_decree_seq",
                "most_common_term",
                "source",
                "llm_response",
            ):
                self.assertIn(key, analysis,
                              f"analysis must include {key!r}")
            # Rule-based path (no LLM was passed to the analyser).
            self.assertEqual(analysis["source"], "rule-based")
            self.assertIsNone(analysis["llm_response"],
                               "rule-based analysis must have llm_response=None")
            # All 3 DECREE_BLOCK events came from intents mentioning
            # "Google" → 3 unique intent_ids, 3 violations.
            self.assertEqual(analysis["unique_intent_count"], 3)
            self.assertEqual(len(analysis["intent_ids"]), 3)
            # All 3 violations reference decree_seq=1 (the only decree
            # in the log) and matched_term="google" (DecreeLog extracts
            # the lowercase head noun from "never use Google").
            self.assertEqual(analysis["decree_seq_counts"], {1: 3})
            self.assertEqual(analysis["matched_term_counts"], {"google": 3})

            # suggestions sub-list must be non-empty and contain at
            # least the always-present investigate + resume actions.
            suggestions = result.get("suggestions")
            self.assertIsInstance(suggestions, list)
            self.assertGreaterEqual(len(suggestions), 2,
                                     "must suggest at least investigate + resume")
            actions = [s.get("action") for s in suggestions]
            self.assertIn("investigate", actions)
            self.assertIn("resume", actions)
            # Ordering: investigate must come BEFORE resume (safest-first
            # per ADR-0035 `suggest_remediation` docstring).
            self.assertLess(actions.index("investigate"), actions.index("resume"),
                            "investigate must be suggested before resume")
            dl.close()

    # ---------------------------------------------------------------- 3
    def test_suggest_remediation_includes_resume(self):
        """`suggest_remediation(analysis)` is a pure function of the
        analysis dict. It ALWAYS includes a `{"action": "resume", ...}`
        entry, regardless of whether the analysis came from the
        rule-based or LLM path. It also includes "investigate" (always
        present) and "supersede" when most_common_decree_seq is set."""
        # Build a hand-crafted analysis dict that mimics the rule-based
        # output for a Google cascade (decree_seq=1 fired 3 times,
        # matched_term="google" fired 3 times).
        analysis = {
            "decree_seq_counts": {1: 3},
            "matched_term_counts": {"google": 3},
            "intent_ids": ["trip0", "trip1", "trip2"],
            "unique_intent_count": 3,
            "most_common_decree_seq": 1,
            "most_common_term": "google",
            "source": "rule-based",
            "llm_response": None,
        }
        analyzer = IncidentAnalyzer(runtime=None, decree_log=None)
        suggestions = analyzer.suggest_remediation(analysis)

        # Must be a non-empty list of action dicts.
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        for s in suggestions:
            self.assertIn("action", s, "every suggestion must have an action")

        # The "resume" action must be present.
        resume_actions = [s for s in suggestions if s.get("action") == "resume"]
        self.assertEqual(len(resume_actions), 1,
                         "exactly one resume suggestion must be present")
        self.assertIn("description", resume_actions[0],
                      "resume suggestion must have a description")

        # The "investigate" action must also be present (always-present).
        invest_actions = [s for s in suggestions if s.get("action") == "investigate"]
        self.assertEqual(len(invest_actions), 1,
                         "exactly one investigate suggestion must be present")

        # The "supersede" action must be present because
        # most_common_decree_seq is set (1). The decree_seq field must
        # match the analysis.
        supersede_actions = [s for s in suggestions if s.get("action") == "supersede"]
        self.assertEqual(len(supersede_actions), 1,
                         "exactly one supersede suggestion when most_common_decree_seq is set")
        self.assertEqual(supersede_actions[0].get("decree_seq"), 1,
                         "supersede suggestion must carry the most-common decree_seq")
        self.assertIn("reason", supersede_actions[0],
                      "supersede suggestion must have a reason")

        # When llm_response is None, there must NOT be an
        # "llm_recommendation" action.
        llm_actions = [s for s in suggestions if s.get("action") == "llm_recommendation"]
        self.assertEqual(len(llm_actions), 0,
                         "no llm_recommendation when llm_response is None")

    # ---------------------------------------------------------------- 4
    def test_rule_based_analysis_finds_most_common_term(self):
        """Without an LLM, the analyser's rule-based aggregation
        correctly identifies the most-common matched_term and
        most_common_decree_seq from a cascade of DECREE_BLOCK events.

        Scenario: trip the breaker with 4 Intents that all mention
        "Google". The decree "never use Google" extracts the lowercase
        head noun "google" as the prohibited term. So all 3 DECREE_BLOCK
        events have matched_term="google" and decree_seq=1 → the
        rule-based analysis must report most_common_term="google" and
        most_common_decree_seq=1."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open")

            # No llm_adapter → pure rule-based analysis.
            analyzer = IncidentAnalyzer(rt, dl, llm_adapter=None)
            result = analyzer.analyze_circuit_breaker_trip()

            self.assertTrue(result["tripped"])
            analysis = result["analysis"]
            # The most-common matched_term must be "google" — the
            # DecreeLog._extract_prohibited_terms() lowercases the
            # head noun "Google" → "google". All 3 DECREE_BLOCKs hit
            # the same term, so it wins by majority (unanimous).
            self.assertEqual(analysis["most_common_term"], "google",
                             "rule-based analysis must pick 'google' as "
                             "the most-common matched_term from a cascade "
                             "of Google-prohibition DECREE_BLOCKs")
            # And the most-common decree_seq must be 1 — the only
            # decree in the log (the "never use Google" prohibition).
            self.assertEqual(analysis["most_common_decree_seq"], 1,
                             "most_common_decree_seq must be 1 — the only "
                             "prohibition decree in the log")
            # Source must be explicitly marked rule-based (so audit
            # trails can distinguish LLM-assisted from rule-based runs
            # per ADR-0019 — observability first).
            self.assertEqual(analysis["source"], "rule-based")
            self.assertIsNone(analysis["llm_response"])
            dl.close()


if __name__ == "__main__":
    unittest.main()
