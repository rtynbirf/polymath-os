"""runtime/tests/test_trust_anchor.py — Tests for the External Trust Anchor
(IAEA nuclear-safeguards pattern, per ADR-0029 §9).

Per IAEA safeguards: tamper-evidence needs an EXTERNAL verification point.
The DecreeLog's hash chain proves internal integrity, but to prove the
whole chain hasn't been REBUILT from scratch, the last decree's hash must
be published to an out-of-band trust anchor (file, printout, USB, lawyer,
blockchain, ...). If someone rebuilds the decree log from scratch, the
external anchor will NOT match — tamper detected.

Six tests, all using tempfile.TemporaryDirectory + DecreeLog.

Test 5 (test_auto_publish_after_issue) and Test 6 (test_make_verify_claim_25)
are the Task 13-B integration tests: they verify that (a) the auto-publish
hook in DecreeLog.issue() refreshes the anchor after every commit, and
(b) `make verify` claim #25 (check_trust_anchor) returns True.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Path to the top-level scripts/check.py — used by test_make_verify_claim_25
# to load the check_trust_anchor function in-process via importlib. The
# file is wrapped in `if __name__ == "__main__":` so importing it does
# NOT trigger the full make-verify run (only the function definitions +
# the extra_checks / checks lists execute).
_TOP_CHECK_PATH = _HERE.parent.parent.parent / "scripts" / "check.py"


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

    # ---------------------------------------------------------------- 5
    def test_auto_publish_after_issue(self):
        """Task 13-B integration test: DecreeLog.issue() auto-publishes the
        external trust anchor after every successful commit (per ADR-0029 §9).

        The auto-publish hook in issue() calls publish_trust_anchor(self),
        which writes the last decree's full SHA-256 hash to a JSON anchor
        file. This test verifies:
          (a) before any issue() → no anchor exists
          (b) after the 1st issue() → anchor exists, references seq=1
          (c) after the 2nd issue() → anchor refreshed, references seq=2
          (d) each refresh produces a different hash (the anchor is not
              a stale snapshot — it tracks the latest decree)

        The auto-publish hook is gated on db_path being the production
        database (~/.polymath-os/decrees.db) OR the env var
        POLYMATH_OS_TRUST_ANCHOR_PATH being set. We set the env var to
        redirect the anchor to a temp path so the test doesn't pollute
        the user's real ~/.polymath-os/trust_anchor.json.
        """
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "auto_trust_anchor.json")

            # Redirect auto-publish to a temp path.
            # (Without this env var, the auto-publish hook is a no-op for
            # temp-dir dbs — it only fires for the production db.)
            old_env = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = anchor_path
            try:
                dl = DecreeLog(db_path)

                # (a) No anchor yet — auto-publish hasn't fired.
                self.assertFalse(
                    Path(anchor_path).exists(),
                    "auto-publish should not fire before the first issue()"
                )

                # (b) Issue 1st decree → auto-publish writes the anchor.
                dl.issue("First decree — auto-publish test", category="law")
                self.assertTrue(
                    Path(anchor_path).exists(),
                    "auto-publish must create the anchor file after the "
                    "first issue()"
                )
                with open(anchor_path) as f:
                    anchor1 = json.load(f)
                self.assertEqual(anchor1["last_decree_seq"], 1,
                                "anchor must reference the just-issued decree (seq=1)")
                self.assertEqual(anchor1["total_decrees"], 1)
                self.assertEqual(len(anchor1["last_decree_hash"]), 64,
                                 "anchor must store the FULL 64-hex SHA-256 hash")
                self.assertNotIn("...", anchor1["last_decree_hash"],
                                 "anchor must NOT store the truncated display form")

                # (c) Issue 2nd decree → anchor refreshed.
                dl.issue("Second decree — anchor refresh test", category="law")
                with open(anchor_path) as f:
                    anchor2 = json.load(f)
                self.assertEqual(anchor2["last_decree_seq"], 2,
                                "anchor must be refreshed to reference seq=2")
                self.assertEqual(anchor2["total_decrees"], 2)

                # (d) Anchor hashes differ across decrees — the anchor
                # tracks the latest decree, not a frozen snapshot.
                self.assertNotEqual(
                    anchor1["last_decree_hash"], anchor2["last_decree_hash"],
                    "anchor must be refreshed with each issue() — hashes "
                    "should differ across decrees"
                )

                # The auto-published anchor must VERIFY correctly against
                # the live decree log (no tampering — we just issued it).
                result = verify_trust_anchor(dl, anchor_path=anchor_path)
                self.assertTrue(
                    result["verified"],
                    "auto-published anchor must verify True against the "
                    f"live log. Got: {result}"
                )

                dl.close()
            finally:
                # Restore env var so other tests see the original state.
                if old_env is None:
                    os.environ.pop("POLYMATH_OS_TRUST_ANCHOR_PATH", None)
                else:
                    os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = old_env

    # ---------------------------------------------------------------- 6
    def test_make_verify_claim_25(self):
        """Task 13-B integration test: scripts/check.py::check_trust_anchor
        (claim #25 of `make verify`) returns True.

        This exercises the top-level make-verify claim that verifies the
        external trust anchor. The claim is dormant (returns True with
        "trust anchor not yet published") when no anchor exists, and
        returns True with "trust anchor verified" when an anchor exists
        and matches the live decree log. Both paths must return True so
        `make verify` passes regardless of whether the human has cut a
        seal yet.

        We test both paths:
          (a) dormant: no anchor file → True
          (b) verified: anchor exists and matches → True
        """
        # Load scripts/check.py as a module via importlib — the file is
        # wrapped in `if __name__ == "__main__":` so this import does NOT
        # trigger the full make-verify run on the user's repo.
        spec = importlib.util.spec_from_file_location(
            "polymath_os_top_check", str(_TOP_CHECK_PATH)
        )
        top_check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(top_check)
        self.assertTrue(
            hasattr(top_check, "check_trust_anchor"),
            "scripts/check.py must expose check_trust_anchor for claim #25"
        )

        # ---- (a) dormant path: no anchor exists → True
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "no_anchor_yet.json")
            dl = DecreeLog(db_path)
            dl.issue("Decree for the dormant-path subtest", category="law")
            dl.close()

            # Override env vars to point check_trust_anchor at the temp
            # paths (so it does NOT touch the user's real ~/.polymath-os/).
            old_a = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            old_d = os.environ.get("POLYMATH_OS_DECREE_DB")
            os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = anchor_path
            os.environ["POLYMATH_OS_DECREE_DB"] = db_path
            try:
                # No anchor file at this path yet → dormant path → True.
                self.assertFalse(
                    Path(anchor_path).exists(),
                    "precondition: anchor file must not exist for dormant subtest"
                )
                ok, detail = top_check.check_trust_anchor()
                self.assertTrue(
                    ok,
                    f"dormant path: check_trust_anchor() must return True when "
                    f"no anchor exists yet. Got: ok={ok}, detail={detail}"
                )
                self.assertIn(
                    "not yet published", detail,
                    f"dormant path: detail must mention 'not yet published'. "
                    f"Got: {detail}"
                )

                # ---- (b) verified path: anchor exists and matches → True
                # Publish a fresh anchor (auto-publish would also fire if
                # we issue another decree, but explicit publish is clearer).
                dl = DecreeLog(db_path)
                publish_trust_anchor(dl, anchor_path=anchor_path)
                dl.close()

                self.assertTrue(
                    Path(anchor_path).exists(),
                    "precondition: anchor file must exist for verified subtest"
                )
                ok, detail = top_check.check_trust_anchor()
                self.assertTrue(
                    ok,
                    f"verified path: check_trust_anchor() must return True when "
                    f"anchor exists and matches the live log. Got: ok={ok}, "
                    f"detail={detail}"
                )
                self.assertIn(
                    "verified", detail.lower(),
                    f"verified path: detail must mention 'verified'. Got: {detail}"
                )
            finally:
                # Restore env vars.
                for key, old in (("POLYMATH_OS_TRUST_ANCHOR_PATH", old_a),
                                 ("POLYMATH_OS_DECREE_DB", old_d)):
                    if old is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old


if __name__ == "__main__":
    unittest.main()
