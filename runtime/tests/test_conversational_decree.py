"""runtime/tests/test_conversational_decree.py — Tests for ADR-0032.

Verifies the ConversationalDecreeInterface:
- Rule-based prohibition detection (canonical "I don't want to use Google
  anymore" → category="prohibition", decree_text="never use Google")
- Rule-based law detection ("always ..." → category="law")
- Full pipeline: issue_from_nl() → DecreeLog.issue() → decree record
  with seq, decree_hash, durable storage
- Default directive path (no recognized trigger → category="directive",
  original text echoed unchanged)

Per ADR-0032 §Verification: exactly 5 tests. All tests use the
rule-based path (no LLM adapter supplied) — the LLM path is covered by
the spec but untested here because it requires a live LLM (per ADR-0006
— falsifiable properties; only deterministic paths are unit-tested).
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

from conversational_decree import ConversationalDecreeInterface
from decree_log import DecreeLog


class ConversationalDecreeTests(unittest.TestCase):
    """ADR-0032 acceptance tests — exactly 5, all rule-based path."""

    # ─── test_rule_based_prohibition_detection ───────────────────

    def test_rule_based_prohibition_detection(self):
        """NL with a prohibition trigger → category == 'prohibition'.

        Covers the canonical ADR-0032 example and a couple of trigger
        variants ('stop using', 'never'). The formalized decree_text
        must start with 'never use' for the verb-first cases.
        """
        cdi = ConversationalDecreeInterface(decree_log=None, llm_adapter=None)

        # Canonical example.
        d = cdi.translate("I don't want to use Google anymore")
        self.assertEqual(d["category"], "prohibition")
        self.assertEqual(d["scope"], "all")
        self.assertTrue(d["text"].lower().startswith("never use "))
        self.assertIn("google", d["text"].lower())

        # 'stop using' trigger.
        d = cdi.translate("stop using Cloudflare")
        self.assertEqual(d["category"], "prohibition")
        self.assertIn("cloudflare", d["text"].lower())

        # 'never' trigger (already-formal input passes through unchanged).
        d = cdi.translate("never use AWS")
        self.assertEqual(d["category"], "prohibition")
        self.assertEqual(d["text"], "never use AWS")

    # ─── test_rule_based_law_detection ────────────────────────────

    def test_rule_based_law_detection(self):
        """NL with a law trigger → category == 'law'.

        The original text is echoed unchanged (law/permission/directive
        categories do not get the `never <verb> <entity>` re-cast).
        """
        cdi = ConversationalDecreeInterface(decree_log=None, llm_adapter=None)

        d = cdi.translate("always use local unbound for DNS")
        self.assertEqual(d["category"], "law")
        self.assertEqual(d["scope"], "all")
        # Law path echoes the input verbatim (no formalization).
        self.assertEqual(d["text"], "always use local unbound for DNS")

        # Russian 'всегда' trigger.
        d = cdi.translate("всегда использовать локальный DNS")
        self.assertEqual(d["category"], "law")
        self.assertEqual(d["text"], "всегда использовать локальный DNS")

    # ─── test_issue_from_nl_creates_decree ────────────────────────

    def test_issue_from_nl_creates_decree(self):
        """Full pipeline: issue_from_nl() returns a real decree record.

        The record must be durable — recoverable via dl.get_all() — and
        must carry the formalized decree_text and the prohibition
        category. The decree_hash must be a non-empty string (the
        append-only hash chain was extended).
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            cdi = ConversationalDecreeInterface(decree_log=dl, llm_adapter=None)

            record = cdi.issue_from_nl("stop using Chrome")

            # Returned record shape (mirrors DecreeLog.issue()'s return).
            self.assertEqual(record["seq"], 1)
            self.assertEqual(record["category"], "prohibition")
            self.assertEqual(record["scope"], "all")
            self.assertEqual(record["decree_text"], "never use Chrome")
            self.assertIn("decree_hash", record)
            self.assertTrue(record["decree_hash"])

            # Durable — the decree is in the SQLite log.
            all_decrees = dl.get_all()
            self.assertEqual(len(all_decrees), 1)
            self.assertEqual(all_decrees[0]["decree_text"], "never use Chrome")
            self.assertEqual(all_decrees[0]["category"], "prohibition")
            dl.close()

    # ─── test_nl_with_google_becomes_prohibition ──────────────────

    def test_nl_with_google_becomes_prohibition(self):
        """The ADR-0032 canonical example, end-to-end through DecreeLog.

        "I don't want to use Google anymore"
          → translate → {text: "never use Google", category: "prohibition", scope: "all"}
          → issue → decree #N recorded
          → check_compliance("configure DNS with Google 8.8.8.8") → DENIED

        This is the ADR-0032 acceptance criterion: the conversational
        decree is byte-for-byte identical to a hand-typed prohibition
        decree, and the kernel's existing check_compliance matcher
        blocks matching intents without any new code in DecreeLog.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            cdi = ConversationalDecreeInterface(decree_log=dl, llm_adapter=None)

            # Translate (no issue).
            d = cdi.translate("I don't want to use Google anymore")
            self.assertEqual(d["category"], "prohibition")
            # Case preserved from the original (human typed capital G).
            self.assertEqual(d["text"], "never use Google")
            self.assertEqual(d["scope"], "all")

            # Issue → decree recorded in the hash-chained log.
            record = cdi.issue_from_nl("I don't want to use Google anymore")
            self.assertEqual(record["category"], "prohibition")
            self.assertEqual(record["decree_text"], "never use Google")

            # Kernel enforcement: existing check_compliance now blocks
            # any intent mentioning Google. No new DecreeLog code needed.
            compliance = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(compliance["compliant"])
            self.assertGreater(len(compliance["violations"]), 0)
            dl.close()

    # ─── test_nl_default_directive ─────────────────────────────────

    def test_nl_default_directive(self):
        """NL with no recognized trigger → category == 'directive'.

        The original text is echoed unchanged (the kernel's
        check_compliance matcher treats directives as informational —
        no enforcement). This is the safe catch-all per ADR-0009:
        when in doubt, record the human's speech as-is rather than
        inventing an interpretation.
        """
        cdi = ConversationalDecreeInterface(decree_log=None, llm_adapter=None)

        d = cdi.translate("the sky is blue today")
        self.assertEqual(d["category"], "directive")
        self.assertEqual(d["scope"], "all")
        # Echoed verbatim (modulo surrounding whitespace).
        self.assertEqual(d["text"], "the sky is blue today")

        # A directive does NOT accidentally become a prohibition —
        # even if it happens to contain the substring 'use' (the verb
        # extraction only fires when category == 'prohibition').
        d = cdi.translate("please use your best judgment")
        self.assertEqual(d["category"], "directive")
        self.assertEqual(d["text"], "please use your best judgment")


if __name__ == "__main__":
    unittest.main()
