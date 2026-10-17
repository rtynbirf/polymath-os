# runtime/src/trust_anchor.py — External Trust Anchor (IAEA pattern, per ADR-0029 §9)
#
# Per IAEA nuclear safeguards: tamper-evidence requires an EXTERNAL
# verification point. The hash-chain proves internal integrity, but
# to prove the chain hasn't been REBUILT from scratch, the last
# hash must be published to an external trust anchor.
#
# This module publishes the hash of the last decree to a file
# that can be:
# - Printed (like a newspaper publication)
# - Stored on read-only media (USB, CD-R)
# - Sent to a trusted third party (lawyer, notary)
# - Published to a blockchain (future)
#
# If someone rebuilds the decree log from scratch, the external
# trust anchor will NOT match — tamper detected.

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional


def _default_anchor_path() -> str:
    """Resolve the default trust anchor file path.

    Resolution order (per Task 13-B integration of ADR-0029 §9):
      1. If env var POLYMATH_OS_TRUST_ANCHOR_PATH is set → use it verbatim.
         (Tests use this to redirect the anchor to a temp file so they
         don't pollute the user's real ~/.polymath-os/trust_anchor.json.
         Production deployments could also use it to put the anchor on
         read-only media like a USB stick mounted at a fixed path.)
      2. Otherwise → ~/.polymath-os/trust_anchor.json
         (the IAEA-pattern 'external seal' location — a file the human
         can print, copy to CD-R, send to a lawyer, etc.)
    """
    env = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
    if env:
        return env
    return os.path.expanduser("~/.polymath-os/trust_anchor.json")


def _default_db_path() -> str:
    """Resolve the default decree-log SQLite path.

    Resolution order (mirrors _default_anchor_path):
      1. Env var POLYMATH_OS_DECREE_DB if set.
      2. Otherwise → ~/.polymath-os/decrees.db (production default).
    """
    env = os.environ.get("POLYMATH_OS_DECREE_DB")
    if env:
        return env
    return os.path.expanduser("~/.polymath-os/decrees.db")


def publish_trust_anchor(decree_log, anchor_path: Optional[str] = None) -> str:
    """Publish the hash of the last decree to an external trust anchor file.

    Per ADR-0029 §9 (IAEA pattern): creates a file containing
    the last decree's hash + timestamp. This file is the
    'external seal' — if the decree log is rebuilt, this
    anchor won't match.

    Args:
        decree_log: DecreeLog instance
        anchor_path: path to trust anchor file (default: env var
            POLYMATH_OS_TRUST_ANCHOR_PATH or ~/.polymath-os/trust_anchor.json)

    Returns: path to the trust anchor file
    """
    if anchor_path is None:
        anchor_path = _default_anchor_path()

    # Get last decree
    all_decrees = decree_log.get_all()
    if not all_decrees:
        return None

    last = all_decrees[-1]
    # Get full hash
    row = decree_log.db.execute(
        "SELECT decree_hash FROM decrees WHERE seq = ?", (last["seq"],)
    ).fetchone()
    full_hash = row[0] if row else "unknown"

    anchor = {
        "last_decree_seq": last["seq"],
        "last_decree_hash": full_hash,
        "last_decree_text": last["decree_text"][:80],
        "total_decrees": decree_log.count(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "anchor_file": anchor_path,
    }

    os.makedirs(os.path.dirname(anchor_path), exist_ok=True)
    with open(anchor_path, "w") as f:
        json.dump(anchor, f, indent=2)

    return anchor_path


def verify_trust_anchor(decree_log, anchor_path: Optional[str] = None) -> dict:
    """Verify the decree log against an external trust anchor.

    Per ADR-0029 §9 (IAEA pattern): compares the last decree hash
    in the decree log with the hash stored in the external trust
    anchor file. If they don't match — TAMPER DETECTED.

    Returns: {verified: bool, anchor_seq, anchor_hash, current_hash, message}
    """
    if anchor_path is None:
        anchor_path = _default_anchor_path()

    if not os.path.exists(anchor_path):
        return {"verified": False, "message": "trust anchor file not found"}

    with open(anchor_path) as f:
        anchor = json.load(f)

    all_decrees = decree_log.get_all()
    if not all_decrees:
        return {"verified": False, "message": "decree log is empty"}

    # Find the decree at the anchor's seq
    anchor_seq = anchor.get("last_decree_seq", 0)
    matching = [d for d in all_decrees if d["seq"] == anchor_seq]

    if not matching:
        return {
            "verified": False,
            "anchor_seq": anchor_seq,
            "message": f"decree #{anchor_seq} not found in log — possible truncation",
        }

    current = matching[0]
    # Get full hash
    row = decree_log.db.execute(
        "SELECT decree_hash FROM decrees WHERE seq = ?", (anchor_seq,)
    ).fetchone()
    current_hash = row[0] if row else "unknown"

    if current_hash == anchor.get("last_decree_hash"):
        return {
            "verified": True,
            "anchor_seq": anchor_seq,
            "anchor_hash": anchor.get("last_decree_hash", "")[:16] + "...",
            "current_hash": current_hash[:16] + "...",
            "message": "trust anchor verified — no tampering detected",
        }
    else:
        return {
            "verified": False,
            "anchor_seq": anchor_seq,
            "anchor_hash": anchor.get("last_decree_hash", "")[:16] + "...",
            "current_hash": current_hash[:16] + "...",
            "message": "TAMPER DETECTED — hash mismatch at decree #" + str(anchor_seq),
        }


# ============================================================
# CLI: python3 -m runtime.src.trust_anchor publish|verify
# ============================================================
# Per Task 13-B §3: expose publish/verify as a CLI so the human
# (or an out-of-band auditor) can refresh / inspect the external
# seal WITHOUT writing a Python one-liner. This is the equivalent
# of IAEA's "publication" step — the operator runs `publish` to
# cut a fresh seal, and an auditor runs `verify` to compare the
# seal in their safe against the live decree log.
#
# The CLI respects the same env vars as the library functions:
#   POLYMATH_OS_TRUST_ANCHOR_PATH — override anchor file location
#   POLYMATH_OS_DECREE_DB         — override decree db location
def _cli(argv=None):
    """CLI entry point. Returns (exit_code, message) — does NOT sys.exit
    itself so it's testable in-process."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python3 -m runtime.src.trust_anchor",
        description="External Trust Anchor (IAEA pattern, ADR-0029 §9). "
                    "Publish/verify the hash of the last decree.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_pub = sub.add_parser("publish", help="Write the last decree's hash to the anchor file.")
    p_pub.add_argument(
        "--anchor", default=None,
        help="anchor file path (default: $POLYMATH_OS_TRUST_ANCHOR_PATH "
             "or ~/.polymath-os/trust_anchor.json)",
    )
    p_pub.add_argument(
        "--db", default=None,
        help="decree db path (default: $POLYMATH_OS_DECREE_DB "
             "or ~/.polymath-os/decrees.db)",
    )

    p_ver = sub.add_parser("verify", help="Compare the anchor's hash to the live decree log.")
    p_ver.add_argument("--anchor", default=None, help="anchor file path (see publish).")
    p_ver.add_argument("--db", default=None, help="decree db path (see publish).")
    p_ver.add_argument(
        "--quiet", action="store_true",
        help="emit only VERIFIED or TAMPERED (one line) for scripting.",
    )

    args = parser.parse_args(argv)
    db_path = args.db if args.db else _default_db_path()

    # Lazy import here to avoid a circular dependency at module load:
    # decree_log.py imports trust_anchor (auto-publish hook) and trust_anchor
    # CLI imports decree_log — the lazy import breaks the cycle and only
    # fires when the CLI is actually used.
    #
    # Robustness: when invoked as `python3 -m runtime.src.trust_anchor`,
    # the runtime/src directory is NOT on sys.path (only the repo root is).
    # Tests put runtime/src on sys.path via conftest.py; the production
    # `make verify` path uses scripts/check.py which also inserts it. The
    # CLI is invoked standalone, so it must self-insert the directory of
    # this file (= runtime/src) so that `from decree_log import DecreeLog`
    # works the same way it does in tests.
    import sys as _sys
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    from decree_log import DecreeLog

    if not os.path.exists(db_path):
        msg = f"decree db not found: {db_path}"
        if args.command == "publish":
            return 1, msg + " — issue a decree first (DecreeLog.issue)"
        return 1, msg

    dl = DecreeLog(db_path)

    try:
        if args.command == "publish":
            returned = publish_trust_anchor(dl, anchor_path=args.anchor)
            if returned is None:
                return 1, "decree log is empty — nothing to anchor (issue a decree first)"
            return 0, f"published trust anchor → {returned}"
        elif args.command == "verify":
            result = verify_trust_anchor(dl, anchor_path=args.anchor)
            if result.get("verified"):
                if args.quiet:
                    return 0, "VERIFIED"
                return 0, (
                    f"VERIFIED — seq={result.get('anchor_seq')} "
                    f"anchor={result.get('anchor_hash')} "
                    f"current={result.get('current_hash')} — "
                    f"{result.get('message')}"
                )
            else:
                if args.quiet:
                    return 2, "TAMPERED"
                return 2, f"TAMPERED — {result.get('message')}"
    finally:
        dl.close()


if __name__ == "__main__":
    import sys as _sys
    _code, _msg = _cli()
    _sys.stdout.write(_msg + "\n")
    _sys.exit(_code)

