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


def publish_trust_anchor(decree_log, anchor_path: Optional[str] = None) -> str:
    """Publish the hash of the last decree to an external trust anchor file.

    Per ADR-0029 §9 (IAEA pattern): creates a file containing
    the last decree's hash + timestamp. This file is the
    'external seal' — if the decree log is rebuilt, this
    anchor won't match.

    Args:
        decree_log: DecreeLog instance
        anchor_path: path to trust anchor file (default: ~/.polymath-os/trust_anchor.json)

    Returns: path to the trust anchor file
    """
    if anchor_path is None:
        anchor_path = os.path.expanduser("~/.polymath-os/trust_anchor.json")

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
        anchor_path = os.path.expanduser("~/.polymath-os/trust_anchor.json")

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
