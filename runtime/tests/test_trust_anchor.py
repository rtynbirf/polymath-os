"""runtime/tests/test_trust_anchor.py — Tests for the External Trust Anchor
(IAEA nuclear-safeguards pattern, per ADR-0029 §9).

Per IAEA safeguards: tamper-evidence needs an EXTERNAL verification point.
The DecreeLog's hash chain proves internal integrity, but to prove the
whole chain hasn't been REBUILT from scratch, the last decree's hash must
be published to an out-of-band trust anchor (file, printout, USB, lawyer,
blockchain, ...). If someone rebuilds the decree log from scratch, the
external anchor will NOT match — tamper detected.

Four tests, all using tempfile.TemporaryDirectory + DecreeLog.
"""
import json, sqlite3, sys, tempfile, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decree_log import DecreeLog
from trust_anchor import publish_trust_anchor, verify_trust_anchor


class TrustAnchorTests(unittest.TestCase):
    """Verify the IAEA-pattern external trust anchor for the decree log."""

    # ---------------------------------------------------------------- 1
    def test_publish_trust_anchor(self):
        """publish_trust_anchor writes a JSON file with the last decree's
        full hash, seq, total count, and a timestamp."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")
            dl = DecreeLog(db_path)
            dl.issue("First decree — the human is PID=1", category="directive")
            dl.issue("Second decree — never use Google", category="prohibition")

            returned = publish_trust_anchor(dl, anchor_path=anchor_path)

            self.assertEqual(returned, anchor_path)
            self.assertTrue(Path(anchor_path).exists(),
                            "publish_trust_anchor must create the anchor file")

            with open(anchor_path) as f:
                anchor = json.load(f)

            # Anchor must reference the LAST decree (seq=2).
            self.assertEqual(anchor["last_decree_seq"], 2)
            # Full 64-hex-char SHA-256 hash, not the truncated display form.
            self.assertEqual(len(anchor["last_decree_hash"]), 64)
            self.assertNotIn("...", anchor["last_decree_hash"],
                             "anchor must store the FULL hash, not a truncated display form")
            self.assertEqual(anchor["total_decrees"], 2)
            self.assertIn("timestamp", anchor)
            self.assertEqual(anchor["anchor_file"], anchor_path)
            # Anchor stores a preview of the decree text (first 80 chars).
            self.assertTrue(anchor["last_decree_text"].startswith("Second decree"))
            dl.close()

    # ---------------------------------------------------------------- 2
    def test_verify_trust_anchor_match(self):
        """Verify returns verified=True when the decree log's hash matches
        the hash stored in the external anchor."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")
            dl = DecreeLog(db_path)
            dl.issue("Decree 1", category="law")
            dl.issue("Decree 2 — never use Google", category="prohibition")
            dl.issue("Decree 3 — allow local unbound DNS", category="permission")
            publish_trust_anchor(dl, anchor_path=anchor_path)

            # Even if more decrees are issued AFTER publishing, the anchor
            # pins decree #3's hash — verify still finds it and matches.
            dl.issue("Decree 4 (post-anchor)", category="observation")

            result = verify_trust_anchor(dl, anchor_path=anchor_path)
            self.assertTrue(result["verified"],
                             "verify must return True when hash matches the anchor")
            self.assertEqual(result["anchor_seq"], 3)
            self.assertIn("anchor_hash", result)
            self.assertIn("current_hash", result)
            self.assertEqual(result["anchor_hash"], result["current_hash"],
                             "anchor and current hashes must match on verified=True")
            self.assertIn("verified", result)
            dl.close()

    # ---------------------------------------------------------------- 3
    def test_verify_trust_anchor_mismatch(self):
        """Verify returns verified=False when the decree log's hash differs
        from the anchor — i.e. someone rebuilt/tampered the log."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")
            dl = DecreeLog(db_path)
            dl.issue("Decree 1", category="law")
            dl.issue("Decree 2 — never use Google", category="prohibition")
            publish_trust_anchor(dl, anchor_path=anchor_path)

            # Simulate tampering: directly overwrite the decree_hash of the
            # anchored decree (#2) in the SQLite DB. This is what an attacker
            # rebuilding the decree log from scratch would produce — a
            # different hash for the same seq.
            db = sqlite3.connect(db_path)
            db.execute("UPDATE decrees SET decree_hash = ? WHERE seq = 2",
                       ("0" * 64,))
            db.commit()
            db.close()

            result = verify_trust_anchor(dl, anchor_path=anchor_path)
            self.assertFalse(result["verified"],
                             "verify must return False when hashes mismatch")
            self.assertEqual(result["anchor_seq"], 2)
            self.assertNotEqual(result["anchor_hash"], result["current_hash"],
                                "mismatched hashes must be reported")
            self.assertIn("TAMPER DETECTED", result["message"],
                          "mismatch message must clearly say TAMPER DETECTED")
            dl.close()

    # ---------------------------------------------------------------- 4
    def test_verify_trust_anchor_missing(self):
        """Verify returns verified=False with a clear 'file not found'
        message when no trust anchor file exists at the given path."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "does_not_exist.json")
            dl = DecreeLog(db_path)
            dl.issue("Decree 1", category="law")

            result = verify_trust_anchor(dl, anchor_path=anchor_path)

            self.assertFalse(result["verified"],
                             "missing anchor file → verified must be False")
            self.assertEqual(result["message"], "trust anchor file not found")
            dl.close()


if __name__ == "__main__":
    unittest.main()
