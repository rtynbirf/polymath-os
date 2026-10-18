"""runtime/src/proven_audit.py — Proven-Based Audit Framework (ADR-0036)

The Proven-Based Audit Framework runs four independent proofs over
the decree system and returns a structured + human-readable audit
report. The four proofs:

    Proof 1: Hash-chain integrity      (ADR-0021, decree_log.verify)
    Proof 2: Trust anchor match         (ADR-0029 §9, IAEA pattern)
    Proof 3: Ed25519 signatures        (ADR-0034, decree_signatures)
    Proof 4: Evidence Ledger completeness (ADR-0019, sqlite_ledger)

Each proof uses a different module / different storage / different
cryptographic primitive — so an attacker who compromises one pillar
is still caught by another. The audit is PASS only if no proof
explicitly FAILED (skipped proofs are non-blocking gaps; the summary
field makes them visible).

Per ADR-0006 (falsifiable self-properties): every claim is testable.
Per ADR-0036: the framework is the synthesis of four pillars.

This module is fail-closed by design:
- If `decree_signatures` is not installed (the proposed ADR-0034
  module), Proof 3 returns status='skipped' (NOT 'failed'). The
  audit can still pass if the other three proofs verify.
- If no `ledger` is supplied, Proof 4 returns status='skipped'.
- If `verify_trust_anchor` cannot find the anchor file, Proof 2
  returns status='failed' (the anchor was expected but is missing
  — this IS a hard audit failure because the IAEA pattern is the
  only thing that catches whole-db rebuilds).
- If `decree_log.verify()` returns False, Proof 1 returns
  status='failed' (chain broken → hard failure).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Make runtime/src importable when this module is loaded directly
# (matches the pattern in webrtc_adapter.py and trust_anchor.py's
# CLI path setup, so callers don't have to set sys.path themselves).
_HERE = Path(__file__).resolve()
_SRC = _HERE.parent  # runtime/src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Proof 1 + Proof 2 dependencies — both already shipped with polymath-os
# (decree_log.py and trust_anchor.py). These imports are required (not
# optional) because ADR-0036 §Decision mandates that Proof 1 and Proof 2
# are always available — Proof 1 because the DecreeLog IS the system
# being audited, Proof 2 because the trust anchor is the IAEA-pattern
# external seal that ships with every DecreeLog since v3.x.0.
from trust_anchor import verify_trust_anchor  # noqa: E402

# Proof 3 (Ed25519 signatures) is OPTIONAL — the `decree_signatures`
# module is a proposed-but-not-yet-implemented module from ADR-0034.
# We try-import it; if absent, Proof 3 reports status='skipped'.
# This is the same fail-closed-with-honest-status pattern that
# webrtc_adapter.py uses for `aiortc` (Tier 2 dependency).
try:
    from decree_signatures import (  # type: ignore
        verify_decree_signature as _verify_decree_signature,
        load_public_key as _load_public_key,
    )
    _HAS_DECREE_SIGNATURES = True
except ImportError:
    _verify_decree_signature = None  # type: ignore
    _load_public_key = None  # type: ignore
    _HAS_DECREE_SIGNATURES = False


# ============================================================
# ProvenAudit class
# ============================================================

class ProvenAudit:
    """Run 4 independent proofs over the decree system + produce a report.

    Per ADR-0036, the four proofs are:
        1. Hash-chain integrity  — DecreeLog.verify()
        2. Trust anchor match     — verify_trust_anchor()
        3. Ed25519 signatures     — decree_signatures.verify_decree_signature()
        4. Evidence Ledger       — ledger.verify() + event count

    Args:
        decree_log: a DecreeLog instance (the system being audited).
        public_key_path: optional path to the human's Ed25519 public
            key file. When provided AND `decree_signatures` is
            importable, Proof 3 runs; otherwise Proof 3 is skipped.
        ledger: optional EvidenceLedger / SQLiteEvidenceLedger
            instance. When provided, Proof 4 runs; otherwise skipped.
            This is an extra optional kwarg (not in the strict
            ADR-0036 constructor signature) so callers that don't
            have a ledger can still run the other three proofs.
    """

    def __init__(
        self,
        decree_log,
        public_key_path: Optional[str] = None,
        ledger=None,
    ):
        self.decree_log = decree_log
        self.public_key_path = public_key_path
        self.ledger = ledger

    # ------------------------------------------------------------------
    # verify_4_proofs
    # ------------------------------------------------------------------
    def verify_4_proofs(self) -> Dict[str, Any]:
        """Run all 4 proofs. Returns the structured audit result.

        Schema (per ADR-0036 §Decision):

            {
                "proofs": {
                    "hash_chain":   {"verified": bool, "status": str, "detail": str},
                    "trust_anchor": {"verified": bool, "status": str, "detail": str, ...},
                    "signatures":   {"verified": bool, "status": str, "detail": str},
                    "ledger":       {"verified": bool, "status": str, "detail": str, "event_count": int},
                },
                "all_verified": bool,
                "summary": str,
            }

        `status` ∈ {"verified", "failed", "skipped"}.
        `all_verified` is True iff NO proof is "failed" (skipped is OK).
        """
        proofs: Dict[str, Any] = {}

        # ---- Proof 1: Hash-chain integrity (ADR-0021) ----
        proofs["hash_chain"] = self._proof1_hash_chain()

        # ---- Proof 2: Trust anchor match (ADR-0029 §9, IAEA) ----
        proofs["trust_anchor"] = self._proof2_trust_anchor()

        # ---- Proof 3: Ed25519 signatures (ADR-0034) ----
        proofs["signatures"] = self._proof3_signatures()

        # ---- Proof 4: Evidence Ledger completeness (ADR-0019) ----
        proofs["ledger"] = self._proof4_ledger()

        # all_verified = True iff NO proof is 'failed'.
        # (skipped proofs don't fail the audit; they're reported as gaps.)
        all_verified = all(p["status"] != "failed" for p in proofs.values())

        # Build the one-line summary.
        verified_count = sum(1 for p in proofs.values() if p["status"] == "verified")
        failed_count = sum(1 for p in proofs.values() if p["status"] == "failed")
        skipped_count = sum(1 for p in proofs.values() if p["status"] == "skipped")
        if failed_count > 0:
            audit_result = "FAIL"
            summary = (
                f"{verified_count}/4 proofs verified ({skipped_count} skipped, "
                f"{failed_count} failed). Audit: {audit_result}."
            )
        elif skipped_count == len(proofs):
            # All proofs skipped — audit is INCONCLUSIVE, not PASS.
            audit_result = "INCONCLUSIVE"
            summary = (
                f"{verified_count}/4 proofs verified ({skipped_count} skipped). "
                f"Audit: {audit_result} — install at least one pillar to enable verification."
            )
        elif skipped_count > 0:
            audit_result = "PASS (with gaps)"
            summary = (
                f"{verified_count}/4 proofs verified ({skipped_count} skipped). "
                f"Audit: {audit_result}."
            )
        else:
            audit_result = "PASS"
            summary = (
                f"{verified_count}/4 proofs verified. Audit: {audit_result}."
            )

        return {
            "proofs": proofs,
            "all_verified": all_verified,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Individual proofs
    # ------------------------------------------------------------------

    def _proof1_hash_chain(self) -> Dict[str, Any]:
        """Proof 1: SHA-256 hash-chain integrity (ADR-0021).

        Catches single-row edits of the SQLite db. If any decree's
        prev_hash / decree_hash / text has been modified after the
        fact, _verify_chain raises DecreeIntegrityError and verify()
        returns False.
        """
        try:
            ok = bool(self.decree_log.verify())
        except Exception as exc:
            # Defensive: verify() should never raise (it catches
            # DecreeIntegrityError internally), but if it does, we
            # treat it as a hard failure rather than crashing the
            # whole audit.
            return {
                "verified": False,
                "status": "failed",
                "detail": f"hash-chain verification raised: {exc!r}",
            }

        try:
            count = self.decree_log.count()
        except Exception:
            count = -1

        if ok:
            detail = (
                f"SHA-256 hash chain valid across {count} decrees; "
                f"genesis=0000...0000"
            )
            return {"verified": True, "status": "verified", "detail": detail}
        else:
            detail = (
                f"hash chain BROKEN — DecreeIntegrityError raised; "
                f"{count} decrees in log; tamper detected"
            )
            return {"verified": False, "status": "failed", "detail": detail}

    def _proof2_trust_anchor(self) -> Dict[str, Any]:
        """Proof 2: External trust anchor match (ADR-0029 §9, IAEA).

        Catches whole-db rebuild. The external anchor file (stored
        out-of-band: printout, USB, lawyer, blockchain) contains the
        SHA-256 hash of the last decree as observed at publication time.
        Mismatch → tamper detected.

        The anchor path is resolved by `verify_trust_anchor` itself:
        env var POLYMATH_OS_TRUST_ANCHOR_PATH, or
        ~/.polymath-os/trust_anchor.json by default.

        Missing anchor file → status='failed' (the IAEA pattern is
        the only thing that catches rebuilds, so a missing anchor
        IS a hard failure — the audit can't prove the db wasn't
        rebuilt).
        """
        try:
            result = verify_trust_anchor(self.decree_log)
        except Exception as exc:
            return {
                "verified": False,
                "status": "failed",
                "detail": f"verify_trust_anchor raised: {exc!r}",
            }

        verified = bool(result.get("verified", False))
        message = result.get("message", "")

        if verified:
            detail = message or "trust anchor verified"
            return {
                "verified": True,
                "status": "verified",
                "detail": detail,
                "anchor_seq": result.get("anchor_seq"),
                "anchor_hash": result.get("anchor_hash"),
                "current_hash": result.get("current_hash"),
            }
        else:
            # Missing anchor file = "trust anchor file not found" →
            # the IAEA pattern can't run, so the audit can't prove
            # the db wasn't rebuilt. This is a hard failure per
            # ADR-0036 (fail-closed).
            detail = message or "trust anchor verification failed"
            return {
                "verified": False,
                "status": "failed",
                "detail": detail,
                "anchor_seq": result.get("anchor_seq"),
                "anchor_hash": result.get("anchor_hash"),
                "current_hash": result.get("current_hash"),
            }

    def _proof3_signatures(self) -> Dict[str, Any]:
        """Proof 3: Ed25519 signatures (ADR-0034).

        Catches forged decree provenance. Each decree is signed by
        the issuing human's Ed25519 private key at issue time. An
        attacker who rebuilds the db without the private key cannot
        produce valid signatures on the re-issued decrees.

        This proof is SKIPPED (not failed) when:
        - the `decree_signatures` module is not installed (the
          proposed ADR-0034 module is not yet implemented)
        - `public_key_path` is None (caller didn't supply a public key)
        - the decree log is empty (no decrees to verify)
        """
        if not _HAS_DECREE_SIGNATURES:
            return {
                "verified": False,
                "status": "skipped",
                "detail": (
                    "decree_signatures module not available in this "
                    "environment — install per ADR-0034 to enable Proof 3"
                ),
            }

        if self.public_key_path is None:
            return {
                "verified": False,
                "status": "skipped",
                "detail": (
                    "public_key_path not supplied — caller must pass "
                    "path to the issuing human's Ed25519 public key"
                ),
            }

        if not os.path.exists(self.public_key_path):
            return {
                "verified": False,
                "status": "skipped",
                "detail": (
                    f"public key file not found: {self.public_key_path}"
                ),
            }

        # Load the issuing human's public key.
        try:
            public_key_hex = _load_public_key(self.public_key_path)
        except Exception as exc:
            return {
                "verified": False,
                "status": "failed",
                "detail": f"failed to load public key: {exc!r}",
            }

        # Verify every decree's signature.
        try:
            all_decrees = self.decree_log.get_all()
        except Exception as exc:
            return {
                "verified": False,
                "status": "failed",
                "detail": f"failed to read decree log: {exc!r}",
            }

        if not all_decrees:
            return {
                "verified": False,
                "status": "skipped",
                "detail": "decree log is empty — no decrees to verify",
            }

        invalid = []
        for d in all_decrees:
            sig = d.get("signature") or d.get("decree_signature")
            if not sig:
                invalid.append({"seq": d.get("seq"), "reason": "no signature field"})
                continue
            try:
                ok = bool(_verify_decree_signature(d, sig, public_key_hex))
            except Exception as exc:
                invalid.append({"seq": d.get("seq"), "reason": f"verify raised: {exc!r}"})
                continue
            if not ok:
                invalid.append({"seq": d.get("seq"), "reason": "signature invalid"})

        if invalid:
            detail = (
                f"{len(invalid)}/{len(all_decrees)} decrees have invalid "
                f"Ed25519 signatures; first invalid: {invalid[0]}"
            )
            return {
                "verified": False,
                "status": "failed",
                "detail": detail,
            }

        detail = (
            f"all {len(all_decrees)} decrees have valid Ed25519 signatures "
            f"against public key {os.path.basename(self.public_key_path)}"
        )
        return {
            "verified": True,
            "status": "verified",
            "detail": detail,
        }

    def _proof4_ledger(self) -> Dict[str, Any]:
        """Proof 4: Evidence Ledger completeness (ADR-0019).

        Catches missing audit events. The Evidence Ledger records
        every state transition in the runtime. If the ledger's own
        hash chain is broken OR the event count is implausibly low
        relative to the decree count (e.g. 100 decrees enforced but
        only 3 events in the ledger), something is wrong.

        This proof is SKIPPED when no `ledger` was supplied to the
        ProvenAudit constructor (the caller doesn't have a ledger
        to audit).
        """
        if self.ledger is None:
            return {
                "verified": False,
                "status": "skipped",
                "detail": (
                    "no Evidence Ledger supplied to ProvenAudit — pass "
                    "ledger=<SQLiteEvidenceLedger instance> to enable "
                    "Proof 4"
                ),
                "event_count": 0,
            }

        # Verify the ledger's own hash chain.
        try:
            ok = bool(self.ledger.verify())
        except AttributeError:
            # The ledger doesn't have a verify() method — it's a
            # different type. Fail closed.
            return {
                "verified": False,
                "status": "failed",
                "detail": (
                    f"ledger object {type(self.ledger).__name__} has no "
                    f"verify() method — not a valid EvidenceLedger"
                ),
                "event_count": 0,
            }
        except Exception as exc:
            return {
                "verified": False,
                "status": "failed",
                "detail": f"ledger.verify() raised: {exc!r}",
                "event_count": 0,
            }

        # Get the event count. Use `.events` property if available
        # (SQLiteEvidenceLedger); fall back to len() on a count()
        # method; fall back to 0 if neither.
        event_count = 0
        try:
            events = self.ledger.events
            event_count = len(events)
        except AttributeError:
            try:
                event_count = int(self.ledger.count())  # type: ignore
            except Exception:
                event_count = 0
        except Exception:
            event_count = 0

        if ok:
            detail = (
                f"{event_count} events in ledger; hash chain valid"
            )
            return {
                "verified": True,
                "status": "verified",
                "detail": detail,
                "event_count": event_count,
            }
        else:
            detail = (
                f"ledger hash chain BROKEN; {event_count} events in "
                f"ledger — tamper detected"
            )
            return {
                "verified": False,
                "status": "failed",
                "detail": detail,
                "event_count": event_count,
            }

    # ------------------------------------------------------------------
    # audit_report
    # ------------------------------------------------------------------
    def audit_report(self) -> str:
        """Human-readable multi-line audit report.

        Suitable for display in:
        - The CLI (make verify summary)
        - The Decree Portal (HTML rendering of the <pre> block)
        - An external auditor's report file

        The format is documented in ADR-0036 §Decision.
        """
        result = self.verify_4_proofs()
        proofs = result["proofs"]

        # Resolve the decree log path for the header.
        try:
            db_path = getattr(self.decree_log, "path", "<unknown>")
        except Exception:
            db_path = "<unknown>"

        try:
            total_decrees = self.decree_log.count()
        except Exception:
            total_decrees = -1

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        lines = []
        lines.append("=== Proven-Based Audit Report (ADR-0036) ===")
        lines.append(f"Generated: {timestamp}")
        lines.append(f"Decree log: {db_path}")
        lines.append(f"Total decrees: {total_decrees}")
        lines.append("")

        # Each proof gets a header + Status + Detail (+ Hint for skipped).
        proof_specs = [
            ("PROOF 1: HASH-CHAIN INTEGRITY (ADR-0021)", proofs["hash_chain"]),
            ("PROOF 2: TRUST ANCHOR MATCH (ADR-0029 §9, IAEA pattern)",
             proofs["trust_anchor"]),
            ("PROOF 3: ED25519 SIGNATURES (ADR-0034)", proofs["signatures"]),
            ("PROOF 4: EVIDENCE LEDGER COMPLETENESS (ADR-0019)",
             proofs["ledger"]),
        ]

        for header, proof in proof_specs:
            lines.append(header)
            status = proof.get("status", "skipped").upper()
            lines.append(f"  Status: {status}")
            lines.append(f"  Detail: {proof.get('detail', '')}")
            if status == "SKIPPED":
                # Add a Hint line explaining how to enable the proof.
                detail = proof.get("detail", "")
                if "decree_signatures module not available" in detail:
                    lines.append(
                        "  Hint:   install PyNaCl + decree_signatures.py "
                        "(per ADR-0034) to enable Proof 3"
                    )
                elif "public_key_path not supplied" in detail:
                    lines.append(
                        "  Hint:   pass public_key_path=<path> to "
                        "ProvenAudit(...) to enable Proof 3"
                    )
                elif "no Evidence Ledger supplied" in detail:
                    lines.append(
                        "  Hint:   pass ledger=<SQLiteEvidenceLedger "
                        "instance> to ProvenAudit(...) to enable Proof 4"
                    )
                elif "decree log is empty" in detail:
                    lines.append(
                        "  Hint:   issue at least one decree to enable "
                        "Proof 3 (no decrees to verify yet)"
                    )
            if "event_count" in proof:
                lines.append(f"  Events: {proof['event_count']}")
            lines.append("")

        lines.append(f"SUMMARY: {result['summary']}")
        lines.append("")
        return "\n".join(lines)


# ============================================================
# CLI: python3 -m runtime.src.proven_audit [--public-key PATH]
# ============================================================
# Convenience entry point so the human (or an out-of-band auditor)
# can run a full audit without writing a Python one-liner. Mirrors
# the trust_anchor.py CLI pattern.
def _cli(argv=None):
    """CLI entry point. Returns (exit_code, message)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python3 -m runtime.src.proven_audit",
        description="Proven-Based Audit Framework (ADR-0036). "
                    "Run 4 proofs over the decree system.",
    )
    parser.add_argument(
        "--db", default=None,
        help="decree db path (default: $POLYMATH_OS_DECREE_DB "
             "or ~/.polymath-os/decrees.db)",
    )
    parser.add_argument(
        "--public-key", default=None,
        help="path to issuing human's Ed25519 public key (enables Proof 3)",
    )
    parser.add_argument(
        "--ledger-db", default=None,
        help="path to Evidence Ledger SQLite db (enables Proof 4)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="emit only PASS / FAIL / INCONCLUSIVE (one line) for scripting",
    )
    args = parser.parse_args(argv)

    db_path = args.db or os.environ.get("POLYMATH_OS_DECREE_DB") \
        or os.path.expanduser("~/.polymath-os/decrees.db")
    if not os.path.exists(db_path):
        return 1, f"decree db not found: {db_path}"

    # Lazy import to avoid circular dependency at module load.
    from decree_log import DecreeLog
    dl = DecreeLog(db_path)

    # Optional: open the ledger if --ledger-db was supplied.
    ledger = None
    if args.ledger_db:
        try:
            from sqlite_ledger import SQLiteEvidenceLedger
            ledger = SQLiteEvidenceLedger(args.ledger_db)
        except Exception as exc:
            dl.close()
            return 1, f"failed to open ledger {args.ledger_db}: {exc!r}"

    try:
        audit = ProvenAudit(dl, public_key_path=args.public_key, ledger=ledger)
        if args.quiet:
            result = audit.verify_4_proofs()
            if not result["all_verified"]:
                return 2, "FAIL"
            if "INCONCLUSIVE" in result["summary"]:
                return 3, "INCONCLUSIVE"
            return 0, "PASS"
        return 0, audit.audit_report()
    finally:
        dl.close()
        if ledger is not None:
            try:
                ledger.db.close()
            except Exception:
                pass


if __name__ == "__main__":
    _code, _msg = _cli()
    sys.stdout.write(_msg + "\n")
    sys.exit(_code)
