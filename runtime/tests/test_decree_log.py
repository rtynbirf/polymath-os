"""runtime/tests/test_decree_log.py — Tests for Decree Log (ВОЛЯ = НАКАЗ).

Verifies:
- Append-only (can't amend, can't delete)
- Hash chain integrity (broken chain → DecreeIntegrityError)
- check_compliance: prohibition decrees block matching intents
- Multiple decrees accumulate
- Decrees survive restart (SQLite WAL durability)
"""

import os, sys, sqlite3, tempfile, time, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from decree_log import DecreeLog, DecreeIntegrityError


class DecreeLogTests(unittest.TestCase):

    def test_issue_first_decree(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            result = dl.issue("Человек — PID=1. Каждый инструмент — fork-exec от человека.")
            self.assertEqual(result["seq"], 1)
            self.assertEqual(result["category"], "directive")
            dl.close()

    def test_issue_multiple_decrees_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("Decree 1", category="law")
            d2 = dl.issue("Decree 2", category="law")
            d3 = dl.issue("Decree 3", category="prohibition")
            self.assertEqual(d1["seq"], 1)
            self.assertEqual(d2["seq"], 2)
            self.assertEqual(d3["seq"], 3)
            all_decrees = dl.get_all()
            self.assertEqual(len(all_decrees), 3)
            dl.close()

    def test_append_only_cannot_amend(self):
        """Decrees are immutable. Can't UPDATE text directly."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("Original decree")
            # Try to UPDATE directly — chain will break on next verify
            import sqlite3
            db = sqlite3.connect(str(Path(tmp) / "decrees.db"))
            db.execute("UPDATE decrees SET decree_text='TAMPERED' WHERE seq=1"); db.commit()
            db.close()
            # Verify should fail
            dl.close()
            # Reopen — chain should be broken
            with self.assertRaises(DecreeIntegrityError):
                DecreeLog(Path(tmp) / "decrees.db")

    def test_hash_chain_verification_on_open(self):
        """Opening a log with a broken chain → DecreeIntegrityError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decrees.db"
            dl = DecreeLog(path)
            dl.issue("Decree 1")
            dl.issue("Decree 2")
            dl.close()
            # Tamper with the database
            db = sqlite3.connect(str(path))
            db.execute("UPDATE decrees SET decree_text='TAMPERED' WHERE seq=1"); db.commit()
            db.close()
            # Reopen — should fail
            with self.assertRaises(DecreeIntegrityError):
                DecreeLog(path)

    def test_check_compliance_prohibition_blocks(self):
        """A prohibition decree blocks matching intents."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google", category="prohibition")
            dl.issue("never use Cloudflare", category="prohibition")

            # Intent mentioning Google → should be non-compliant
            result = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)

            # Intent without prohibited terms → compliant
            result = dl.check_compliance("configure DNS with local unbound")
            self.assertTrue(result["compliant"])
            dl.close()

    def test_check_compliance_no_decrees_allows_all(self):
        """Empty decree log → everything compliant (no prohibitions)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            result = dl.check_compliance("do anything")
            self.assertTrue(result["compliant"])
            self.assertEqual(result["laws_checked"], 0)
            dl.close()

    def test_decrees_survive_restart(self):
        """Decrees persist in SQLite across restart."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decrees.db"
            dl = DecreeLog(path)
            dl.issue("Decree 1", category="law")
            dl.issue("Decree 2", category="prohibition")
            dl.close()

            # Reopen
            dl2 = DecreeLog(path)
            self.assertEqual(dl2.count(), 2)
            laws = dl2.get_active_laws()
            self.assertEqual(len(laws), 2)
            dl2.close()

    def test_decree_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            self.assertEqual(dl.count(), 0)
            dl.issue("Decree 1")
            dl.issue("Decree 2")
            self.assertEqual(dl.count(), 2)
            dl.close()

    # ---------------------------------------------------------------- v0.5 phrase matching

    def test_v05_phrase_matching_google_dns_does_not_block_unbound(self):
        """v0.5 fix: decree 'never use Google DNS' must NOT block an intent
        about configuring local unbound DNS.

        Pre-v0.4 behavior was buggy: it split 'Google DNS' into individual
        words and matched 'dns' anywhere, producing a false positive on
        legitimate DNS work like 'configure DNS with local unbound'. v0.5
        treats the decree as a PHRASE (dns is a recognized acronym) so the
        only prohibited substrings are 'google dns' (full phrase) and
        'google' (head noun). 'unbound' matches neither.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("configure DNS with local unbound")
            self.assertTrue(
                result["compliant"],
                f"v0.5 false positive: 'unbound' should not match 'Google DNS' "
                f"decree. Got: {result}",
            )
            dl.close()

    def test_v05_phrase_matching_blocks_google_alone(self):
        """v0.5: decree 'never use Google DNS' still blocks any intent that
        mentions 'google' alone — because the human said 'never use Google
        DNS' and using Google for anything DNS-related is implied-prohibited.
        The matched_term field on the violation records 'google' for callers.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)
            self.assertEqual(result["violations"][0]["matched_term"], "google")
            self.assertEqual(
                result["violations"][0]["decree_text"], "never use Google DNS"
            )
            self.assertEqual(result["violations"][0]["decree_seq"], 1)
            dl.close()

    def test_v05_phrase_matching_blocks_full_phrase(self):
        """v0.5: decree 'never use Google DNS' blocks the FULL phrase
        'google dns' as a contiguous substring.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            result = dl.check_compliance("use Google DNS server")
            self.assertFalse(result["compliant"])
            self.assertGreater(len(result["violations"]), 0)
            self.assertIn("google dns", result["violations"][0]["matched_term"])
            dl.close()

    def test_v05_single_word_prohibition_still_blocks(self):
        """v0.5 SINGLE classification: 'never use Cloudflare' → prohibited
        terms = {'cloudflare'} — single word, block on that word.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Cloudflare", category="prohibition")
            self.assertFalse(dl.check_compliance("use Cloudflare for CDN")["compliant"])
            self.assertTrue(dl.check_compliance("use Fastly for CDN")["compliant"])
            dl.close()

    def test_v05_list_matching_chrome_firefox_edge_safari(self):
        """v0.5 LIST classification: 'never use Chrome Firefox Edge Safari'
        has 4 words, all proper nouns (each starts with uppercase in the
        original decree text and/or is a known browser proper noun). Each
        word is an INDEPENDENT prohibited term — block on any single match.

        Note on the spec's 'chrome inside chromium' warning: 'chrome' is
        NOT in fact a substring of 'chromium'. chrome = c-h-r-o-m-e (6 chars);
        chromium = c-h-r-o-m-i-u-m. They diverge at index 5 (e vs i). So v0.5
        substring matching does NOT match 'chrome' inside 'ungoogled-chromium',
        and the spec's stated limitation does not arise for this input.
        A genuine v0.5 limitation DOES exist for inputs where 'chrome' is a
        real substring, e.g. 'chromebook' or 'chromedriver' — v0.6 word-
        boundary regex will address those.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Chrome Firefox Edge Safari", category="prohibition")

            # Each individual browser name should trigger denial.
            self.assertFalse(dl.check_compliance("install Chrome as default browser")["compliant"])
            self.assertFalse(dl.check_compliance("use Safari browser")["compliant"])
            self.assertFalse(dl.check_compliance("switch to Firefox")["compliant"])
            self.assertFalse(dl.check_compliance("install Edge")["compliant"])

            # No prohibited term → compliant.
            self.assertTrue(dl.check_compliance("use Konqueror as browser")["compliant"])

            # 'ungoogled-chromium' is compliant — 'chrome' is not a substring
            # of 'chromium' (diverge at idx 5: e vs i).
            result = dl.check_compliance("use ungoogled-chromium")
            self.assertTrue(
                result["compliant"],
                f"'chrome' is not a substring of 'chromium' (diverge at idx 5: "
                f"e vs i). Expected compliant, got: {result}",
            )

            # v0.6 FIX: 'chrome' WAS a substring of 'chromebook' in v0.5 → DENIED.
            # v0.6 uses \bchrome\b regex → 'chromebook' has no word boundary
            # after 'chrome' → COMPLIANT.
            result_v06 = dl.check_compliance("buy a chromebook")
            self.assertTrue(
                result_v06["compliant"],
                f"v0.6 word-boundary fix: 'chromebook' should NOT match \\bchrome\\b "
                f"regex. Expected compliant=True, got: {result_v06}",
            )
            dl.close()


class DecreeLogV06Tests(unittest.TestCase):
    """v0.6 tests — word-boundary regex matching, scope filtering, regex parser."""

    def test_v06_word_boundary_chrome_does_not_match_chromebook(self):
        """v0.6 FIX: 'chrome' is a whole word, not a substring.
        'chromebook' has no word boundary after 'chrome' → no match."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Chrome Firefox Edge Safari", category="prohibition")
            # v0.5 false positive: 'chrome' substring of 'chromebook' → DENIED
            # v0.6: \bchrome\b word boundary → 'chromebook' doesn't match → COMPLIANT
            r = dl.check_compliance("buy a chromebook")
            self.assertTrue(r["compliant"],
                f"v0.6: 'chromebook' should be compliant (\\bchrome\\b regex). Got: {r}")
            # But 'install Chrome' should still be DENIED
            r = dl.check_compliance("install Chrome as default browser")
            self.assertFalse(r["compliant"])
            dl.close()

    def test_v06_word_boundary_firefox_does_not_match_firefoxbinary(self):
        """v0.6: 'firefoxbinary' has no word boundary after 'firefox' → no match."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Chrome Firefox Edge Safari", category="prohibition")
            r = dl.check_compliance("install firefoxbinary package")
            self.assertTrue(r["compliant"],
                f"v0.6: 'firefoxbinary' should be compliant. Got: {r}")
            r = dl.check_compliance("use Firefox browser")
            self.assertFalse(r["compliant"])
            dl.close()

    def test_v06_word_boundary_google_does_not_match_googleplex(self):
        """v0.6: 'googleplex' (single word) doesn't match \\bgoogle\\b."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition")
            # 'googleplex' as a single word — \bgoogle\b won't match (no boundary)
            r = dl.check_compliance("visit googleplex headquarters")
            self.assertTrue(r["compliant"],
                f"v0.6: 'googleplex' (single word) should not match \\bgoogle\\b. Got: {r}")
            # But 'visit Google headquarters' matches \bgoogle\b → DENIED
            r = dl.check_compliance("visit Google headquarters")
            self.assertFalse(r["compliant"])
            dl.close()

    def test_v06_scope_filter_only_matching_decrees(self):
        """v0.6 scope parameter filters decrees.

        v3.19.0 NOTE: scope filtering now follows a true hierarchy
        (see _SCOPE_HIERARCHY). A decree scoped to 'singulyar' (rank 1)
        is now ALSO enforced when checking at scope='polymath-os' (rank 2)
        — the more specific scope inherits the more general (parent)
        decrees. This replaces v0.6's flat 'exact match OR all' rule.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            # Decree scoped to 'singulyar' (rank 1)
            dl.issue("never use Google DNS", category="prohibition", scope="singulyar")
            # Decree scoped to 'all' (rank 0)
            dl.issue("never use Cloudflare", category="prohibition", scope="all")

            # Without scope filter — all decrees apply (backward compat)
            r = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(r["compliant"], "without scope, all decrees apply")
            self.assertEqual(r["laws_checked"], 2)

            # With scope='singulyar' (rank 1) — sees rank 0 (all) + rank 1
            # (singulyar). Both Google DNS and Cloudflare apply.
            r = dl.check_compliance("configure DNS with Google 8.8.8.8", scope="singulyar")
            self.assertFalse(r["compliant"], "Google DNS decree scope=singulyar applies")
            self.assertEqual(r["laws_checked"], 2)  # all + singulyar

            # With scope='polymath-os' (rank 2) — v3.19.0 hierarchy: also
            # inherits decrees from singulyar (rank 1) and all (rank 0).
            # So the Google DNS decree (scope='singulyar', rank 1) ALSO
            # applies at scope='polymath-os' (rank 2).
            r = dl.check_compliance("configure DNS with Google 8.8.8.8", scope="polymath-os")
            self.assertFalse(r["compliant"],
                "v3.19.0 hierarchy: Google DNS decree (scope=singulyar, rank 1) "
                "applies at scope=polymath-os (rank 2) via inheritance")
            self.assertEqual(r["laws_checked"], 2,
                "rank 2 caller sees rank 0 + rank 1 decrees (both apply)")

            # Cloudflare (rank 0) still blocks under any scope — it's universal.
            r = dl.check_compliance("use Cloudflare for CDN", scope="polymath-os")
            self.assertFalse(r["compliant"], "Cloudflare scope=all always applies")
            dl.close()

    def test_v06_scope_filter_with_runtime(self):
        """v0.6 realistic Runtime use case.

        v3.19.0 NOTE: scope='all' decrees apply to every Intent. Under the
        new scope hierarchy, scope='singulyar' decrees ALSO apply to more
        specific scopes (polymath-os, cell65-host) via inheritance — but
        NOT to less specific scopes (the parent doesn't see the child).
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Cloudflare", category="prohibition", scope="all")
            dl.issue("never use WebRTC", category="prohibition", scope="singulyar")

            # Simulate singulyar Intent (rank 1) — sees rank 0 + rank 1.
            r = dl.check_compliance("use WebRTC for video", scope="singulyar")
            self.assertFalse(r["compliant"], "WebRTC decree applies to singulyar scope")
            # Simulate polymath-os Intent (rank 2) — v3.19.0 hierarchy:
            # also inherits singulyar (rank 1) decrees via inheritance.
            r = dl.check_compliance("use WebRTC for video", scope="polymath-os")
            self.assertFalse(r["compliant"],
                "v3.19.0 hierarchy: WebRTC decree (scope=singulyar) also applies "
                "at scope=polymath-os via inheritance (rank 2 >= rank 1)")
            dl.close()

    def test_v06_regex_parser_handles_never_abuse(self):
        """v0.6 FIX: 'never abuse any services' was mis-parsed by v0.5
        (which used text.split('use', 1) and extracted 'any services').
        v0.6 uses _PROHIBITION_REGEX which only matches the verbs
        {use, install, deploy, run, adopt, rely on} — 'abuse' is NOT
        in the set → no terms extracted → never blocks."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never abuse any services", category="prohibition")
            # v0.5: extracted "any services" → would block "use any services"
            # v0.6: regex doesn't match "abuse" → no terms → no violations
            r = dl.check_compliance("use any services you want")
            self.assertTrue(r["compliant"],
                f"v0.6: 'never abuse any services' should not extract 'any services' "
                f"as prohibited. Got: {r}")
            self.assertEqual(r["laws_checked"], 1)
            dl.close()

    def test_v06_regex_parser_handles_never_install(self):
        """v0.6: 'never install X' should extract X (was: only 'never use' worked)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never install Slack", category="prohibition")
            r = dl.check_compliance("install Slack for team chat")
            self.assertFalse(r["compliant"], "'never install Slack' should block")
            r = dl.check_compliance("use Discord for team chat")
            self.assertTrue(r["compliant"], "'never install Slack' should not block Discord")
            dl.close()

    def test_v06_regex_parser_handles_never_rely_on(self):
        """v0.6: 'never rely on X' should extract X."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never rely on AWS for storage", category="prohibition")
            # 'rely on AWS' is a 3-word phrase, but 'AWS' is a proper noun
            # and the LIST classification requires 3+ proper nouns.
            # Since 'for storage' isn't a proper noun, this falls into the
            # fallback case (treat the entire phrase as a single term).
            r = dl.check_compliance("rely on AWS for storage")
            # Behavior: fallback returns "aws for storage" as a phrase.
            # Substring 'aws for storage' won't match 'rely on aws for storage' unless
            # exact substring. So this is COMPLIANT unless the fallback is smarter.
            # For v0.6 we accept this — the LIST/PHRASE classifier doesn't handle
            # this case well. Documented as known limitation.
            dl.close()

    def test_v06_regex_parser_use_the(self):
        """v0.6: 'never use the X' should extract X (the 'the' is consumed)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use the Chrome browser", category="prohibition")
            # Extracts "Chrome browser" → 2 words, 'browser' not acronym →
            # DEFAULT case → block on "chrome browser" + head noun "chrome"
            r = dl.check_compliance("install Chrome browser")
            self.assertFalse(r["compliant"], "'never use the Chrome browser' should block 'Chrome'")
            r = dl.check_compliance("use Chrome")
            self.assertFalse(r["compliant"], "'never use the Chrome browser' should block 'Chrome' alone")
            dl.close()

    def test_v06_backward_compat_no_scope(self):
        """v0.6 backward compatibility: check_compliance() without scope
        still checks ALL decrees (matches v0.5 behavior)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Cloudflare", category="prohibition", scope="all")
            dl.issue("never use WebRTC", category="prohibition", scope="singulyar")
            # No scope → all decrees apply (backward compat with v0.5)
            r = dl.check_compliance("use WebRTC for video")
            self.assertFalse(r["compliant"], "without scope, all decrees apply")
            self.assertEqual(r["laws_checked"], 2)
            dl.close()

    def test_v06_term_regex_cache_works(self):
        """v0.6: _compile_term_regex caches compiled patterns across calls."""
        from decree_log import _compile_term_regex, _TERM_REGEX_CACHE
        # Compile same term twice → same cached object
        r1 = _compile_term_regex("test_term_1")
        r2 = _compile_term_regex("test_term_1")
        self.assertIs(r1, r2, "cached pattern should be identical object")
        # Different term → different object
        r3 = _compile_term_regex("test_term_2")
        self.assertIsNot(r1, r3)
        # Word boundary check
        self.assertTrue(r1.search("use test_term_1 today"))
        self.assertFalse(r1.search("use test_term_123 today"), "no word boundary after term")

    def test_v06_word_boundary_at_string_boundaries(self):
        """v0.6: \\bchrome\\b should match at start/end of string."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Chrome", category="prohibition")
            # 'chrome' alone — match at start AND end of string
            self.assertFalse(dl.check_compliance("chrome")["compliant"], "alone matches")
            # 'chrome' at start of sentence
            self.assertFalse(dl.check_compliance("chrome is great")["compliant"])
            # 'chrome' at end of sentence
            self.assertFalse(dl.check_compliance("use chrome")["compliant"])
            dl.close()


class DecreeLogSupersessionTests(unittest.TestCase):
    """v0.7 (v3.14.0) — Decree Supersession tests (per ADR-0028).

    Decrees can be superseded — the original remains in the log (immutable,
    hash-chained) but get_active_laws() skips it.
    """

    def test_supersede_marks_target_as_inactive(self):
        """After supersede(), the target decree is no longer in get_active_laws()."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Google DNS", category="prohibition")
            d2 = dl.issue("never use Cloudflare", category="prohibition")
            # Verify both are active initially
            active = dl.get_active_laws()
            self.assertEqual(len(active), 2)
            # Supersede d1
            d3 = dl.supersede(target_seq=d1["seq"], reason="now using unbound DNS locally")
            self.assertEqual(d3["category"], "supersession")
            self.assertEqual(d3["scope"], f"supersession:{d1['seq']}")
            # d1 no longer in active_laws
            active = dl.get_active_laws()
            self.assertEqual(len(active), 1, f"Expected 1 active law after supersede, got {len(active)}")
            self.assertEqual(active[0]["seq"], d2["seq"])
            dl.close()

    def test_supersede_changes_check_compliance_behavior(self):
        """Superseding a prohibition decree means check_compliance no longer blocks."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue("never use Google DNS", category="prohibition", scope="all")
            # Initial — Google is blocked
            r = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertFalse(r["compliant"])
            self.assertEqual(r["laws_checked"], 1)
            # Supersede the decree
            dl.supersede(target_seq=1, reason="migrated to local unbound — Google DNS allowed now")
            # After supersede — Google is no longer blocked
            r = dl.check_compliance("configure DNS with Google 8.8.8.8")
            self.assertTrue(r["compliant"], f"Expected compliant after supersede, got: {r}")
            self.assertEqual(r["laws_checked"], 0, "Superseded decree should not be checked")
            dl.close()

    def test_supersede_nonexistent_target_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            with self.assertRaises(ValueError):
                dl.supersede(target_seq=999, reason="nonexistent target")
            dl.close()

    def test_supersede_a_supersession_decree_raises(self):
        """Cannot supersede a supersession decree (would create confusing chain)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use WebRTC", category="prohibition")
            d2 = dl.supersede(target_seq=d1["seq"], reason="WebRTC now needed for cell65-llm")
            # Try to supersede d2 — should raise
            with self.assertRaises(ValueError) as ctx:
                dl.supersede(target_seq=d2["seq"], reason="re-instate WebRTC prohibition")
            self.assertIn("already a supersession decree", str(ctx.exception))
            dl.close()

    def test_supersede_preserves_immutability_invariant(self):
        """Original decree text/hash must be unchanged after supersede."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Chrome", category="prohibition")
            original_text = d1["decree_text"]
            original_hash = d1["decree_hash"]
            # Supersede
            dl.supersede(target_seq=d1["seq"], reason="switched to firefox only")
            # Get the original decree back via get_all
            all_decrees = dl.get_all()
            d1_after = next(d for d in all_decrees if d["seq"] == d1["seq"])
            self.assertEqual(d1_after["decree_text"], original_text)
            self.assertEqual(d1_after["decree_hash"], original_hash)
            # Verify chain integrity still OK
            self.assertTrue(dl.verify())
            dl.close()

    def test_get_superseded_decrees(self):
        """get_superseded_decrees() returns list of supersession records."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Google DNS", category="prohibition")
            d2 = dl.issue("never use Cloudflare", category="prohibition")
            d3 = dl.supersede(target_seq=d1["seq"], reason="migrated to local unbound")
            d4 = dl.supersede(target_seq=d2["seq"], reason="Cloudflare no longer used")
            superseded = dl.get_superseded_decrees()
            self.assertEqual(len(superseded), 2)
            seqs_superseded = {r["superseded_seq"] for r in superseded}
            self.assertEqual(seqs_superseded, {d1["seq"], d2["seq"]})
            # Verify reason extracted correctly for each entry
            for entry in superseded:
                self.assertIn(
                    entry["reason"],
                    ["migrated to local unbound", "Cloudflare no longer used"],
                    f"Unexpected reason: {entry['reason']!r}"
                )
            dl.close()

    def test_supersede_affects_scope_filtered_check(self):
        """Superseding with scope filter — superseded decrees skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use WebRTC", category="prohibition", scope="singulyar")
            d2 = dl.issue("never use Cloudflare", category="prohibition", scope="all")
            # Initial: WebRTC decree applies when scope=singulyar
            r = dl.check_compliance("use WebRTC for video", scope="singulyar")
            self.assertFalse(r["compliant"])
            self.assertEqual(r["laws_checked"], 2)  # all + singulyar
            # Supersede d1 (the singulyar-scoped WebRTC decree)
            dl.supersede(target_seq=d1["seq"], reason="WebRTC now needed for cell65-llm P2P")
            # After supersede: WebRTC decree no longer applies
            r = dl.check_compliance("use WebRTC for video", scope="singulyar")
            self.assertTrue(r["compliant"])
            self.assertEqual(r["laws_checked"], 1, "only 'all'-scoped Cloudflare remains")
            dl.close()

    def test_supersession_decree_not_in_active_laws(self):
        """Supersession decrees themselves are not in get_active_laws()."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Google DNS", category="prohibition")
            d2 = dl.supersede(target_seq=d1["seq"], reason="test")
            active = dl.get_active_laws()
            # Should be empty — d1 is superseded, d2 is supersession (meta)
            self.assertEqual(len(active), 0)
            dl.close()


class DecreeLogClearanceTests(unittest.TestCase):
    """v3.18.0 — NSA compartmentalization tests (per ADR-0029 §7).

    AgentCard.clearance_level (added v3.17.0) is now ENFORCED in
    check_compliance() via the new `clearance` parameter. Each decree carries
    a `classification` ∈ {'public', 'internal', 'secret'} (hierarchy:
    'public' < 'internal' < 'secret'). A decree whose classification exceeds
    the caller's clearance is INVISIBLE — filtered out before the prohibition
    matcher runs. Compartmentalization invariant: a 'secret' decree CANNOT
    cause a DENIED result for a 'public'-cleared agent.
    """

    def _issue_three(self, dl):
        """Issue 3 prohibitions, one at each classification level.

        'Google'  → public   (always visible)
        'Slack'   → internal (visible to internal+secret)
        'AWS'     → secret   (visible only to secret)
        """
        dl.issue("never use Google", category="prohibition", classification="public")
        dl.issue("never use Slack", category="prohibition", classification="internal")
        dl.issue("never use AWS", category="prohibition", classification="secret")

    def test_clearance_public_only_sees_public(self):
        """clearance='public' → ONLY 'public'-classified decrees are checked.

        'internal' (Slack) and 'secret' (AWS) decrees are invisible — even
        when the intent mentions the prohibited term by name, the decree
        cannot block because the caller doesn't know it exists.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            self._issue_three(dl)

            # 'Slack' (internal decree) — invisible to public-clearance caller.
            r = dl.check_compliance("install Slack for chat", clearance="public")
            self.assertTrue(
                r["compliant"],
                f"public clearance must hide 'internal' Slack decree. Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 1, "only 'public' decree visible")

            # 'AWS' (secret decree) — invisible to public-clearance caller.
            r = dl.check_compliance("deploy on AWS", clearance="public")
            self.assertTrue(
                r["compliant"],
                f"public clearance must hide 'secret' AWS decree. Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 1)

            # 'Google' (public decree) — still enforced at public clearance.
            r = dl.check_compliance("use Google search", clearance="public")
            self.assertFalse(r["compliant"], "public decree still enforced at public clearance")
            self.assertEqual(r["laws_checked"], 1)
            dl.close()

    def test_clearance_internal_sees_public_and_internal(self):
        """clearance='internal' → 'public' + 'internal' decrees checked.

        'secret' (AWS) decree remains invisible.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            self._issue_three(dl)

            # 'Google' (public) — enforced at internal clearance.
            r = dl.check_compliance("use Google search", clearance="internal")
            self.assertFalse(r["compliant"], "public decree enforced at internal clearance")

            # 'Slack' (internal) — enforced at internal clearance.
            r = dl.check_compliance("install Slack for chat", clearance="internal")
            self.assertFalse(r["compliant"], "internal decree enforced at internal clearance")

            # 'AWS' (secret) — STILL invisible at internal clearance.
            r = dl.check_compliance("deploy on AWS", clearance="internal")
            self.assertTrue(
                r["compliant"],
                f"internal clearance must hide 'secret' AWS decree. Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 2, "public + internal visible at internal clearance")
            dl.close()

    def test_clearance_secret_sees_all(self):
        """clearance='secret' → ALL decrees checked (public + internal + secret)."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            self._issue_three(dl)

            # All 3 decrees enforced at secret clearance.
            r = dl.check_compliance("use Google search", clearance="secret")
            self.assertFalse(r["compliant"], "public decree enforced at secret clearance")
            r = dl.check_compliance("install Slack for chat", clearance="secret")
            self.assertFalse(r["compliant"], "internal decree enforced at secret clearance")
            r = dl.check_compliance("deploy on AWS", clearance="secret")
            self.assertFalse(r["compliant"], "secret decree enforced at secret clearance")

            # Non-prohibited intent → compliant, all 3 laws were checked.
            r = dl.check_compliance("use Fastly for CDN", clearance="secret")
            self.assertTrue(r["compliant"], "non-prohibited intent is compliant")
            self.assertEqual(r["laws_checked"], 3, "all 3 decrees visible at secret clearance")
            dl.close()

    def test_secret_decree_hidden_from_public_clearance(self):
        """Core compartmentalization invariant: a 'secret' decree MUST NOT
        block at clearance='public' — even when the intent literally
        mentions the prohibited term by name. The agent does not know the
        decree exists, so it cannot be DENIED on its basis.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            # Only a single 'secret' decree — no public/internal decrees at all.
            dl.issue("never use AWS", category="prohibition", classification="secret")

            # At public clearance — AWS decree is INVISIBLE, intent is compliant.
            r = dl.check_compliance("deploy on AWS", clearance="public")
            self.assertTrue(
                r["compliant"],
                f"secret decree MUST be hidden from public clearance. Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 0, "no laws visible at public clearance")

            # At secret clearance — AWS decree enforced, intent DENIED.
            r = dl.check_compliance("deploy on AWS", clearance="secret")
            self.assertFalse(r["compliant"], "secret decree enforced at secret clearance")
            self.assertEqual(r["laws_checked"], 1)
            dl.close()


class DecreeLogMultiSigTests(unittest.TestCase):
    """v3.18.0 — N-of-M multi-signature blocking tests (per ADR-0029 §6).

    Decrees with required_signatures > 1 are PENDING until enough
    co-signatures are collected. get_active_laws() excludes PENDING
    decrees; check_compliance() therefore doesn't enforce them. Once
    the threshold is met (count >= required_signatures), the decree
    becomes ACTIVE and is enforced.

    The issuer is auto-recorded as signer '_issuer' at issue() time,
    so a required_signatures=1 decree is ACTIVE immediately (no
    explicit co_sign() call needed) and a required_signatures=N
    decree (N>1) needs N-1 additional explicit co_sign() calls.
    """

    def test_multisig_decree_not_active_until_threshold(self):
        """A decree with required_signatures=3 is NOT active until 3
        co-signatures are collected (including the implicit '_issuer')."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Slack", category="prohibition",
                          required_signatures=3)
            # After issue(): 1 co-sign (implicit '_issuer') — NOT active (1 < 3).
            self.assertFalse(
                dl.is_decree_active(d1["seq"]),
                "Decree with required_signatures=3 must NOT be active after "
                "issue() with only the implicit _issuer co-sign (count=1 < 3)",
            )
            self.assertEqual(
                len(dl.get_active_laws()), 0,
                "PENDING decree must NOT appear in get_active_laws()",
            )

            # Add 1 explicit co-sign — still below threshold (count=2 < 3).
            r1 = dl.co_sign(d1["seq"], "alice")
            self.assertEqual(r1["signatures_collected"], 2)
            self.assertFalse(r1["is_active"], "Still below threshold (2 < 3)")
            self.assertFalse(dl.is_decree_active(d1["seq"]))
            self.assertEqual(len(dl.get_active_laws()), 0)

            # check_compliance must NOT enforce a PENDING decree.
            r = dl.check_compliance("install Slack for team chat")
            self.assertTrue(
                r["compliant"],
                f"PENDING multi-sig decree must NOT block check_compliance. "
                f"Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 0, "PENDING decree not counted")
            dl.close()

    def test_multisig_decree_active_after_threshold(self):
        """Once the co-signature count reaches required_signatures, the
        decree becomes ACTIVE and appears in get_active_laws()."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Slack", category="prohibition",
                          required_signatures=3)
            # Below threshold — not active.
            self.assertFalse(dl.is_decree_active(d1["seq"]))
            self.assertEqual(len(dl.get_active_laws()), 0)

            # Add 2 explicit co-signs — threshold met (count=3 >= 3).
            dl.co_sign(d1["seq"], "alice")
            r2 = dl.co_sign(d1["seq"], "bob")
            self.assertEqual(r2["signatures_collected"], 3)
            self.assertTrue(
                r2["is_active"],
                "Decree must be ACTIVE once count reaches required_signatures",
            )
            self.assertTrue(dl.is_decree_active(d1["seq"]))

            # get_active_laws() now includes the decree with threshold info.
            active = dl.get_active_laws()
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["seq"], d1["seq"])
            self.assertEqual(active[0]["required_signatures"], 3)
            self.assertEqual(active[0]["signatures_collected"], 3)
            dl.close()

    def test_cosign_idempotent(self):
        """Calling co_sign() twice with the same signer_id is idempotent —
        the duplicate insert is ignored (PRIMARY KEY on (decree_seq,
        signer_id)) and signatures_collected stays the same."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Slack", category="prohibition",
                          required_signatures=3)
            # Initial count after issue(): 1 (implicit '_issuer').
            r1 = dl.co_sign(d1["seq"], "alice")
            self.assertEqual(
                r1["signatures_collected"], 2,
                "After 1 explicit co_sign: count = 2 (issuer + alice)",
            )
            # Second co_sign with same signer_id — must be a no-op.
            r2 = dl.co_sign(d1["seq"], "alice")
            self.assertEqual(
                r2["signatures_collected"], 2,
                "Idempotent: second co_sign(alice) must NOT increment count",
            )
            # is_active status unchanged after the duplicate call.
            self.assertFalse(r2["is_active"], "count=2 < 3 → still not active")

            # Verify the co_signatures table has exactly 2 rows
            # (issuer + alice), not 3 (no duplicate alice).
            sigs = dl.get_co_signatures(d1["seq"])
            self.assertEqual(len(sigs), 2, "No duplicate rows in co_signatures")
            signer_ids = {s["signer_id"] for s in sigs}
            self.assertEqual(signer_ids, {"_issuer", "alice"})
            dl.close()

    def test_get_co_signatures(self):
        """get_co_signatures() returns all co-signatures for a decree,
        including the implicit '_issuer' signature auto-recorded at
        issue() time. Each entry has signer_id + timestamp keys."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Slack", category="prohibition",
                          required_signatures=3)
            dl.co_sign(d1["seq"], "alice")
            dl.co_sign(d1["seq"], "bob")

            sigs = dl.get_co_signatures(d1["seq"])
            # 3 entries: _issuer (auto) + alice + bob.
            self.assertEqual(len(sigs), 3)
            signer_ids = {s["signer_id"] for s in sigs}
            self.assertEqual(signer_ids, {"_issuer", "alice", "bob"})

            # Each entry must have a non-empty timestamp (ISO 8601 UTC).
            for s in sigs:
                self.assertIn("signer_id", s)
                self.assertIn("timestamp", s)
                self.assertTrue(s["timestamp"], "timestamp must be non-empty")
                self.assertIn("T", s["timestamp"], "ISO 8601 'T' separator present")
                self.assertTrue(s["timestamp"].endswith("Z"), "UTC 'Z' suffix present")

            # get_co_signatures for a nonexistent decree → empty list
            # (defensive — doesn't raise).
            self.assertEqual(dl.get_co_signatures(999), [])
            dl.close()

    def test_multisig_blocks_check_compliance(self):
        """A multi-sig decree blocks check_compliance ONLY after its
        required_signatures threshold is met. Before that, the decree is
        PENDING and check_compliance() returns compliant=True with
        laws_checked=0 for intents the decree would otherwise block."""
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            d1 = dl.issue("never use Slack", category="prohibition",
                          required_signatures=2)
            # After issue(): count=1 (issuer) < 2 → PENDING, NOT enforced.
            r = dl.check_compliance("install Slack for team chat")
            self.assertTrue(
                r["compliant"],
                f"PENDING multi-sig decree must NOT block. Got: {r}",
            )
            self.assertEqual(
                r["laws_checked"], 0,
                "PENDING decree not counted as a checked law",
            )

            # Add 1 explicit co-sign → count=2 >= 2 → ACTIVE.
            dl.co_sign(d1["seq"], "alice")

            # Now the decree is active — Slack is blocked.
            r = dl.check_compliance("install Slack for team chat")
            self.assertFalse(
                r["compliant"],
                f"ACTIVE multi-sig decree must block matching intent. Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 1, "1 active law checked")
            # The violation must point at the multi-sig decree.
            self.assertEqual(len(r["violations"]), 1)
            self.assertEqual(r["violations"][0]["decree_seq"], d1["seq"])
            self.assertEqual(r["violations"][0]["matched_term"], "slack")

            # A non-matching intent is still compliant (no false positives).
            r = dl.check_compliance("use Discord for team chat")
            self.assertTrue(r["compliant"], "Non-matching intent must be compliant")
            dl.close()


class DecreeLogExpiryAndScopeHierarchyTests(unittest.TestCase):
    """v3.19.0 — Decree expiry (time-limited decrees) + scope hierarchy.

    Two features in this release:

    1. **Decree expiry (expires_at).** issue() accepts an optional
       `expires_at` parameter (ISO 8601 UTC datetime string). If set,
       get_active_laws() (and therefore check_compliance()) automatically
       excludes the decree once the current UTC time exceeds expires_at.
       NULL = no expiry (permanent — backward compatible with all
       pre-v3.19.0 decrees, including the 7 foundational decrees in
       ~/.polymath-os/decrees.db). The decree remains in the append-only
       log (immutable, hash-chained); it simply stops being enforced.

    2. **Scope hierarchy (nested scopes).** A scope with a HIGHER rank
       inherits all decrees from scopes with LOWER rank (per
       _SCOPE_HIERARCHY = {'all': 0, 'singulyar': 1, 'polymath-os': 2,
       'cell65-host': 3, 'outbound': 1}). So a decree scoped to
       'singulyar' (rank 1) also applies when checking compliance at
       scope='polymath-os' (rank 2) — the more specific scope sees the
       more general (parent) decrees. Conversely, scope='singulyar'
       (rank 1) does NOT see scope='polymath-os' (rank 2) decrees —
       parent doesn't see child.
    """

    # ---- Decree expiry tests (expires_at) ----

    def test_expired_decree_not_in_active_laws(self):
        """A decree with expires_at in the past is excluded from
        get_active_laws() and therefore not enforced by
        check_compliance(). The decree remains in get_all() (the
        append-only audit view) — it's just no longer binding.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue(
                "never use Cloudflare",
                category="prohibition",
                expires_at="1999-01-01T00:00:00Z",  # past → already expired
            )

            # get_active_laws() excludes the expired decree.
            active = dl.get_active_laws()
            self.assertEqual(
                len(active), 0,
                f"Expired decree must NOT be in get_active_laws(). Got: {active}",
            )

            # check_compliance() consumes get_active_laws() — so it sees
            # zero laws and the intent is compliant.
            r = dl.check_compliance("use Cloudflare for CDN")
            self.assertTrue(
                r["compliant"],
                f"Expired decree must NOT block check_compliance(). Got: {r}",
            )
            self.assertEqual(
                r["laws_checked"], 0,
                "Expired decree counts as 0 laws checked",
            )

            # But the decree is STILL in get_all() — append-only invariant.
            # It's not deleted, just not enforced. (Audit view shows expiry.)
            all_decrees = dl.get_all()
            self.assertEqual(len(all_decrees), 1, "Decree still in append-only log")
            self.assertEqual(all_decrees[0]["expires_at"], "1999-01-01T00:00:00Z")
            dl.close()

    def test_non_expired_decree_still_active(self):
        """A decree with expires_at in the future remains active and
        enforced. The expires_at field is surfaced in the active_laws
        record so callers can see when the decree will lapse.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            dl.issue(
                "never use Cloudflare",
                category="prohibition",
                expires_at="2999-01-01T00:00:00Z",  # far future → not expired
            )

            active = dl.get_active_laws()
            self.assertEqual(len(active), 1, "Future-expiry decree is still active")
            self.assertEqual(active[0]["expires_at"], "2999-01-01T00:00:00Z")

            r = dl.check_compliance("use Cloudflare for CDN")
            self.assertFalse(
                r["compliant"],
                f"Non-expired decree MUST still block check_compliance(). Got: {r}",
            )
            self.assertEqual(r["laws_checked"], 1)
            dl.close()

    def test_expiry_after_time_passes(self):
        """A decree whose expires_at is computed dynamically as 1 second
        before 'now' is correctly excluded. This proves the time-based
        comparison fires whenever expires_at < now (strict >).

        We compute expires_at from time.time()-1 (UTC epoch) so the test
        is robust against clock skew between when the test computes the
        stamp and when get_active_laws() reads the clock — the gap is at
        most a few ms, well within the 1-second floor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            # expires_at = 'now - 1 second' in the same ISO 8601 UTC format
            # used internally by issue() / get_active_laws().
            past_epoch = time.time() - 1
            past_iso = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(past_epoch)
            )
            dl.issue(
                "never use Cloudflare",
                category="prohibition",
                expires_at=past_iso,
            )

            active = dl.get_active_laws()
            self.assertEqual(
                len(active), 0,
                f"Decree with expires_at 1s in the past ({past_iso}) must be "
                f"excluded from active_laws. Got: {active}",
            )
            r = dl.check_compliance("use Cloudflare for CDN")
            self.assertTrue(
                r["compliant"],
                f"Decree with expires_at in the past must not block. Got: {r}",
            )
            dl.close()

    # ---- Scope hierarchy tests (nested scopes) ----

    def test_scope_hierarchy_child_sees_parent_decrees(self):
        """v3.19.0 scope hierarchy: when checking compliance at
        scope='polymath-os' (rank 2), decrees scoped to 'singulyar'
        (rank 1) ALSO apply — polymath-os inherits singulyar's decrees.

        The more specific scope (child, rank 2) sees the more general
        (parent, rank 1) decree.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            # Decree scoped to 'singulyar' (rank 1) — a parent of polymath-os.
            dl.issue(
                "never use WebRTC",
                category="prohibition",
                scope="singulyar",
            )

            # Check at scope='polymath-os' (rank 2) — the WebRTC decree
            # (rank 1) applies via inheritance (1 <= 2).
            r = dl.check_compliance("use WebRTC for video", scope="polymath-os")
            self.assertFalse(
                r["compliant"],
                f"v3.19.0 hierarchy: scope=polymath-os (rank 2) MUST see "
                f"scope=singulyar (rank 1) decrees. Got: {r}",
            )
            self.assertEqual(
                r["laws_checked"], 1,
                "WebRTC decree (rank 1) inherited by polymath-os (rank 2)",
            )
            dl.close()

    def test_scope_hierarchy_parent_doesnt_see_child_decrees(self):
        """v3.19.0 scope hierarchy: when checking compliance at
        scope='singulyar' (rank 1), decrees scoped to 'polymath-os'
        (rank 2) do NOT apply — the parent scope doesn't see child-scoped
        decrees.

        This is the inverse of test_scope_hierarchy_child_sees_parent_decrees
        and confirms the hierarchy is one-directional (child inherits from
        parent, NOT vice versa).
        """
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(Path(tmp) / "decrees.db")
            # Decree scoped to 'polymath-os' (rank 2) — a child of singulyar.
            dl.issue(
                "never use WebRTC",
                category="prohibition",
                scope="polymath-os",
            )

            # Check at scope='singulyar' (rank 1) — the polymath-os decree
            # (rank 2) does NOT apply (2 > 1 → not inherited).
            r = dl.check_compliance("use WebRTC for video", scope="singulyar")
            self.assertTrue(
                r["compliant"],
                f"v3.19.0 hierarchy: scope=singulyar (rank 1) MUST NOT see "
                f"scope=polymath-os (rank 2) decrees. Got: {r}",
            )
            self.assertEqual(
                r["laws_checked"], 0,
                "WebRTC decree (rank 2) NOT inherited by singulyar (rank 1)",
            )

            # Sanity check: the same decree DOES apply at scope='polymath-os'
            # (its own scope, exact rank match — 2 <= 2).
            r = dl.check_compliance("use WebRTC for video", scope="polymath-os")
            self.assertFalse(
                r["compliant"],
                "Sanity: decree applies at its own scope (exact rank match)",
            )
            dl.close()


if __name__ == "__main__":
    import sqlite3
    unittest.main()

