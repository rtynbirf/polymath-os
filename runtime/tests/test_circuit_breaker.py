"""runtime/tests/test_circuit_breaker.py — Tests for the Circuit Breaker
(Stock Exchange pattern, per ADR-0029 §12).

When DECREE_BLOCK events exceed a threshold within a rolling time window,
the Runtime automatically pauses — all new Intents → WAITING_FOR_HUMAN.
This prevents cascade failures (analogous to stock-market circuit breakers
that halt trading when the market drops too fast).

Five tests, all using tempfile.TemporaryDirectory + DecreeLog + Runtime +
MemoryAdapter. Each test issues a 'never use Google' prohibition decree,
then issues many Intents mentioning 'Google' to trigger DECREE_BLOCK events.
"""
import sys, tempfile, time, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from singulyar_runtime import Runtime, Policy, Capability, Intent, State, MemoryAdapter
from decree_log import DecreeLog


def _setup(tmp: str, threshold: int = 3, window: int = 60):
    """Build a Runtime with a 'never use Google' prohibition decree attached,
    and configure the circuit breaker with the given threshold / window."""
    dl = DecreeLog(str(Path(tmp) / "decrees.db"))
    dl.issue("never use Google", category="prohibition")
    caps = [Capability("c1", "send", "memory", "low", True, True)]
    rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), redaction_key=b"k")
    rt.set_decree_log(dl)
    rt.set_circuit_breaker(threshold=threshold, window=window)
    return rt, dl


class CircuitBreakerTests(unittest.TestCase):
    """Verify the Stock Exchange circuit breaker pattern (ADR-0029 §12)."""

    # ---------------------------------------------------------------- 1
    def test_circuit_breaker_not_tripped_below_threshold(self):
        """DECREE_BLOCK count below threshold → breaker stays armed, not tripped."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Issue 2 Intents that violate the 'never use Google' decree.
            # Each call to _advance() detects the violation, records a
            # DECREE_BLOCK event, and returns WAITING_FOR_HUMAN.
            for i in range(2):
                it = Intent(f"b{i}", f"send data to Google API #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                st = rt.run(it)
                self.assertEqual(st, State.WAITING_FOR_HUMAN,
                                 f"intent {i} should be blocked by the prohibition decree")
            # 2 blocks < threshold 3 → breaker should NOT have tripped.
            self.assertFalse(rt._cb_paused,
                             "circuit breaker must NOT trip below threshold")
            self.assertEqual(len(rt._cb_blocks), 2)
            # No CIRCUIT_BREAKER_PAUSED event should have been emitted.
            cb_events = [e for e in rt.ledger.events
                         if e["type"] == "CIRCUIT_BREAKER_PAUSED"]
            self.assertEqual(len(cb_events), 0,
                             "no CIRCUIT_BREAKER_PAUSED event below threshold")
            dl.close()

    # ---------------------------------------------------------------- 2
    def test_circuit_breaker_tripped_at_threshold(self):
        """Once `threshold` DECREE_BLOCKs are recorded, the NEXT Intent's
        _check_circuit_breaker() call sees len(blocks) >= threshold and
        trips the breaker (paused=True)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Issue `threshold` (3) decree-violating Intents.
            # Each records a DECREE_BLOCK timestamp. After 3 runs the
            # block list has 3 entries but the breaker is NOT yet
            # paused — _check_circuit_breaker() only fires on the NEXT
            # _advance() call.
            for i in range(3):
                it = Intent(f"t{i}", f"send data to Google API #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertEqual(len(rt._cb_blocks), 3)
            self.assertFalse(rt._cb_paused,
                             "breaker is not paused yet — the trip check "
                             "only fires on the next _advance() call")
            # The 4th Intent triggers the trip: _check_circuit_breaker()
            # sees 3 >= threshold → sets _cb_paused=True → short-circuits
            # _advance() with CIRCUIT_BREAKER_PAUSED (no DECREE_BLOCK recorded).
            trip_intent = Intent("t3", "send data to Google API #3", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(trip_intent)
            self.assertTrue(rt._cb_paused,
                            "circuit breaker MUST trip once block count "
                            "reaches threshold")
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "tripping intent must be blocked by the breaker")
            # The tripping Intent is blocked by the breaker, NOT by decree —
            # so no new DECREE_BLOCK was recorded for it.
            trip_blocks = [e for e in rt.ledger.events
                           if e["type"] == "DECREE_BLOCK"
                           and e["payload"].get("intent_id") == "t3"]
            self.assertEqual(len(trip_blocks), 0,
                             "tripping intent must be blocked by the breaker, "
                             "not by a fresh DECREE_BLOCK event")
            cb_events = [e for e in rt.ledger.events
                         if e["type"] == "CIRCUIT_BREAKER_PAUSED"]
            self.assertGreaterEqual(len(cb_events), 1,
                                     "ledger must record CIRCUIT_BREAKER_PAUSED "
                                     "when the breaker trips")
            dl.close()

    # ---------------------------------------------------------------- 3
    def test_circuit_breaker_blocks_all_intents_when_tripped(self):
        """Once tripped, ALL Intents are blocked — even ones that don't violate
        any decree. The breaker short-circuits the decree + policy gates."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker: 3 decree-violating Intents fill the block
            # list (each records a DECREE_BLOCK), then the 4th trips it.
            for i in range(4):
                it = Intent(f"p{i}", f"send to Google #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertTrue(rt._cb_paused,
                            "breaker must be tripped after 4 decree-violating intents")
            # Now issue an Intent that does NOT violate any decree.
            # The tripped breaker must still block it (cascade-failure protection).
            safe_intent = Intent("safe1", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(safe_intent)
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "tripped breaker must block ALL intents, even safe ones")
            # Ledger must record a CIRCUIT_BREAKER_PAUSED event for the safe intent.
            safe_cb = [e for e in rt.ledger.events
                       if e["type"] == "CIRCUIT_BREAKER_PAUSED"
                       and e["payload"].get("intent_id") == "safe1"]
            self.assertGreaterEqual(len(safe_cb), 1,
                                     "ledger must record CIRCUIT_BREAKER_PAUSED "
                                     "for the blocked safe intent")
            # The safe intent must NOT have been recorded as a DECREE_BLOCK
            # (the breaker short-circuits before the decree gate runs).
            safe_blocks = [e for e in rt.ledger.events
                           if e["type"] == "DECREE_BLOCK"
                           and e["payload"].get("intent_id") == "safe1"]
            self.assertEqual(len(safe_blocks), 0,
                             "safe intent must not be decree-blocked when breaker is tripped")
            dl.close()

    # ---------------------------------------------------------------- 4
    def test_circuit_breaker_resumed_by_human(self):
        """resume_from_circuit_breaker() clears the paused flag and block
        history — like resuming trading after a market halt. After resume,
        safe Intents proceed normally again."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker: 3 decree-violating Intents fill the block
            # list, then the 4th trips it.
            for i in range(4):
                it = Intent(f"r{i}", f"send to Google #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertTrue(rt._cb_paused,
                            "breaker must be tripped before resume test")
            self.assertEqual(len(rt._cb_blocks), 3,
                             "only 3 DECREE_BLOCKs recorded — the 4th intent "
                             "was blocked by the breaker before decree check")
            # Human resumes — clears pause + block history.
            rt.resume_from_circuit_breaker()
            self.assertFalse(rt._cb_paused,
                             "resume must clear the paused flag")
            self.assertEqual(len(rt._cb_blocks), 0,
                             "resume must clear the block history")
            # Now a safe Intent should proceed to CONFIRMED.
            safe_intent = Intent("safe2", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(safe_intent)
            self.assertEqual(st, State.CONFIRMED,
                             "after resume, safe intent should proceed to CONFIRMED")
            dl.close()

    # ---------------------------------------------------------------- 5
    def test_circuit_breaker_window_expiry(self):
        """Old DECREE_BLOCK entries are pruned once they fall outside the
        rolling window — so a fresh block after the window expires does not
        accumulate with old blocks to trip the breaker."""
        with tempfile.TemporaryDirectory() as tmp:
            # Very short window so the test can observe prune behaviour quickly.
            rt, dl = _setup(tmp, threshold=3, window=1)
            # 2 blocks (below threshold) → breaker armed, not tripped.
            for i in range(2):
                it = Intent(f"w{i}", f"send to Google #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertFalse(rt._cb_paused)
            self.assertEqual(len(rt._cb_blocks), 2)
            # Wait for the rolling window to expire.
            time.sleep(1.5)
            # Issue one more decree-violating Intent. On entry to _advance(),
            # _check_circuit_breaker() prunes the 2 stale timestamps (now
            # outside window=1s), leaving an empty list. The new block is
            # then recorded — total live blocks = 1, below threshold.
            it = Intent("w2", "send to Google #2", "send", {"v": "x"}, {"v": "x"})
            st = rt.run(it)
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "the decree violation itself still blocks the intent")
            self.assertFalse(rt._cb_paused,
                             "window expiry must prune old blocks so breaker does not trip")
            self.assertLess(len(rt._cb_blocks), 3,
                            "block list must remain below threshold after window prune")
            dl.close()


if __name__ == "__main__":
    unittest.main()
