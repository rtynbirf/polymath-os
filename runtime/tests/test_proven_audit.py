"""runtime/tests/test_proven_audit.py — Tests for the Proven-Based Audit
Framework (ADR-0036).

Four tests, all using tempfile.TemporaryDirectory + DecreeLog. The tests
verify the four-proof structure end-to-end:

  1. test_verify_hash_chain      — Proof 1 runs + returns verified=True
                                   on a freshly-issued valid log.
  2. test_verify_trust_anchor    — Proof 2 runs + returns verified=True
                                   when the IAEA-pattern anchor matches.
  3. test_all_proofs_returned    — verify_4_proofs() returns the full
                                   schema with all four proof keys.
  4. test_audit_report_readable  — audit_report() returns a non-empty
                                   string with all four PROOF headers
                                   + the SUMMARY line.

Per ADR-0036, Proof 3 (Ed25519) is `skipped` when the
`decree_signatures` module isn't installed — this is expected in
environments where ADR-0034 is not yet implemented. The tests
explicitly assert this skip status (not a hard failure).
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

from decree_log import DecreeLog  # noqa: E402
from proven_audit import ProvenAudit  # noqa: E402
from trust_anchor import publish_trust_anchor  # noqa: E402


class ProvenAuditTests(unittest.TestCase):
    """Verify the Proven-Based Audit Framework (ADR-0036)."""

    # ---------------------------------------------------------------- 1
    def test_verify_hash_chain(self):
        """Proof 1 (hash-chain integrity) returns verified=True on a
        freshly-issued valid log.

        Per ADR-0021: the decree log is hash-chained (SHA-256 over
        prev_hash + timestamp + text). `_verify_chain()` is called on
        open + `verify()` exposes the result. On a freshly-issued log
        with no tampering, the chain MUST verify.
        """
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            dl = DecreeLog(db_path)
            dl.issue("Decree 1 — the human is PID=1", category="law")
            dl.issue("Decree 2 — never use Google DNS", category="prohibition")
            dl.issue("Decree 3 — allow local unbound DNS", category="permission")

            audit = ProvenAudit(dl)
            result = audit.verify_4_proofs()

            # Proof 1 must be present in the proofs dict.
            self.assertIn("hash_chain", result["proofs"],
                          "Proof 1 key must be present in proofs dict")
            proof1 = result["proofs"]["hash_chain"]

            # Proof 1 must verify True on a freshly-issued valid log.
            self.assertTrue(proof1["verified"],
                            f"Proof 1 (hash_chain) must be verified=True "
                            f"on a valid log. Got: {proof1}")
            self.assertEqual(proof1["status"], "verified",
                             f"Proof 1 status must be 'verified'. "
                             f"Got: {proof1['status']}")
            # Detail must mention the hash chain + decree count.
            self.assertIn("hash chain", proof1["detail"].lower(),
                          f"Proof 1 detail must mention 'hash chain'. "
                          f"Got: {proof1['detail']}")
            self.assertIn("3", proof1["detail"],
                          f"Proof 1 detail must mention the decree count "
                          f"(3). Got: {proof1['detail']}")
            dl.close()

    # ---------------------------------------------------------------- 2
    def test_verify_trust_anchor(self):
        """Proof 2 (trust anchor match, IAEA pattern) returns
        verified=True when the external anchor matches the live log.

        Per ADR-0029 §9: the external trust anchor is a JSON file
        containing the SHA-256 hash of the last decree. When the
        live decree log's hash matches the anchor's hash → no
        tampering detected.

        This test sets POLYMATH_OS_TRUST_ANCHOR_PATH to redirect the
        anchor to a temp file (same pattern as test_trust_anchor.py),
        publishes an anchor explicitly, then runs ProvenAudit —
        Proof 2 must verify True.
        """
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")

            # Redirect the trust anchor to a temp path so the test
            # doesn't pollute the user's real ~/.polymath-os/trust_anchor.json
            old_env = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = anchor_path
            try:
                dl = DecreeLog(db_path)
                dl.issue("Decree 1 — the human is PID=1", category="law")
                dl.issue("Decree 2 — never use Google DNS", category="prohibition")
                dl.issue("Decree 3 — allow local unbound DNS", category="permission")

                # Publish the external trust anchor (IAEA pattern).
                publish_trust_anchor(dl, anchor_path=anchor_path)
                self.assertTrue(Path(anchor_path).exists(),
                                "precondition: publish_trust_anchor must "
                                "have created the anchor file")

                audit = ProvenAudit(dl)
                result = audit.verify_4_proofs()

                # Proof 2 must be present in the proofs dict.
                self.assertIn("trust_anchor", result["proofs"],
                              "Proof 2 key must be present in proofs dict")
                proof2 = result["proofs"]["trust_anchor"]

                # Proof 2 must verify True when the anchor matches.
                self.assertTrue(proof2["verified"],
                                f"Proof 2 (trust_anchor) must be "
                                f"verified=True when the anchor matches. "
                                f"Got: {proof2}")
                self.assertEqual(proof2["status"], "verified",
                                 f"Proof 2 status must be 'verified'. "
                                 f"Got: {proof2['status']}")
                # Detail must mention verification (the message from
                # verify_trust_anchor includes 'trust anchor verified').
                self.assertIn("verif", proof2["detail"].lower(),
                              f"Proof 2 detail must mention verification. "
                              f"Got: {proof2['detail']}")
                dl.close()
            finally:
                # Restore env var so other tests see the original state.
                if old_env is None:
                    os.environ.pop("POLYMATH_OS_TRUST_ANCHOR_PATH", None)
                else:
                    os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = old_env

    # ---------------------------------------------------------------- 3
    def test_all_proofs_returned(self):
        """verify_4_proofs() returns a dict with all four proof keys
        (hash_chain, trust_anchor, signatures, ledger) plus
        all_verified + summary.

        Per ADR-0036 §Decision: the result schema is:
            {
                "proofs": {hash_chain, trust_anchor, signatures, ledger},
                "all_verified": bool,
                "summary": str,
            }

        In environments where ADR-0034 (decree_signatures module) is
        not yet implemented, Proof 3 returns status='skipped' — this
        is expected and documented, NOT a hard failure.
        """
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")

            old_env = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = anchor_path
            try:
                dl = DecreeLog(db_path)
                dl.issue("Decree 1 — the human is PID=1", category="law")
                publish_trust_anchor(dl, anchor_path=anchor_path)

                audit = ProvenAudit(dl)  # no public_key, no ledger
                result = audit.verify_4_proofs()

                # Top-level schema must include proofs + all_verified + summary.
                self.assertIn("proofs", result,
                              "result must include 'proofs' dict")
                self.assertIn("all_verified", result,
                              "result must include 'all_verified' bool")
                self.assertIn("summary", result,
                              "result must include 'summary' str")

                # all_verified must be a bool.
                self.assertIsInstance(result["all_verified"], bool,
                                      "all_verified must be a bool")

                # summary must be a non-empty string.
                self.assertIsInstance(result["summary"], str)
                self.assertTrue(len(result["summary"]) > 0,
                                "summary must be a non-empty string")

                # All four proof keys must be present in the proofs dict.
                expected_keys = {"hash_chain", "trust_anchor",
                                 "signatures", "ledger"}
                self.assertEqual(set(result["proofs"].keys()), expected_keys,
                                 f"proofs dict must have exactly the 4 "
                                 f"expected keys. Got: "
                                 f"{set(result['proofs'].keys())}")

                # Each proof must have at least verified + status + detail.
                for key in expected_keys:
                    proof = result["proofs"][key]
                    self.assertIn("verified", proof,
                                  f"proof {key} must have 'verified' field")
                    self.assertIn("status", proof,
                                  f"proof {key} must have 'status' field")
                    self.assertIn("detail", proof,
                                  f"proof {key} must have 'detail' field")
                    self.assertIsInstance(proof["verified"], bool,
                                          f"proof {key} 'verified' must be bool")
                    self.assertIn(proof["status"],
                                  {"verified", "failed", "skipped"},
                                  f"proof {key} 'status' must be one of "
                                  f"verified/failed/skipped. Got: "
                                  f"{proof['status']}")

                # Proof 1 (hash_chain) should verify on a fresh log.
                self.assertTrue(result["proofs"]["hash_chain"]["verified"],
                                "Proof 1 (hash_chain) must verify on a "
                                "fresh valid log")

                # Proof 2 (trust_anchor) should verify (we published).
                self.assertTrue(result["proofs"]["trust_anchor"]["verified"],
                                "Proof 2 (trust_anchor) must verify when "
                                "the anchor matches")

                # Proof 3 (signatures) is expected to be SKIPPED in
                # environments where the decree_signatures module is not
                # available. This is NOT a hard failure — it's a
                # documented gap per ADR-0036.
                if result["proofs"]["signatures"]["status"] == "skipped":
                    # Skipped is fine — the audit can still pass.
                    pass
                else:
                    # If the module IS available, the proof must be
                    # verified or failed (not silently wrong).
                    self.assertIn(result["proofs"]["signatures"]["status"],
                                  {"verified", "failed"})

                # Proof 4 (ledger) is expected to be SKIPPED when no
                # ledger was supplied (the default in this test).
                self.assertEqual(
                    result["proofs"]["ledger"]["status"], "skipped",
                    f"Proof 4 (ledger) must be 'skipped' when no ledger "
                    f"was supplied. Got: "
                    f"{result['proofs']['ledger']['status']}"
                )

                # all_verified must be True (no proof is 'failed' —
                # signatures is skipped (OK), ledger is skipped (OK),
                # the other two are verified).
                self.assertTrue(result["all_verified"],
                                f"all_verified must be True when no proof "
                                f"is 'failed'. Got: {result}")

                # Summary must mention the proof count (4).
                self.assertIn("4", result["summary"],
                              f"summary must mention the proof count (4). "
                              f"Got: {result['summary']}")
                dl.close()
            finally:
                if old_env is None:
                    os.environ.pop("POLYMATH_OS_TRUST_ANCHOR_PATH", None)
                else:
                    os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = old_env

    # ---------------------------------------------------------------- 4
    def test_audit_report_readable(self):
        """audit_report() returns a non-empty multi-line string with all
        four PROOF headers + the SUMMARY line.

        Per ADR-0036 §Decision: the report format is:
            === Proven-Based Audit Report (ADR-0036) ===
            Generated: <ISO timestamp>
            Decree log: <path>
            Total decrees: <count>

            PROOF 1: HASH-CHAIN INTEGRITY (ADR-0021)
              Status: VERIFIED
              Detail: ...

            PROOF 2: TRUST ANCHOR MATCH (ADR-0029 §9, IAEA pattern)
              Status: VERIFIED
              Detail: ...

            PROOF 3: ED25519 SIGNATURES (ADR-0034)
              Status: SKIPPED
              Detail: ...

            PROOF 4: EVIDENCE LEDGER COMPLETENESS (ADR-0019)
              Status: SKIPPED
              Detail: ...

            SUMMARY: <one-line summary>

        The report must be human-readable (no JSON, no binary).
        """
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "decrees.db")
            anchor_path = str(Path(tmp) / "trust_anchor.json")

            old_env = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = anchor_path
            try:
                dl = DecreeLog(db_path)
                dl.issue("Decree 1 — the human is PID=1", category="law")
                dl.issue("Decree 2 — never use Google DNS", category="prohibition")
                publish_trust_anchor(dl, anchor_path=anchor_path)

                audit = ProvenAudit(dl)
                report = audit.audit_report()

                # Must be a string.
                self.assertIsInstance(report, str,
                                      "audit_report() must return a string")

                # Must be non-empty.
                self.assertTrue(len(report) > 0,
                                "audit_report() must return a non-empty string")

                # Must contain the header.
                self.assertIn("Proven-Based Audit Report", report,
                              "report must contain the header")
                self.assertIn("ADR-0036", report,
                              "report must reference ADR-0036")

                # Must contain a Generated timestamp (ISO 8601 UTC).
                self.assertIn("Generated:", report,
                              "report must contain a 'Generated:' timestamp line")

                # Must contain the Decree log path.
                self.assertIn("Decree log:", report,
                              "report must contain a 'Decree log:' line")

                # Must contain the Total decrees line.
                self.assertIn("Total decrees:", report,
                              "report must contain a 'Total decrees:' line")

                # Must contain all four PROOF headers.
                self.assertIn("PROOF 1: HASH-CHAIN INTEGRITY", report,
                              "report must contain PROOF 1 header")
                self.assertIn("PROOF 2: TRUST ANCHOR MATCH", report,
                              "report must contain PROOF 2 header")
                self.assertIn("PROOF 3: ED25519 SIGNATURES", report,
                              "report must contain PROOF 3 header")
                self.assertIn("PROOF 4: EVIDENCE LEDGER COMPLETENESS", report,
                              "report must contain PROOF 4 header")

                # Each proof must have a Status line.
                # (with at least one VERIFIED and at least one SKIPPED
                # given the test setup.)
                self.assertGreaterEqual(
                    report.count("Status:"), 4,
                    "report must have a Status: line for each of the 4 proofs"
                )

                # Each proof must have a Detail line.
                self.assertGreaterEqual(
                    report.count("Detail:"), 4,
                    "report must have a Detail: line for each of the 4 proofs"
                )

                # Must contain the SUMMARY line.
                self.assertIn("SUMMARY:", report,
                              "report must contain a SUMMARY: line")

                # Summary line must mention "proofs verified".
                self.assertIn("proofs verified", report,
                              "report summary must mention 'proofs verified'")

                # Must NOT be JSON — sanity check by ensuring it doesn't
                # start with { or end with }.
                stripped = report.strip()
                self.assertFalse(
                    stripped.startswith("{") and stripped.endswith("}"),
                    "report must be human-readable, not a JSON blob"
                )

                # The Status values must appear in uppercase (VERIFIED /
                # FAILED / SKIPPED) per ADR-0036 §Decision format.
                # We expect at least one VERIFIED (Proofs 1 + 2) and at
                # least one SKIPPED (Proofs 3 + 4 in this test setup).
                self.assertIn("VERIFIED", report,
                              "report must contain at least one VERIFIED status")
                self.assertIn("SKIPPED", report,
                               "report must contain at least one SKIPPED status "
                               "(Proof 3 without decree_signatures module "
                               "and/or Proof 4 without a ledger)")

                dl.close()
            finally:
                if old_env is None:
                    os.environ.pop("POLYMATH_OS_TRUST_ANCHOR_PATH", None)
                else:
                    os.environ["POLYMATH_OS_TRUST_ANCHOR_PATH"] = old_env


if __name__ == "__main__":
    unittest.main()
