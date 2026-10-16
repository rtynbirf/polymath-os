"""Durable SQLite-backed evidence ledger (same interface as EvidenceLedger).

- WAL + synchronous=FULL, explicit BEGIN IMMEDIATE per append (sequence allocated inside the txn).
- Chain is re-verified on open; a broken chain raises LedgerIntegrityError (fail closed).
- Tamper-evidence only: someone who can rewrite the DB AND recompute every hash is not detected
  unless a checkpoint was stored elsewhere (see checkpoint()/verify_against()).
"""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any, Dict, List

from singulyar_runtime import ZERO_HASH, _canonical, _hash_event


class LedgerIntegrityError(RuntimeError):
    pass


class SQLiteEvidenceLedger:
    def __init__(self, path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS evidence_events (
            seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL, time_ns INTEGER NOT NULL, event_hash TEXT NOT NULL UNIQUE)""")
        self._load()   # raises on a corrupt chain

    def _load(self) -> List[Dict[str, Any]]:
        rows = self.db.execute("SELECT seq, prev_hash, event_type, payload_json, time_ns, event_hash "
                               "FROM evidence_events ORDER BY seq").fetchall()
        events, prev = [], ZERO_HASH
        for expected_seq, (seq, prev_hash, etype, pj, tns, ehash) in enumerate(rows):
            try:
                payload = json.loads(pj)
            except json.JSONDecodeError as exc:
                raise LedgerIntegrityError(f"unparseable payload at seq={seq}") from exc
            body = {"seq": seq, "prev_hash": prev_hash, "type": etype, "payload": payload, "time_ns": tns}
            if seq != expected_seq or prev_hash != prev:
                raise LedgerIntegrityError(f"broken sequence/link at seq={seq}")
            if _hash_event(body) != ehash:
                raise LedgerIntegrityError(f"hash mismatch at seq={seq}")
            events.append(dict(body, hash=ehash))
            prev = ehash
        return events

    @property
    def events(self) -> List[Dict[str, Any]]:
        return self._load()

    @property
    def head(self) -> str:
        row = self.db.execute("SELECT event_hash FROM evidence_events ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else ZERO_HASH

    def append(self, event_type: str, payload: Dict[str, Any]):
        payload = json.loads(_canonical(payload))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT seq, event_hash FROM evidence_events ORDER BY seq DESC LIMIT 1").fetchone()
            seq, prev = (0, ZERO_HASH) if row is None else (row[0] + 1, row[1])
            body = {"seq": seq, "prev_hash": prev, "type": event_type, "payload": payload, "time_ns": time.time_ns()}
            digest = _hash_event(body)
            self.db.execute("INSERT INTO evidence_events VALUES (?,?,?,?,?,?)",
                            (seq, prev, event_type, _canonical(payload), body["time_ns"], digest))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return dict(body, hash=digest)

    def verify(self) -> bool:
        try:
            self._load()
            return True
        except LedgerIntegrityError:
            return False

    def checkpoint(self) -> Dict[str, Any]:
        ev = self._load()
        return {"count": len(ev), "hash": ev[-1]["hash"] if ev else ZERO_HASH}

    def verify_against(self, cp: Dict[str, Any]) -> bool:
        try:
            ev = self._load()
        except LedgerIntegrityError:
            return False
        if len(ev) < cp["count"]:
            return False
        return cp["count"] == 0 or ev[cp["count"] - 1]["hash"] == cp["hash"]

    def export_jsonl(self, destination):
        ev = self._load()   # refuses to export a broken chain by raising
        path = Path(destination)
        with path.open("w", encoding="utf-8") as fh:
            for e in ev:
                fh.write(_canonical(e) + "\n")
        return path

    def close(self):
        self.db.close()
