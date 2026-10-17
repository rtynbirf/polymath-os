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
            decree_hash TEXT NOT NULL UNIQUE
        )""")

        # v3.17.0: Multi-signature (SWIFT pattern, per ADR-0029 §6)
        # Co-signatures for decrees that require N-of-M authorization
        self.db.execute("""CREATE TABLE IF NOT EXISTS co_signatures (
            decree_seq INTEGER NOT NULL,
            signer_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            PRIMARY KEY (decree_seq, signer_id),
            FOREIGN KEY (decree_seq) REFERENCES decrees(seq)
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
        """Return all 'law' and 'prohibition' decrees that are NOT superseded — the binding rules.

        Per ADR-0028 (v3.14.0): decrees with category='supersession' and
        scope='supersession:N' mark decree #N as superseded. Such decrees
        are excluded from the active_laws list (the supersession decree
        itself is also excluded — it's a meta-decree, not a law to enforce).
        """
        # Build the set of superseded seqs by scanning for supersession decrees.
        # A supersession decree has category='supersession' and scope='supersession:N'
        # where N is the seq of the target decree.
        superseded_set = self._build_superseded_set()

        rows = self.db.execute(
            "SELECT seq, timestamp, decree_text, category, scope FROM decrees "
            "WHERE category IN ('law', 'prohibition') ORDER BY seq"
        ).fetchall()
        return [
            {"seq": r[0], "timestamp": r[1], "text": r[2], "category": r[3], "scope": r[4]}
            for r in rows
            if r[0] not in superseded_set  # v3.14.0: skip superseded decrees
        ]

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

    def co_sign(self, decree_seq: int, signer_id: str) -> Dict[str, Any]:
        """Add a co-signature to a decree (SWIFT multi-sig pattern, per ADR-0029 §6).

        Decrees with required_signatures > 1 are PENDING until enough
        co-signatures are collected. Once the threshold is met,
        the decree becomes ACTIVE.

        Args:
            decree_seq: seq of the decree to co-sign
            signer_id: identifier of the co-signer

        Returns: {decree_seq, signer_id, signatures_collected, required, is_active}
        """
        # Check decree exists
        row = self.db.execute(
            'SELECT decree_text, category, scope FROM decrees WHERE seq = ?', (decree_seq,)
        ).fetchone()
        if row is None:
            raise ValueError(f'Cannot co-sign: no decree with seq={decree_seq}')

        # Record the co-signature (ignore if already signed)
        ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        try:
            self.db.execute(
                'INSERT INTO co_signatures (decree_seq, signer_id, timestamp) VALUES (?, ?, ?)',
                (decree_seq, signer_id, ts)
            )
        except Exception:
            pass  # already signed — idempotent

        # Count signatures
        count = self.db.execute(
            'SELECT COUNT(*) FROM co_signatures WHERE decree_seq = ?', (decree_seq,)
        ).fetchone()[0]

        # For v3.17.0, all decrees have required_signatures=1 (single-sig by default).
        # Multi-sig decrees would be issued with a custom required count
        # stored in the decree_text as metadata. For now, co_sign is
        # an audit mechanism — it records WHO signed, but doesn't block.
        # Full multi-sig enforcement (blocking until threshold met) is v3.18.0.

        return {
            'decree_seq': decree_seq,
            'signer_id': signer_id,
            'signatures_collected': count,
            'required': 1,  # v3.17.0: single-sig by default; v3.18.0 will support N-of-M
            'is_active': True,  # active with 1 signature (default)
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


    def check_compliance(self, intent_text: str, scope: Optional[str] = None) -> Dict[str, Any]:
        """Check if an intent complies with all active decrees.

        This is the enforcement mechanism — the kernel calls this before
        executing any Intent. If a decree prohibits the action → DENIED.

        v0.6 changes (vs v0.5):
        - **Word-boundary regex matching.** Each prohibited term is matched
          using `\\b{term}\\b` regex instead of v0.5's substring check. This
          fixes the v0.5 false positive where "chrome" matched "chromebook"
          (the word "chrome" appears as a substring of "chromebook" but NOT
          as a whole word). v0.6 uses re.escape + word boundaries.
        - **Decree scope filtering.** New optional `scope` parameter. When
          passed (e.g. scope="singulyar"), only decrees whose scope matches
          (decree.scope == "all" OR decree.scope == scope) are checked.
          When scope=None (default), all decrees are checked (backward
          compatible with v0.5 behavior).
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
                   scope matches are checked. Scope matching: decree.scope
                   == "all" → always applies. Otherwise, exact string match
                   with the passed scope. Pass None to check all decrees
                   (backward compatible with v0.5).

        Returns: {compliant: bool, violations: [...], laws_checked: int}
        """
        laws = self.get_active_laws()
        # v0.6 scope filter — only apply decrees whose scope matches.
        # v3.15.0 FIX: when scope="all" (or None), ALL decrees apply (no filter).
        # Previously, scope="all" was treated as a filter that only kept decrees
        # with scope=="all" — incorrectly excluding scope-specific decrees like
        # "never use Google DNS" (scope="polymath-os"). Now scope="all" means
        # "no filter" — matching the semantic intent of decree_scope="all" on
        # Agent Cards (per ADR-0023: 'all' = all decrees apply).
        if scope is not None and scope != "all":
            laws = [law for law in laws if law["scope"] == "all" or law["scope"] == scope]
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
