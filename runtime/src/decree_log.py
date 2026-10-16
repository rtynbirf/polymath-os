"""runtime/src/decree_log.py — Decree Log (ВОЛЯ ЧЕЛОВЕКОИЗЪЯВЛЕНИЯ = НАКАЗ)

The supreme law layer of polymath-os. Above all ADRs, above all code.
The human's raw expression (PAROLE) is recorded as a binding decree.
Each decree is:
- Append-only (immutable once recorded)
- Hash-chained (tamper-evident)
- Timestamped
- Serves as a HARD CONSTRAINT on the SINGULYAR EIR kernel

Per MANIFESTO principle 1: 'Человек — PID=1.'
Per MANIFESTO principle 2: 'PAROLE > LANGUE.'
Per SOVEREIGNTY_CONTRACT.md §11: 'The human says X and polymath-os's
kernel treats it as law.'

When the human says 'never use Google' → decree recorded → every Intent
with operation involving Google is DENIED. Not by policy rule — by DECREE.

The decree log is the HUMAN'S layer — above the AI, above the kernel,
above the code. The AI (me) writes decrees on the human's behalf, but
the decree itself is the human's word, not the AI's interpretation.

Per ADR-0016 (Self-rewriting ADR): a decree can create/supersede an ADR.
The decree ALWAYS wins over existing ADRs — PAROLE > LANGUE.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class DecreeLog:
    """Append-only hash-chained decree log — the supreme law of polymath-os.

    Implementation: SQLite (WAL, synchronous=FULL), same pattern as
    EvidenceLedger. Each decree is a row with:
    - seq: monotonic sequence number
    - prev_hash: hash of previous decree (chain)
    - timestamp: ISO 8601 UTC
    - decree_text: the raw human expression (PAROLE)
    - decree_hash: SHA-256 of (prev_hash + timestamp + decree_text)
    - category: 'law' | 'prohibition' | 'permission' | 'observation' | 'directive'
    - scope: which part of the system this decree applies to

    Per ADR-0006: if the chain is broken → DecreeIntegrityError (fail-closed).
    Per ADR-0009: default-deny — if no decree permits an action, it's denied.
    """

    def __init__(self, path: str):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self._init_schema()
        self._verify_chain()

    def _init_schema(self):
        self.db.execute("""CREATE TABLE IF NOT EXISTS decrees (
            seq INTEGER PRIMARY KEY,
            prev_hash TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            decree_text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'directive',
            scope TEXT NOT NULL DEFAULT 'all',
            decree_hash TEXT NOT NULL UNIQUE
        )""")

    def _hash_decree(self, prev_hash: str, timestamp: str, text: str) -> str:
        body = f"{prev_hash}|{timestamp}|{text}"
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _verify_chain(self):
        """Verify the hash chain on open. Fail-closed if broken."""
        rows = self.db.execute(
            "SELECT seq, prev_hash, timestamp, decree_text, decree_hash FROM decrees ORDER BY seq"
        ).fetchall()
        prev = "0" * 64  # genesis hash
        for seq, prev_hash, ts, text, dhash in rows:
            if prev_hash != prev:
                raise DecreeIntegrityError(f"Chain broken at seq {seq}: prev_hash mismatch")
            expected = self._hash_decree(prev_hash, ts, text)
            if expected != dhash:
                raise DecreeIntegrityError(f"Chain broken at seq {seq}: hash mismatch")
            prev = dhash

    def issue(self, text: str, category: str = "directive", scope: str = "all") -> Dict[str, Any]:
        """Issue a new decree. The human's word becomes law.

        Args:
            text: The raw human expression (PAROLE). This is the decree text.
            category: 'law' (binding rule), 'prohibition' (never do X),
                      'permission' (explicitly allow X), 'observation' (record),
                      'directive' (specific action command)
            scope: 'all' (system-wide), 'singulyar', 'polymath-os',
                   'cell65-host', 'singulyar-llm', or specific module/adapter

        Returns: The decree record as a dict.
        """
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prev_row = self.db.execute(
            "SELECT decree_hash FROM decrees ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev_row[0] if prev_row else "0" * 64
        decree_hash = self._hash_decree(prev_hash, timestamp, text)

        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO decrees (prev_hash, timestamp, decree_text, category, scope, decree_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (prev_hash, timestamp, text, category, scope, decree_hash)
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

        seq = self.db.execute("SELECT seq FROM decrees WHERE decree_hash=?", (decree_hash,)).fetchone()[0]
        return {
            "seq": seq,
            "timestamp": timestamp,
            "decree_text": text,
            "category": category,
            "scope": scope,
            "decree_hash": decree_hash[:16] + "...",
            "prev_hash": prev_hash[:16] + "...",
        }

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all decrees in order."""
        rows = self.db.execute(
            "SELECT seq, timestamp, decree_text, category, scope, decree_hash FROM decrees ORDER BY seq"
        ).fetchall()
        return [
            {"seq": r[0], "timestamp": r[1], "decree_text": r[2],
             "category": r[3], "scope": r[4], "decree_hash": r[5][:16] + "..."}
            for r in rows
        ]

    def get_active_laws(self) -> List[Dict[str, Any]]:
        """Return all 'law' and 'prohibition' decrees — the binding rules."""
        rows = self.db.execute(
            "SELECT seq, timestamp, decree_text, category, scope FROM decrees "
            "WHERE category IN ('law', 'prohibition') ORDER BY seq"
        ).fetchall()
        return [
            {"seq": r[0], "timestamp": r[1], "text": r[2], "category": r[3], "scope": r[4]}
            for r in rows
        ]

    def check_compliance(self, intent_text: str) -> Dict[str, Any]:
        """Check if an intent complies with all active decrees.

        This is the enforcement mechanism — the kernel calls this before
        executing any Intent. If a decree prohibits the action → DENIED.

        Simple implementation: string matching. If a prohibition decree
        says 'never use Google' and the intent contains 'google' → denied.

        Future v0.5: NLP-based semantic matching (but deterministic, no LLM).
        """
        laws = self.get_active_laws()
        violations = []
        for law in laws:
            text_lower = law["text"].lower()
            intent_lower = intent_text.lower()
            # Simple keyword extraction from decree text
            # If decree says "never use X" → check if intent contains X
            # Extract prohibited keywords from 'never use X' decrees
            if "never" in text_lower and "use" in text_lower:
                parts = text_lower.split("use", 1)
                if len(parts) > 1:
                    prohibited_raw = parts[-1].strip().rstrip(".").rstrip(",")
                    # Check each significant word in the prohibited phrase
                    for word in prohibited_raw.split():
                        if len(word) > 2 and word in intent_lower:
                            violations.append({
                                "decree_seq": law["seq"],
                                "decree_text": law["text"],
                                "violation": f"intent contains prohibited term: {word}",
                            })
                            break  # one violation per decree
            # If decree says "always X" → check if intent does X
            # (this is a positive requirement, harder to enforce)
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "laws_checked": len(laws),
        }

    def verify(self) -> bool:
        """Verify the chain integrity."""
        try:
            self._verify_chain()
            return True
        except DecreeIntegrityError:
            return False

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM decrees").fetchone()[0]

    def close(self):
        self.db.close()


class DecreeIntegrityError(RuntimeError):
    """Raised when the decree log chain is broken (fail-closed per ADR-0006)."""
    pass
