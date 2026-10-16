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


if __name__ == "__main__":
    import sqlite3
    unittest.main()
