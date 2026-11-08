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
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# Recognized technical acronyms — when a 2-word prohibition's second word is one
# of these, classify it as a PHRASE (block on full phrase + head noun).
_RECOGNIZED_ACRONYMS = frozenset({
    "dns", "cdn", "api", "s3", "ec2", "ssh", "vpn", "smtp",
    "http", "https", "ftp", "sql", "rdp", "os", "db", "cli",
    "rest", "graphql", "grpc", "wsgi", "asgi",
})

# Regex to extract the prohibited phrase from a "never <verb> X" decree.
# Captures everything after "never <verb> " where verb ∈ {use, use the,
# install, deploy, run, adopt, rely on, send, share, transmit, expose}.
# Fixes v0.5 naive `text.split("use", 1)` parser which mis-parsed
# "never abuse any services" as prohibited="any services" (because "abuse"
# contains "use" as substring).
#
# v0.6.1 (v3.11.0) extension: added "send", "share", "transmit", "expose"
# to recognize data-flow prohibitions like "never send PII to external
# services" — needed for ADR-0025 outbound decree enforcement.
#
# Examples:
#   "never use Google DNS"            → captures "Google DNS"
#   "never use the Google DNS server" → captures "Google DNS server"
#   "never install Chrome"            → captures "Chrome"
#   "never rely on AWS"               → captures "AWS"
#   "never send PII to external"      → captures "PII to external" (v0.6.1 NEW)
#   "never share user data"           → captures "user data" (v0.6.1 NEW)
#   "never transmit credentials"      → captures "credentials" (v0.6.1 NEW)
#   "never expose secrets externally" → captures "secrets externally" (v0.6.1 NEW)
#   "never abuse any services"        → no match (verb "abuse" not in set)
_PROHIBITION_REGEX = re.compile(
    r"\bnever\s+(?:use(?:\s+the)?|install|deploy|run|adopt|rely\s+on|send|share|transmit|expose)\s+(.+?)\s*[.,;:!?]*$",
    re.IGNORECASE,
)

# Cache of compiled per-term regex patterns — avoids recompiling \b{term}\b
# on every check_compliance() call. Key: lowercase term. Value: compiled
# regex. Per-instance (not class-level) because DecreeLog instances may
# have different decree texts; but the cache key is the term itself, so
# repeated terms across instances benefit too.
_TERM_REGEX_CACHE: Dict[str, "re.Pattern"] = {}


def _compile_term_regex(term: str) -> "re.Pattern":
    """Compile a word-boundary regex for the given prohibited term.

    v0.6 — uses `\\b{re.escape(term)}\\b` instead of v0.5's substring check.
    This fixes the false positive where "chrome" matched "chromebook" (the
    word "chrome" appears as a substring of "chromebook" but NOT as a whole
    word).

    For multi-word terms like "google dns", the regex is `\\bgoogle dns\\b`
    (with the space inside the pattern, which is fine — \\b matches at the
    start of the first word and end of the last word).

    The regex is case-insensitive (uses re.IGNORECASE).
    """
    cached = _TERM_REGEX_CACHE.get(term)
    if cached is None:
        # Use re.escape to handle special regex chars in the term.
        # Word boundaries (\b) match at the start of the first word and end
        # of the last word.
        pattern = r"\b" + re.escape(term) + r"\b"
        cached = re.compile(pattern, re.IGNORECASE)
        _TERM_REGEX_CACHE[term] = cached
    return cached


# Known browser/technology proper nouns — even if a decree author forgets to
# capitalize them, these still count as proper nouns for LIST classification.
_KNOWN_PROPER_NOUNS = frozenset({
    "chrome", "firefox", "edge", "safari",
})

# v3.18.0: NSA compartmentalization (per ADR-0029 §7).
# Classification hierarchy for decrees: 'public' < 'internal' < 'secret'.
# An agent's clearance_level (set on AgentCard) determines which decrees it
# is permitted to see during check_compliance(). Lower rank = lower clearance.
# A decree with classification > caller's clearance is INVISIBLE to that caller
# — i.e. it is filtered out before the prohibition matcher runs. This means a
# 'secret' decree cannot block an intent from a 'public'-cleared agent — the
# agent literally doesn't know the decree exists.
_CLASSIFICATION_RANK: Dict[str, int] = {
    "public": 0,
    "internal": 1,
    "secret": 2,
}

# v3.19.0: Scope hierarchy (nested scopes).
# A scope with a HIGHER rank inherits all decrees from scopes with LOWER rank.
# So when checking compliance at scope="polymath-os" (rank 2), decrees scoped
# to "singulyar" (rank 1) AND "all" (rank 0) also apply — the more specific
# scope inherits the more general (parent) decrees. Conversely, checking at
# scope="singulyar" (rank 1) does NOT see decrees scoped to "polymath-os"
# (rank 2) — the parent doesn't see the child.
#
# Pre-v3.19.0 behavior was a flat 2-level filter: scope="all" (always applies)
# OR exact string match. v3.19.0 generalizes this into a true hierarchy so
# that, e.g., a polymath-os-scoped intent is bound by singulyar-scoped
# prohibitions (the whole-system scope "singulyar" governs sub-scopes).
#
# Unknown scopes default to rank 0 (treated as 'all' — fail-open at the scope
# axis; the decree axis remains default-deny).
_SCOPE_HIERARCHY: Dict[str, int] = {
    "all": 0,
    "singulyar": 1,
    "polymath-os": 2,
    "cell65-host": 3,
    "outbound": 1,
}


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

    def __init__(self, path: str, check_same_thread: bool = True):
        """Open the DecreeLog.

        Args:
            path: path to SQLite database file
            check_same_thread: passed to sqlite3.connect(). Set to False
                for use in threaded servers (e.g. AgentMeshServer per ADR-0027).
                Default True (safe — single-thread only). With False, the
                caller is responsible for ensuring no concurrent writes
                (WAL mode allows concurrent readers + 1 writer).
        """
        self.path = str(path)
        self.db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=check_same_thread)
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
            decree_hash TEXT NOT NULL UNIQUE,
            classification TEXT NOT NULL DEFAULT 'public',
            required_signatures INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT
        )""")

        # v3.18.0: Migration for pre-v3.18.0 databases that were created
        # without the `classification` column. ALTER TABLE ... ADD COLUMN is
        # idempotent-unsafe: SQLite raises OperationalError 'duplicate column
        # name' if the column already exists (e.g. on a freshly-created table
        # above). We catch + ignore that specific case. Existing rows get the
        # DEFAULT 'public' classification — preserving back-compat with the
        # 7 foundational decrees in ~/.polymath-os/decrees.db.
        try:
            self.db.execute(
                "ALTER TABLE decrees ADD COLUMN classification TEXT NOT NULL DEFAULT 'public'"
            )
        except sqlite3.OperationalError:
            # Column already exists — nothing to migrate.
            pass

        # v3.18.0 (N-of-M multi-sig, ADR-0029 §6): add required_signatures
        # column to pre-multi-sig databases. Same idempotent-unsafe pattern
        # as `classification` above — catch the duplicate-column error.
        # Existing rows get DEFAULT 1 (single-sig → active immediately).
        try:
            self.db.execute(
                "ALTER TABLE decrees ADD COLUMN required_signatures "
                "INTEGER NOT NULL DEFAULT 1"
            )
        except sqlite3.OperationalError:
            # Column already exists — nothing to migrate.
            pass

        # v3.19.0: Migration for the `expires_at` column (time-limited
        # decrees). NULL = no expiry (permanent — backward compatible with
        # all pre-v3.19.0 decrees, including the 7 foundational decrees in
        # ~/.polymath-os/decrees.db). Same idempotent-unsafe ALTER TABLE
        # pattern as `classification` and `required_signatures` above —
        # catch the duplicate-column OperationalError on freshly-created
        # tables where the column already exists.
        try:
            self.db.execute(
                "ALTER TABLE decrees ADD COLUMN expires_at TEXT"
            )
        except sqlite3.OperationalError:
            # Column already exists — nothing to migrate.
            pass

        # v3.17.0: Multi-signature (SWIFT pattern, per ADR-0029 §6)
        # Co-signatures for decrees that require N-of-M authorization
        self.db.execute("""CREATE TABLE IF NOT EXISTS co_signatures (
            decree_seq INTEGER NOT NULL,
            signer_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            PRIMARY KEY (decree_seq, signer_id),
            FOREIGN KEY (decree_seq) REFERENCES decrees(seq)
        )""")

        # v3.18.0 (N-of-M blocking): backfill an implicit _issuer co-signature
        # for every legacy decree that doesn't yet have one. This preserves
        # back-compat: legacy decrees had required_signatures=1 (the migration
        # above set the default) but no co_signatures row — under the new
        # "count >= required_signatures" rule they'd become INACTIVE (count=0
        # < 1). The issuer is the implicit first signer per SWIFT multi-sig
        # semantics, so we auto-record it. INSERT OR IGNORE makes this
        # idempotent across opens. For decrees issued via the new issue()
        # below, the _issuer row is already inserted at issue-time so this
        # is a no-op.
        self.db.execute(
            "INSERT OR IGNORE INTO co_signatures "
            "(decree_seq, signer_id, timestamp) "
            "SELECT seq, '_issuer', timestamp FROM decrees "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM co_signatures c "
            "  WHERE c.decree_seq = decrees.seq AND c.signer_id = '_issuer'"
            ")"
        )

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

    def issue(
        self,
        text: str,
        category: str = "directive",
        scope: str = "all",
        classification: str = "public",
        required_signatures: int = 1,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Issue a new decree. The human's word becomes law.

        Args:
            text: The raw human expression (PAROLE). This is the decree text.
            category: 'law' (binding rule), 'prohibition' (never do X),
                      'permission' (explicitly allow X), 'observation' (record),
                      'directive' (specific action command)
            scope: 'all' (system-wide), 'singulyar', 'polymath-os',
                   'cell65-host', 'singulyar-llm', or specific module/adapter.
                   Per v3.19.0 scope hierarchy, a decree scoped to a LOWER
                   rank (e.g. 'singulyar', rank 1) also applies when checking
                   compliance at a HIGHER rank (e.g. 'polymath-os', rank 2).
            classification: v3.18.0 — NSA compartmentalization label per ADR-0029 §7.
                      'public' (default; visible to all agents),
                      'internal' (visible to internal+secret cleared agents),
                      'secret' (visible only to secret-cleared agents).
                      Stored on the decree row; checked by check_compliance()
                      against the caller's `clearance` argument.
            required_signatures: v3.18.0 — N-of-M threshold (default 1 =
                      single-sig). The decree is PENDING (not enforced by
                      get_active_laws / check_compliance) until at least
                      `required_signatures` co-signatures exist in the
                      co_signatures table. The issuer is auto-recorded as
                      signer '_issuer' — so required_signatures=1 → active
                      immediately upon issue; required_signatures=N (N>1) →
                      requires N-1 additional explicit co_sign() calls.
                      Must be an int >= 1 (raises ValueError otherwise).
            expires_at: v3.19.0 — Optional ISO 8601 UTC datetime string
                      (e.g. '2999-01-01T00:00:00Z') marking when the decree
                      EXPIRES. After expires_at, the decree is automatically
                      excluded from get_active_laws() and therefore not
                      enforced by check_compliance() (the decree is still
                      in the append-only log — immutable, hash-chained —
                      but no longer binding). Default None = no expiry
                      (permanent — backward compatible with all
                      pre-v3.19.0 decrees). Comparison is a strict string
                      compare of ISO 8601 UTC values (lexicographic =
                      chronological for the fixed-width format).

        Returns: The decree record as a dict.
        """
        if not isinstance(required_signatures, int) or required_signatures < 1:
            raise ValueError(
                f"required_signatures must be an int >= 1, got {required_signatures!r}"
            )

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prev_row = self.db.execute(
            "SELECT decree_hash FROM decrees ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev_row[0] if prev_row else "0" * 64
        decree_hash = self._hash_decree(prev_hash, timestamp, text)

        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO decrees "
                "(prev_hash, timestamp, decree_text, category, scope, classification, "
                " required_signatures, expires_at, decree_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (prev_hash, timestamp, text, category, scope, classification,
                 required_signatures, expires_at, decree_hash)
            )
            seq = self.db.execute(
                "SELECT seq FROM decrees WHERE decree_hash=?", (decree_hash,)
            ).fetchone()[0]
            # v3.18.0 (N-of-M blocking): auto-record the issuer as the
            # implicit first co-signer. This means required_signatures=1
            # decrees are ACTIVE immediately (count=1 >= 1) without any
            # explicit co_sign() call, preserving back-compat with all
            # pre-v3.18.0 callers. Multi-sig decrees (required_signatures=N,
            # N>1) still need N-1 additional explicit co_sign() calls to
            # reach the threshold. signer_id='_issuer' is reserved.
            self.db.execute(
                "INSERT OR IGNORE INTO co_signatures "
                "(decree_seq, signer_id, timestamp) VALUES (?, ?, ?)",
                (seq, "_issuer", timestamp)
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

        # v3.x.0 (Task 13-B / claim #25): auto-publish the external trust
        # anchor AFTER the decree is committed (per ADR-0029 §9 IAEA pattern).
        #
        # The trust anchor is a JSON file containing the last decree's full
        # SHA-256 hash. It is the 'external seal' — out-of-band relative to
        # the SQLite db — so that if someone rebuilds the decree log from
        # scratch (resigning every decree), the anchor won't match and
        # `make verify` will report TAMPER DETECTED.
        #
        # The publish is best-effort: wrapped in try/except so a failure to
        # write the anchor (e.g. read-only filesystem) does NOT fail the
        # decree issue. The decree itself is already law; the anchor is the
        # auditor's tool, not a hard correctness requirement of issue().
        #
        # Gating: auto-publish fires only when (a) this DecreeLog is the
        # production database (~/.polymath-os/decrees.db) OR (b) the env var
        # POLYMATH_OS_TRUST_ANCHOR_PATH is set (used by tests to redirect the
        # anchor to a temp file). Temp-dir dbs used by the rest of the test
        # suite do not pollute the user's real anchor file.
        try:
            _default_db = os.path.expanduser("~/.polymath-os/decrees.db")
            _env_anchor = os.environ.get("POLYMATH_OS_TRUST_ANCHOR_PATH")
            if _env_anchor is not None or self.path == _default_db:
                # Lazy import — avoids a circular dependency at module load:
                # trust_anchor.py is imported here only when a decree is
                # actually issued, not when decree_log.py is first imported.
                from trust_anchor import publish_trust_anchor
                publish_trust_anchor(self)
        except Exception:
            # Anchor publish failed (disk full, permission denied, ...).
            # The decree itself is already committed — do NOT roll it back.
            # The next successful publish will overwrite the stale anchor.
            pass

        return {
            "seq": seq,
            "timestamp": timestamp,
            "decree_text": text,
            "category": category,
            "scope": scope,
            "classification": classification,
            "required_signatures": required_signatures,
            "expires_at": expires_at,
            "decree_hash": decree_hash[:16] + "...",
            "prev_hash": prev_hash[:16] + "...",
        }

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all decrees in order (v3.18.0: includes classification +
        required_signatures; v3.19.0: includes expires_at).

        NOTE: expired decrees are still returned here — this is the append-only
        audit view. Use get_active_laws() for the binding-law view (which
        excludes expired decrees).
        """
        rows = self.db.execute(
            "SELECT seq, timestamp, decree_text, category, scope, classification, "
            "required_signatures, expires_at, decree_hash FROM decrees ORDER BY seq"
        ).fetchall()
        return [
            {"seq": r[0], "timestamp": r[1], "decree_text": r[2],
             "category": r[3], "scope": r[4], "classification": r[5],
             "required_signatures": r[6], "expires_at": r[7],
             "decree_hash": r[8][:16] + "..."}
            for r in rows
        ]

    def get_active_laws(self) -> List[Dict[str, Any]]:
        """Return all 'law' and 'prohibition' decrees that are NOT superseded,
        NOT expired, AND have reached their required_signatures threshold —
        the binding rules.

        Per ADR-0028 (v3.14.0): decrees with category='supersession' and
        scope='supersession:N' mark decree #N as superseded. Such decrees
        are excluded from the active_laws list (the supersession decree
        itself is also excluded — it's a meta-decree, not a law to enforce).

        Per ADR-0029 §6 (v3.18.0 N-of-M blocking): decrees whose
        co-signature count is below their required_signatures threshold
        are PENDING — excluded from active_laws (and therefore NOT enforced
        by check_compliance). The issuer is auto-recorded as signer '_issuer'
        at issue() time, so required_signatures=1 decrees are active as soon
        as they're issued (no explicit co_sign() call needed).

        v3.19.0 (time-limited decrees): decrees with a non-NULL `expires_at`
        column are excluded once the current UTC time exceeds expires_at.
        NULL = no expiry (permanent — backward compatible with all
        pre-v3.19.0 decrees, including the 7 foundational decrees in
        ~/.polymath-os/decrees.db). Comparison is a strict string compare of
        ISO 8601 UTC values — lexicographic order == chronological order for
        the fixed-width '%Y-%m-%dT%H:%M:%SZ' format produced by time.gmtime.
        """
        # Build the set of superseded seqs by scanning for supersession decrees.
        # A supersession decree has category='supersession' and scope='supersession:N'
        # where N is the seq of the target decree.
        superseded_set = self._build_superseded_set()

        # Single LEFT JOIN + GROUP BY query — avoids N+1 query pattern.
        # COUNT(c.signer_id) returns 0 when no co_signatures rows exist
        # (LEFT JOIN produces a NULL row → COUNT of non-NULL = 0).
        rows = self.db.execute(
            "SELECT d.seq, d.timestamp, d.decree_text, d.category, d.scope, "
            "d.classification, d.required_signatures, d.expires_at, "
            "COUNT(c.signer_id) AS sig_count "
            "FROM decrees d "
            "LEFT JOIN co_signatures c ON c.decree_seq = d.seq "
            "WHERE d.category IN ('law', 'prohibition') "
            "GROUP BY d.seq "
            "ORDER BY d.seq"
        ).fetchall()
        # v3.19.0: snapshot 'now' once (in the SAME ISO 8601 UTC format as
        # `expires_at`) so that all rows are compared against the same
        # reference instant. time.strftime + time.gmtime == the same stamp
        # used at issue() — formats match → lexicographic compare is sound.
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        active = []
        for r in rows:
            (seq, ts, text, cat, scope, classification,
             required, expires_at, count) = r
            if seq in superseded_set:
                continue  # v3.14.0: skip superseded decrees
            # v3.18.0 (N-of-M blocking): exclude decrees below their
            # required_signatures threshold. PENDING decrees are not enforced.
            if count < required:
                continue
            # v3.19.0 (time-limited decrees): exclude expired decrees.
            # expires_at is NULL → no expiry (permanent). Otherwise, if the
            # current time is strictly greater than expires_at → exclude.
            # ISO 8601 UTC strings compare lexicographically == chronologically.
            if expires_at is not None and now > expires_at:
                continue
            active.append({
                "seq": seq,
                "timestamp": ts,
                "text": text,
                "category": cat,
                "scope": scope,
                "classification": classification,
                "required_signatures": required,
                "signatures_collected": count,
                "expires_at": expires_at,
            })
        return active

    def _build_superseded_set(self) -> set:
        """Build the set of seqs of decrees that have been superseded.

        Per ADR-0028 — a decree is superseded if there exists a
        supersession decree (category='supersession') with scope matching
        'supersession:<seq>' pointing at it.

        Returns: set of int seqs that are superseded.
        """
        rows = self.db.execute(
            "SELECT scope FROM decrees WHERE category = 'supersession'"
        ).fetchall()
        superseded = set()
        for (scope,) in rows:
            if scope and scope.startswith("supersession:"):
                try:
                    target_seq = int(scope.split(":", 1)[1].strip())
                    superseded.add(target_seq)
                except (ValueError, IndexError):
                    # Malformed scope — skip silently (defensive)
                    pass
        return superseded

    def supersede(self, target_seq: int, reason: str) -> Dict[str, Any]:
        """Issue a new decree that supersedes an existing one.

        Per ADR-0028 (v3.14.0): the original decree remains in the log
        (immutable, hash-chained), but get_active_laws() will skip it.

        Args:
            target_seq: the seq of the decree to supersede
            reason: human-readable reason for supersession

        Returns:
            The new supersession decree record.

        Raises:
            ValueError: if target_seq doesn't exist
        """
        # Validate target_seq exists
        row = self.db.execute(
            "SELECT seq, decree_text, category FROM decrees WHERE seq = ?", (target_seq,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Cannot supersede: no decree with seq={target_seq}")

        target_text, target_category = row[1], row[2]
        if target_category == "supersession":
            # Don't allow superseding a supersession decree (would create
            # confusing chain — the original target would be un-superseded
            # but still in the log as superseded).
            raise ValueError(
                f"Cannot supersede decree #{target_seq}: it's already a supersession decree. "
                f"To undo a supersession, issue a new decree with the original text."
            )

        # Issue a new supersession decree with scope='supersession:<target_seq>'.
        return self.issue(
            text=f"Supersede decree #{target_seq} ({target_text[:80]}{'...' if len(target_text) > 80 else ''}). Reason: {reason}",
            category="supersession",
            scope=f"supersession:{target_seq}",
        )

    def is_decree_active(self, decree_seq: int) -> bool:
        """Return True if the decree has reached its required_signatures threshold.

        Per ADR-0029 §6 (v3.18.0 N-of-M): a decree is ACTIVE iff its
        co-signature count is >= its required_signatures. PENDING decrees
        (count < required_signatures) are NOT enforced by check_compliance()
        and are excluded from get_active_laws().

        The issuer's signature is auto-recorded at issue() time
        (signer_id='_issuer'), so a required_signatures=1 decree is ACTIVE
        immediately upon issue. A required_signatures=N (N>1) decree needs
        N-1 additional explicit co_sign() calls to become ACTIVE.

        Args:
            decree_seq: seq of the decree to check.

        Returns:
            True if the decree exists AND has enough co-signatures.
            False if the decree doesn't exist OR is still PENDING (below
            its required_signatures threshold).
        """
        row = self.db.execute(
            "SELECT required_signatures FROM decrees WHERE seq = ?",
            (decree_seq,)
        ).fetchone()
        if row is None:
            return False  # decree doesn't exist — not active
        required = row[0]
        count = self.db.execute(
            "SELECT COUNT(*) FROM co_signatures WHERE decree_seq = ?",
            (decree_seq,)
        ).fetchone()[0]
        return count >= required

    def co_sign(self, decree_seq: int, signer_id: str) -> Dict[str, Any]:
        """Add a co-signature to a decree (SWIFT multi-sig pattern, per ADR-0029 §6).

        Decrees with required_signatures > 1 are PENDING until enough
        co-signatures are collected. Once the threshold is met
        (count >= required_signatures), the decree becomes ACTIVE and
        get_active_laws() / check_compliance() enforce it.

        The issuer is auto-recorded as signer '_issuer' at issue() time,
        so a decree with required_signatures=N needs N-1 additional explicit
        co_sign() calls to become active.

        Co-signing is idempotent: the (decree_seq, signer_id) pair is the
        PRIMARY KEY of the co_signatures table, so calling co_sign() twice
        with the same signer_id is a no-op (the second insert is silently
        ignored, and the returned signatures_collected count is unchanged).

        Args:
            decree_seq: seq of the decree to co-sign
            signer_id: identifier of the co-signer. '_issuer' is reserved
                       for the implicit issuer signature auto-recorded at
                       issue() time; external callers should use a different
                       id (e.g. 'alice', 'agent-cell65', etc.).

        Returns:
            {decree_seq, signer_id, signatures_collected, required,
             is_active, timestamp} where `required` is the decree's actual
            required_signatures (read from the decrees row) and `is_active`
            is True iff signatures_collected >= required.

        Raises:
            ValueError: if decree_seq doesn't exist.
        """
        # Check decree exists and fetch its required_signatures threshold
        row = self.db.execute(
            'SELECT decree_text, category, scope, required_signatures '
            'FROM decrees WHERE seq = ?', (decree_seq,)
        ).fetchone()
        if row is None:
            raise ValueError(f'Cannot co-sign: no decree with seq={decree_seq}')

        required = row[3]

        # Record the co-signature (idempotent — PRIMARY KEY on
        # (decree_seq, signer_id) means duplicate inserts are ignored).
        ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        try:
            self.db.execute(
                'INSERT INTO co_signatures (decree_seq, signer_id, timestamp) '
                'VALUES (?, ?, ?)',
                (decree_seq, signer_id, ts)
            )
        except Exception:
            pass  # already signed by this signer_id — idempotent

        # Count signatures (real threshold check, replacing v3.17.0's
        # hardcoded required=1 / is_active=True audit-only behavior).
        count = self.db.execute(
            'SELECT COUNT(*) FROM co_signatures WHERE decree_seq = ?',
            (decree_seq,)
        ).fetchone()[0]

        return {
            'decree_seq': decree_seq,
            'signer_id': signer_id,
            'signatures_collected': count,
            'required': required,
            'is_active': count >= required,
            'timestamp': ts,
        }

    def get_co_signatures(self, decree_seq: int) -> List[Dict[str, Any]]:
        """Return all co-signatures for a decree."""
        rows = self.db.execute(
            'SELECT signer_id, timestamp FROM co_signatures WHERE decree_seq = ? ORDER BY timestamp',
            (decree_seq,)
        ).fetchall()
        return [{'signer_id': r[0], 'timestamp': r[1]} for r in rows]

    def get_superseded_decrees(self) -> List[Dict[str, Any]]:
        """Return list of (superseded_seq, supersession_decree_seq, reason) tuples.

        For audit / UI display — shows which decrees have been superseded
        and the supersession decrees that revoked them.
        """
        rows = self.db.execute(
            "SELECT seq, timestamp, decree_text, scope FROM decrees "
            "WHERE category = 'supersession' ORDER BY seq"
        ).fetchall()
        result = []
        for sup_seq, sup_ts, sup_text, sup_scope in rows:
            if sup_scope and sup_scope.startswith("supersession:"):
                try:
                    target_seq = int(sup_scope.split(":", 1)[1].strip())
                    # Extract just the 'reason' portion from sup_text
                    # (the text format is: "Supersede decree #N (...). Reason: <reason>")
                    reason = sup_text
                    if "Reason:" in sup_text:
                        reason = sup_text.split("Reason:", 1)[1].strip()
                    result.append({
                        "superseded_seq": target_seq,
                        "supersession_seq": sup_seq,
                        "timestamp": sup_ts,
                        "reason": reason,
                    })
                except (ValueError, IndexError):
                    pass
        return result

    def _extract_prohibited_terms(self, decree_text: str) -> List[str]:
        """v0.6 phrase-based matcher (deterministic, no LLM).

        Given a prohibition decree of the form "never use X" (or "never
        install X", "never deploy X", "never rely on X", etc.), extract X
        and classify it as one of:

          - LIST     : 3+ words, ALL proper nouns (each starts with uppercase in
                       the original decree text OR is a known browser/tech proper
                       noun). Each word is an INDEPENDENT prohibited term — block
                       on any single match.
          - PHRASE   : 2 words where the second word is a recognized technical
                       acronym (DNS, CDN, ...). Block on the FULL phrase OR on
                       the head noun alone (the first word).
          - SINGLE   : 1 word. Block on that word.
          - DEFAULT  : 2 words without a recognized acronym — treat as PHRASE
                       (block on full phrase + first word).

        Returns: List[str] of prohibited search terms, all lowercase, deduped.
        Returns [] if the decree is not a "never <verb> X" prohibition.

        v0.6 changes (vs v0.5):
        - Uses _PROHIBITION_REGEX instead of naive `text.split("use", 1)`.
          This fixes mis-parsing of "never abuse any services" (which v0.5
          read as prohibited="any services" because "abuse" contains "use"
          as a substring). v0.6 recognizes only the verbs {use, install,
          deploy, run, adopt, rely on} (with optional "the" after "use").
        """
        match = _PROHIBITION_REGEX.search(decree_text)
        if not match:
            return []
        prohibited_raw = match.group(1).strip().rstrip(".,;:!?")
        if not prohibited_raw:
            return []

        # Lowercased version — for the actual search terms.
        raw_lower = prohibited_raw.lower()
        words_lower = raw_lower.split()
        if not words_lower:
            return []

        # Original-case version — for proper-noun detection.
        raw_orig = prohibited_raw
        words_orig = raw_orig.split()

        def _is_proper_noun(orig_word: str, lower_word: str) -> bool:
            if lower_word in _KNOWN_PROPER_NOUNS:
                return True
            return bool(orig_word) and orig_word[0].isupper()

        # SINGLE: 1 word.
        if len(words_lower) == 1:
            return [words_lower[0]]

        # LIST: 3+ words where ALL words look like proper nouns.
        if len(words_lower) >= 3:
            orig_aligned = words_orig if len(words_orig) == len(words_lower) else []
            if orig_aligned and all(
                _is_proper_noun(o, w) for o, w in zip(orig_aligned, words_lower)
            ):
                # Each word is independent — dedupe preserving order.
                return list(dict.fromkeys(words_lower))

        # 2-word PHRASE / DEFAULT case.
        if len(words_lower) == 2:
            full_phrase = " ".join(words_lower)
            head_noun = words_lower[0]
            return list(dict.fromkeys([full_phrase, head_noun]))

        # Fallback for 3+ word decrees that aren't all proper nouns: treat the
        # entire phrase as a single prohibited term.
        return [" ".join(words_lower)]


    def check_compliance(
        self,
        intent_text: str,
        scope: Optional[str] = None,
        clearance: str = "public",
    ) -> Dict[str, Any]:
        """Check if an intent complies with all active decrees.

        This is the enforcement mechanism — the kernel calls this before
        executing any Intent. If a decree prohibits the action → DENIED.

        v3.18.0 (NSA compartmentalization, per ADR-0029 §7):
        - **Clearance filtering.** New optional `clearance` parameter. Each
          decree has a `classification` ∈ {'public', 'internal', 'secret'}
          (hierarchy: 'public' < 'internal' < 'secret'). A decree whose
          classification EXCEEDS the caller's clearance is INVISIBLE — it is
          filtered out before the prohibition matcher runs. So a 'secret'
          decree cannot block an intent from a 'public'-cleared agent: the
          agent literally doesn't know the decree exists (compartmentalization
          invariant). Default `clearance='public'` is the most restrictive.

        v3.19.0 (scope hierarchy — nested scopes):
        - **Hierarchical scope inheritance.** The `scope` parameter now
          follows the _SCOPE_HIERARCHY = {'all': 0, 'singulyar': 1,
          'polymath-os': 2, 'cell65-host': 3, 'outbound': 1}. A decree
          whose scope rank is <= the caller's scope rank applies. So at
          scope='polymath-os' (rank 2), decrees with scope='singulyar'
          (rank 1) AND 'all' (rank 0) ALSO apply — the more specific
          scope inherits the more general (parent) decrees. The reverse
          is NOT true: at scope='singulyar' (rank 1), decrees with
          scope='polymath-os' (rank 2) do NOT apply (parent doesn't see
          child).
        - **Hybrid fallback for unknown scopes.** When EITHER the caller's
          scope OR the decree's scope is NOT in _SCOPE_HIERARCHY, fall back
          to the pre-v3.19.0 'exact match OR all' behavior. This preserves
          backward compatibility with arbitrary custom scopes (e.g.
          'internal-only') — a custom-scoped decree still only applies
          when the caller's scope exactly matches it.
        - Replaces v0.6's flat 2-level filter for known-hierarchy scopes
          (decree.scope == "all" OR decree.scope == scope).

        v3.19.0 (time-limited decrees):
        - **Expiry filtering.** Decrees with a non-NULL `expires_at` column
          are automatically excluded from `get_active_laws()` once the
          current time exceeds expires_at. check_compliance() therefore
          doesn't enforce them after expiry. This happens INSIDE
          get_active_laws() — check_compliance() doesn't filter expiry
          itself, it just consumes the active-law set.

        v0.6 changes (vs v0.5):
        - **Word-boundary regex matching.** Each prohibited term is matched
          using `\\b{term}\\b` regex instead of v0.5's substring check. This
          fixes the v0.5 false positive where "chrome" matched "chromebook"
          (the word "chrome" appears as a substring of "chromebook" but NOT
          as a whole word). v0.6 uses re.escape + word boundaries.
        - **Decree scope filtering.** New optional `scope` parameter. When
          passed (e.g. scope="singulyar"), only decrees whose scope matches
          are checked. v3.19.0 generalizes this into a true hierarchy (see
          above). When scope=None (default), all decrees are checked
          (backward compatible with v0.5 behavior).
        - **Regex-based prohibition parser.** `_extract_prohibited_terms()`
          now uses `_PROHIBITION_REGEX` instead of naive
          `text.split("use", 1)`. This fixes mis-parsing of "never abuse
          any services" (which v0.5 read as prohibited="any services"
          because "abuse" contains "use" as a substring).

        v0.5 (still applies): phrase-based deterministic matching. For each
        prohibition decree of form "never use X", we extract X's prohibited
        search terms via `_extract_prohibited_terms()` and block if ANY
        term appears as a whole word in `intent_text`. This fixes the v0.4
        false positive where decree "never use Google DNS" matched "dns"
        anywhere (e.g. "configure DNS with local unbound"). v0.5+ instead
        blocks on the full phrase "google dns" OR the head noun "google"
        alone.

        Args:
            intent_text: The intent's description (or any text to check).
            scope: Optional scope filter. If provided, only decrees whose
                   scope rank is <= the caller's scope rank (per
                   _SCOPE_HIERARCHY) are checked. So at scope='polymath-os'
                   (rank 2), decrees with scopes 'all' (0), 'singulyar'
                   (1), 'outbound' (1), and 'polymath-os' (2) all apply.
                   scope=None (or scope="all") means no filter — every
                   active decree is checked (backward compatible with v0.5).
            clearance: v3.18.0 — caller's clearance_level per ADR-0029 §7.
                   'public' (default; sees only 'public' decrees),
                   'internal' (sees 'public' + 'internal' decrees),
                   'secret' (sees all decrees). Decrees whose classification
                   exceeds clearance are filtered out before the prohibition
                   matcher runs — they cannot cause a DENIED result.

        Returns: {compliant: bool, violations: [...], laws_checked: int}
        """
        laws = self.get_active_laws()
        # v3.19.0: scope hierarchy — a caller at scope S (rank r_S) inherits
        # all decrees with scope rank <= r_S. So at scope='polymath-os'
        # (rank 2), decrees scoped to 'singulyar' (rank 1) AND 'all' (rank 0)
        # also apply — the more specific scope inherits the more general
        # (parent) decrees.
        #
        # v3.15.0 FIX (preserved): when scope="all" (or None), NO filter
        # is applied — all active decrees are checked. This matches the
        # semantic intent of decree_scope="all" on Agent Cards (per
        # ADR-0023: 'all' = all decrees apply).
        #
        # Hybrid fallback for unknown scopes: when EITHER the caller's
        # scope OR the decree's scope is NOT in _SCOPE_HIERARCHY, fall back
        # to the pre-v3.19.0 'exact match OR all' semantics. This preserves
        # backward compatibility with arbitrary custom scopes (e.g.
        # 'internal-only') that are intentionally NOT part of the standard
        # hierarchy — a custom-scoped decree still only applies when the
        # caller's scope exactly matches it (or the decree is scope='all').
        if scope is not None and scope != "all":
            caller_rank = _SCOPE_HIERARCHY.get(scope)
            if caller_rank is not None:
                # Caller is in the hierarchy → use rank comparison for
                # in-hierarchy decrees; fall back to exact-match for
                # out-of-hierarchy decree scopes.
                def _scope_applies(law: Dict[str, Any]) -> bool:
                    decree_rank = _SCOPE_HIERARCHY.get(law["scope"])
                    if decree_rank is not None:
                        # Both in hierarchy → child inherits from parent
                        # (decree_rank <= caller_rank).
                        return decree_rank <= caller_rank
                    # Decree's scope is custom (not in the hierarchy) →
                    # only apply on exact match with the caller's scope
                    # (or if it's the universal 'all' scope, which is in
                    # the hierarchy so wouldn't reach here).
                    return law["scope"] == scope or law["scope"] == "all"
                laws = [law for law in laws if _scope_applies(law)]
            else:
                # Caller's scope is NOT in the hierarchy → use the
                # pre-v3.19.0 legacy behavior (exact match OR 'all').
                laws = [law for law in laws if law["scope"] == "all" or law["scope"] == scope]

        # v3.18.0: NSA compartmentalization — filter out decrees whose
        # classification EXCEEDS the caller's clearance. The caller must not
        # even know such decrees exist (so they can't cause DENIED results and
        # they don't show up in `laws_checked`). Rank: 'public'=0 < 'internal'=1
        # < 'secret'=2. Unknown classifications are treated as 'public' (rank 0)
        # on both sides — fail-open on the classification axis, fail-closed on
        # the decree axis (default-deny still applies for visible decrees).
        clearance_rank = _CLASSIFICATION_RANK.get(clearance, 0)
        laws = [
            law for law in laws
            if _CLASSIFICATION_RANK.get(law.get("classification", "public"), 0) <= clearance_rank
        ]

        violations = []
        for law in laws:
            terms = self._extract_prohibited_terms(law["text"])
            for term in terms:
                if not term:
                    continue
                # v0.6: word-boundary regex match (was: substring match in v0.5)
                pattern = _compile_term_regex(term)
                if pattern.search(intent_text):
                    violations.append({
                        "decree_seq": law["seq"],
                        "decree_text": law["text"],
                        "violation": f"intent contains prohibited term: {term}",
                        "matched_term": term,
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
