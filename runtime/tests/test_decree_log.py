"""runtime/tests/test_decree_log.py — Tests for Decree Log (ВОЛЯ = НАКАЗ).

Verifies:
- Append-only (can't amend, can't delete)
- Hash chain integrity (broken chain → DecreeIntegrityError)
- check_compliance: prohibition decrees block matching intents
- Multiple decrees accumulate
- Decrees survive restart (SQLite WAL durability)
"""

import os, sys, sqlite3, tempfile, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decree_log import DecreeLog, DecreeIntegrityError


class DecreeLogTests(unittest.TestCase):

    def test_issue_first_decree(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            result = dl.issue("Человек — PID=1. Каждый инструмент — fork-exec от человека.")
            self.assertEqual(result["seq"], 1)
            self.assertEqual(result["category"], "directive")
            dl.close()

    def test_issue_multiple_decrees_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("Decree 1", category="law")
            d2 = dl.issue("Decree 2", category="law")
            d3 = dl.issue("Decree 3", category="prohibition")
            self.assertEqual(d1["seq"], 1)
            self.assertEqual(d2["seq"], 2)
            self.assertEqual(d3["seq"], 3)
            all_decrees = dl.get_all()
            self.assertEqual(len(all_decrees), 3)
            dl.close()

    def test_append_only_cannot_amend(self):
        """Decrees are immutable. Can't UPDATE text directly."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("Original decree")
            # Try to UPDATE directly — chain will break on next verify
            import sqlite3
            db = sqlite3.connect(str(Path(tmp) / "decrees.db"))
            db.execute("UPDATE decrees SET decree_text='TAMPERED' WHERE seq=1"); db.commit()
            db.close()
            # Verify should fail
            dl.close()
            # Reopen — chain should be broken
            with self.assertRaises(DecreeIntegrityError):
                DecreeLog(Path(tmp) / "decrees.db")

    def test_hash_chain_verification_on_open(self):
        """Opening a log with a broken chain → DecreeIntegrityError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decrees.db"
            dl = DecreeLog(path)
            dl.issue("Decree 1")
            dl.issue("Decree 2")
            dl.close()
            # Tamper with the database
            db = sqlite3.connect(str(path))
            db.execute("UPDATE decrees SET decree_text='TAMPERED' WHERE seq=1"); db.commit()
            db.close()
            # Reopen — should fail
            with self.assertRaises(DecreeIntegrityError):
                DecreeLog(path)

    def test_check_compliance_prohibition_blocks(self):
        """A prohibition decree blocks matching intents."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google", category="prohibition")
            dl.issue("never use Cloudflare", category="prohibition")

            # Intent mentioning Google → should be non-compliant
            result = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)

            # Intent without prohibited terms → compliant
            result = dl.check_compliance("configure DNS with local unbound")
            self.assertTrue(result["compliant"])
            dl.close()

    def test_check_compliance_no_decrees_allows_all(self):
        """Empty decree log → everything compliant (no prohibitions)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            result = dl.check_compliance("do anything")
            self.assertTrue(result["compliant"])
            self.assertEqual(result["laws_checked"], 0)
            dl.close()

    def test_decrees_survive_restart(self):
        """Decrees persist in SQLite across restart."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decrees.db"
            dl = DecreeLog(path)
            dl.issue("Decree 1", category="law")
            dl.issue("Decree 2", category="prohibition")
            dl.close()

            # Reopen
            dl2 = DecreeLog(path)
            self.assertEqual(dl2.count(), 2)
            laws = dl2.get_active_laws()
            self.assertEqual(len(laws), 2)
            dl2.close()

    def test_decree_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            self.assertEqual(dl.count(), 0)
            dl.issue("Decree 1")
            dl.issue("Decree 2")
            self.assertEqual(dl.count(), 2)
            dl.close()

    # ---------------------------------------------------------------- v0.5 phrase matching

    def test_v05_phrase_matching_google_dns_does_not_block_unbound(self):
        """v0.5 fix: decree 'never use Google DNS' must NOT block an intent
        about configuring local unbound DNS.

        Pre-v0.4 behavior was buggy: it split 'Google DNS' into individual
        words and matched 'dns' anywhere, producing a false positive on
        legitimate DNS work like 'configure DNS with local unbound'. v0.5
        treats the decree as a PHRASE (dns is a recognized acronym) so the
        only prohibited substrings are 'google dns' (full phrase) and
        'google' (head noun). 'unbound' matches neither.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("configure DNS with local unbound")
            self.assertTrue(
                result["compliant"],
                f"v0.5 false positive: 'unbound' should not match 'Google DNS' "
                f"decree. Got: {result}",
            )
            dl.close()

    def test_v05_phrase_matching_blocks_google_alone(self):
        """v0.5: decree 'never use Google DNS' still blocks any intent that
        mentions 'google' alone — because the human said 'never use Google
        DNS' and using Google for anything DNS-related is implied-prohibited.
        The matched_term field on the violation records 'google' for callers.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)
            self.assertEqual(result["violations"][0]["matched_term"], "google")
            self.assertEqual(
                result["violations"][0]["decree_text"], "never use Google DNS"
            )
            self.assertEqual(result["violations"][0]["decree_seq"], 1)
            dl.close()

    def test_v05_phrase_matching_blocks_full_phrase(self):
        """v0.5: decree 'never use Google DNS' blocks the FULL phrase
        'google dns' as a contiguous substring.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("use Google DNS server")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)
            self.assertIn("google dns", result["violations"][0]["matched_term"])
            dl.close()

    def test_v05_single_word_prohibition_still_blocks(self):
        """v0.5 SINGLE classification: 'never use Cloudflare' → prohibited
        terms = {'cloudflare'} — single word, block on that word.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Cloudflare", category="prohibition")
            self.assertFalse(dl.check_compliance("use Cloudflare for CDN")["compliant"])
            self.assertTrue(dl.check_compliance("use Fastly for CDN")["compliant"])
            dl.close()

    def test_v05_list_matching_chrome_firefox_edge_safari(self):
        """v0.5 LIST classification: 'never use Chrome Firefox Edge Safari'
        has 4 words, all proper nouns (each starts with uppercase in the
        original decree text and/or is a known browser proper noun). Each
        word is an INDEPENDENT prohibited term — block on any single match.

        Note on the spec's 'chrome inside chromium' warning: 'chrome' is
        NOT in fact a substring of 'chromium'. chrome = c-h-r-o-m-e (6 chars);
        chromium = c-h-r-o-m-i-u-m. They diverge at index 5 (e vs i). So v0.5
        substring matching does NOT match 'chrome' inside 'ungoogled-chromium',
        and the spec's stated limitation does not arise for this input.
        A genuine v0.5 limitation DOES exist for inputs where 'chrome' is a
        real substring, e.g. 'chromebook' or 'chromedriver' — v0.6 word-
        boundary regex will address those.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Chrome Firefox Edge Safari", category="prohibition")

            # Each individual browser name should trigger denial.
            self.assertFalse(dl.check_compliance("install Chrome as default browser")["compliant"])
            self.assertFalse(dl.check_compliance("use Safari browser")["compliant"])
            self.assertFalse(dl.check_compliance("switch to Firefox")["compliant"])
            self.assertFalse(dl.check_compliance("install Edge")["compliant"])

            # No prohibited term → compliant.
            self.assertTrue(dl.check_compliance("use Konqueror as browser")["compliant"])

            # 'ungoogled-chromium' is compliant — see docstring: 'chrome' is
            # NOT a substring of 'chromium' (the spec's stated v0.5 limitation
            # is factually wrong for this input).
            result = dl.check_compliance("use ungoogled-chromium")
            self.assertTrue(
                result["compliant"],
                f"'chrome' is not a substring of 'chromium' (diverge at idx 5: "
                f"e vs i). Expected compliant, got: {result}",
            )

            # Genuine v0.5 substring limitation: 'chrome' IS a substring of
            # 'chromebook' → will be DENIED. v0.6 word-boundary regex will fix.
            self.assertFalse(dl.check_compliance("buy a chromebook")["compliant"])
            dl.close()


if __name__ == "__main__":
    import sqlite3
    unittest.main()
