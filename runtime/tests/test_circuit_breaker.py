"""runtime/tests/test_circuit_breaker.py — Tests for the 3-state Circuit Breaker
(Martin Fowler pattern, per ADR-0029 §12 + https://martinfowler.com/bliki/CircuitBreaker.html).

The breaker has 3 states:

  CLOSED    — normal flow. Counts DECREE_BLOCK events in a rolling window.
              When the count reaches `threshold` → OPEN.
  OPEN      — all new Intents short-circuit to WAITING_FOR_HUMAN
              (cascade-failure protection, like a stock-market halt).
              After `window` seconds → HALF-OPEN.
  HALF-OPEN — exactly ONE test Intent is allowed to bypass the breaker.
              If it succeeds (no DECREE_BLOCK) → CLOSED.
              If it fails (DECREE_BLOCK) → OPEN (timer restarted).

Eight tests, all using tempfile.TemporaryDirectory + DecreeLog + Runtime +
MemoryAdapter. The first 5 (test_circuit_breaker_*) cover the closed/open
behaviour inherited from v3.17.0; the last 3 (test_half_open_*) cover the
new half-open recovery probe added in v3.18.0.
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


def _trip_breaker(rt, dl, *, n_violating: int = 4):
    """Helper: trip the breaker by issuing `n_violating` decree-violating
    Intents. Default 4 (one more than the threshold=3 in _setup) so the
    4th Intent trips on entry to _advance()."""
    for i in range(n_violating):
        it = Intent(f"trip{i}", f"send to Google #{i}", "send",
                    {"v": "x"}, {"v": "x"})
        rt.run(it)


class CircuitBreakerTests(unittest.TestCase):
    """Verify the Martin Fowler 3-state circuit breaker (ADR-0029 §12)."""

    # ---------------------------------------------------------------- 1
    def test_circuit_breaker_not_tripped_below_threshold(self):
        """DECREE_BLOCK count below threshold → breaker stays CLOSED."""
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
            self.assertEqual(rt._cb_state, "closed",
                             "circuit breaker must stay CLOSED below threshold")
            self.assertEqual(len(rt._cb_blocks), 2)
            # State snapshot helper should reflect the same state.
            snap = rt.get_circuit_breaker_state()
            self.assertEqual(snap["state"], "closed")
            self.assertEqual(snap["block_count"], 2)
            self.assertEqual(snap["trip_count"], 0)
            self.assertIsNone(snap["tripped_at"])
            # No CIRCUIT_BREAKER_PAUSED event should have been emitted.
            cb_events = [e for e in rt.ledger.events
                         if e["type"] == "CIRCUIT_BREAKER_PAUSED"]
            self.assertEqual(len(cb_events), 0,
                             "no CIRCUIT_BREAKER_PAUSED event below threshold")
            # No CIRCUIT_BREAKER_ALERT either (alert only fires on a trip).
            alert_events = [e for e in rt.ledger.events
                           if e["type"] == "CIRCUIT_BREAKER_ALERT"]
            self.assertEqual(len(alert_events), 0)
            dl.close()

    # ---------------------------------------------------------------- 2
    def test_circuit_breaker_tripped_at_threshold(self):
        """Once `threshold` DECREE_BLOCKs are recorded, the NEXT Intent's
        _check_circuit_breaker() call sees len(blocks) >= threshold and
        trips the breaker (closed → open, emits CIRCUIT_BREAKER_ALERT)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Issue `threshold` (3) decree-violating Intents.
            # Each records a DECREE_BLOCK timestamp. After 3 runs the
            # block list has 3 entries but the breaker is NOT yet
            # OPEN — _check_circuit_breaker() only fires on the NEXT
            # _advance() call.
            for i in range(3):
                it = Intent(f"t{i}", f"send data to Google API #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertEqual(len(rt._cb_blocks), 3)
            self.assertEqual(rt._cb_state, "closed",
                             "breaker is not OPEN yet — the trip check "
                             "only fires on the next _advance() call")
            # The 4th Intent triggers the trip: _check_circuit_breaker()
            # sees 3 >= threshold → _trip_to_open() → state="open" →
            # short-circuits _advance() with CIRCUIT_BREAKER_PAUSED.
            trip_intent = Intent("t3", "send data to Google API #3", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(trip_intent)
            self.assertEqual(rt._cb_state, "open",
                            "circuit breaker MUST trip to OPEN once block "
                            "count reaches threshold")
            self.assertIsNotNone(rt._cb_tripped_at,
                                 "OPEN state must record a trip timestamp")
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
            # CIRCUIT_BREAKER_PAUSED must be recorded for the trip.
            cb_events = [e for e in rt.ledger.events
                         if e["type"] == "CIRCUIT_BREAKER_PAUSED"]
            self.assertGreaterEqual(len(cb_events), 1,
                                     "ledger must record CIRCUIT_BREAKER_PAUSED "
                                     "when the breaker trips")
            # v3.18.0 NEW: a CIRCUIT_BREAKER_ALERT must also be emitted
            # (with threshold, window, block_count, timestamp — per spec).
            alerts = [e for e in rt.ledger.events
                      if e["type"] == "CIRCUIT_BREAKER_ALERT"]
            self.assertEqual(len(alerts), 1,
                             "closed→open trip must emit exactly one ALERT")
            a = alerts[0]["payload"]
            self.assertEqual(a["reason"], "threshold_exceeded")
            self.assertEqual(a["previous_state"], "closed")
            self.assertEqual(a["threshold"], 3)
            self.assertEqual(a["window"], 60)
            self.assertEqual(a["block_count"], 3)
            self.assertIn("timestamp", a)
            # Snapshot helper should reflect the OPEN state.
            snap = rt.get_circuit_breaker_state()
            self.assertEqual(snap["state"], "open")
            self.assertEqual(snap["trip_count"], 1)
            self.assertGreaterEqual(snap["seconds_until_half_open"], 0)
            dl.close()

    # ---------------------------------------------------------------- 3
    def test_circuit_breaker_blocks_all_intents_when_tripped(self):
        """Once OPEN, ALL Intents are blocked — even ones that don't violate
        any decree. The breaker short-circuits the decree + policy gates."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker: 3 decree-violating Intents fill the block
            # list (each records a DECREE_BLOCK), then the 4th trips it.
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open",
                            "breaker must be OPEN after 4 decree-violating intents")
            # Now issue an Intent that does NOT violate any decree.
            # The OPEN breaker must still block it (cascade-failure protection).
            safe_intent = Intent("safe1", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(safe_intent)
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "OPEN breaker must block ALL intents, even safe ones")
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
                             "safe intent must not be decree-blocked when breaker is OPEN")
            dl.close()

    # ---------------------------------------------------------------- 4
    def test_circuit_breaker_resumed_by_human(self):
        """resume_from_circuit_breaker() force-closes the breaker — clears
        state, block history, and trip timer. After resume, safe Intents
        proceed normally again (back to CLOSED state)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker: 3 decree-violating Intents fill the block
            # list, then the 4th trips it.
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open",
                            "breaker must be OPEN before resume test")
            self.assertEqual(len(rt._cb_blocks), 3,
                             "only 3 DECREE_BLOCKs recorded — the 4th intent "
                             "was blocked by the breaker before decree check")
            # Human resumes — clears state + block history + trip timer.
            rt.resume_from_circuit_breaker()
            self.assertEqual(rt._cb_state, "closed",
                             "resume must move state back to CLOSED")
            self.assertEqual(len(rt._cb_blocks), 0,
                             "resume must clear the block history")
            self.assertIsNone(rt._cb_tripped_at,
                              "resume must clear the trip timestamp")
            # Resume must emit a CIRCUIT_BREAKER_RESET ledger event.
            reset_events = [e for e in rt.ledger.events
                            if e["type"] == "CIRCUIT_BREAKER_RESET"]
            self.assertEqual(len(reset_events), 1)
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
        accumulate with old blocks to trip the breaker (state stays CLOSED)."""
        with tempfile.TemporaryDirectory() as tmp:
            # Very short window so the test can observe prune behaviour quickly.
            rt, dl = _setup(tmp, threshold=3, window=1)
            # 2 blocks (below threshold) → breaker CLOSED, not tripped.
            for i in range(2):
                it = Intent(f"w{i}", f"send to Google #{i}", "send",
                           {"v": "x"}, {"v": "x"})
                rt.run(it)
            self.assertEqual(rt._cb_state, "closed")
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
            self.assertEqual(rt._cb_state, "closed",
                             "window expiry must prune old blocks so breaker stays CLOSED")
            self.assertLess(len(rt._cb_blocks), 3,
                            "block list must remain below threshold after window prune")
            dl.close()

    # ================================================================
    # v3.18.0 NEW: half-open recovery probe tests
    # ================================================================
    # All three tests below fast-forward _cb_tripped_at to the past so the
    # next _check_circuit_breaker() call transitions open → half_open.
    # This avoids a multi-second time.sleep() (the window can be 60s by
    # default). White-box: the field is private but accessible.

    # ---------------------------------------------------------------- 6
    def test_half_open_allows_one_test_intent(self):
        """In HALF-OPEN state, exactly ONE test Intent is allowed through.
        While that test is in flight, a second Intent is BLOCKED."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker.
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open")
            # Simulate "a test Intent is currently being processed" by
            # transitioning to half_open manually and setting the
            # in-flight marker (the test Intent's iid is "fake-in-flight").
            # The next Intent that arrives will see test_in_flight=True and
            # be blocked.
            rt._cb_state = "half_open"
            rt._cb_test_in_flight = True
            rt._cb_test_failed = False
            rt._cb_test_intent_iid = "fake-in-flight"
            # Issue a safe Intent — it must be blocked because a test is
            # already in flight.
            safe_intent = Intent("safe-h1", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(safe_intent)
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "half_open with test in flight MUST block new intents")
            # State must remain half_open (the in-flight test wasn't settled
            # because this Intent was not the test).
            self.assertEqual(rt._cb_state, "half_open",
                             "blocked Intent must not change the breaker state")
            # The fake "in-flight" marker must be preserved (this Intent
            # was not the test, so _settle_half_open_test was a no-op).
            self.assertEqual(rt._cb_test_intent_iid, "fake-in-flight")
            self.assertTrue(rt._cb_test_in_flight)
            # Ledger must record CIRCUIT_BREAKER_PAUSED for the blocked Intent.
            paused = [e for e in rt.ledger.events
                      if e["type"] == "CIRCUIT_BREAKER_PAUSED"
                      and e["payload"].get("intent_id") == "safe-h1"]
            self.assertEqual(len(paused), 1)
            self.assertEqual(paused[0]["payload"]["state"], "half_open")
            # No new CIRCUIT_BREAKER_TEST_INTENT event should have been emitted
            # (the test Intent is already in flight).
            tests = [e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_TEST_INTENT"]
            self.assertEqual(len(tests), 0,
                              "no new test Intent bypassed — one is already in flight")
            dl.close()

    # ---------------------------------------------------------------- 7
    def test_half_open_closes_on_success(self):
        """If the test Intent succeeds (no DECREE_BLOCK) → CLOSED (reset)."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker.
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open")
            # Fast-forward the trip timestamp to the past so the next check
            # transitions open → half_open. (Avoids a real time.sleep(60).)
            rt._cb_tripped_at = time.time() - rt._cb_window - 1
            # Issue a SAFE Intent (does NOT mention Google → no DECREE_BLOCK).
            # _check_circuit_breaker() will: see state=open, window expired →
            # transition to half_open → allow this Intent through as the test.
            test_intent = Intent("test-ok", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(test_intent)
            self.assertEqual(st, State.CONFIRMED,
                             "the test Intent must bypass the breaker and "
                             "reach CONFIRMED (decree gate, policy, capability, "
                             "execution, verification all passed)")
            # Success → breaker must have CLOSED (reset).
            self.assertEqual(rt._cb_state, "closed",
                             "successful test Intent must close the breaker")
            self.assertEqual(rt._cb_blocks, [],
                             "successful test Intent must clear block history")
            self.assertIsNone(rt._cb_tripped_at,
                              "CLOSED state must have tripped_at = None")
            # Ledger must record the half_open transition + test Intent bypass.
            half_open_events = [e for e in rt.ledger.events
                                if e["type"] == "CIRCUIT_BREAKER_HALF_OPEN"]
            self.assertEqual(len(half_open_events), 1,
                             "open→half_open transition must be logged")
            test_intent_events = [e for e in rt.ledger.events
                                  if e["type"] == "CIRCUIT_BREAKER_TEST_INTENT"]
            self.assertEqual(len(test_intent_events), 1)
            self.assertEqual(test_intent_events[0]["payload"]["intent_id"], "test-ok")
            # Ledger must record the closed transition (success path).
            closed_events = [e for e in rt.ledger.events
                             if e["type"] == "CIRCUIT_BREAKER_CLOSED"]
            self.assertEqual(len(closed_events), 1,
                             "half_open→closed (test success) must be logged")
            # A subsequent safe Intent must go through normally (closed state,
            # no half_open transition, no test Intent bypass).
            next_intent = Intent("next", "send more local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st2 = rt.run(next_intent)
            self.assertEqual(st2, State.CONFIRMED)
            self.assertEqual(rt._cb_state, "closed")
            # Counts must not have increased.
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_HALF_OPEN"]), 1,
                "no second half_open transition after success")
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_TEST_INTENT"]), 1,
                "no second test Intent after success")
            dl.close()

    # ---------------------------------------------------------------- 8
    def test_half_open_reopens_on_failure(self):
        """If the test Intent triggers a DECREE_BLOCK → OPEN (restart timer).
        The breaker re-trips and the next Intent is blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            rt, dl = _setup(tmp, threshold=3, window=60)
            # Trip the breaker.
            _trip_breaker(rt, dl, n_violating=4)
            self.assertEqual(rt._cb_state, "open")
            first_trip_at = rt._cb_tripped_at
            self.assertIsNotNone(first_trip_at)
            # Fast-forward so the next check transitions open → half_open.
            rt._cb_tripped_at = time.time() - rt._cb_window - 1
            # Issue a DECREE-VIOLATING Intent (mentions Google). _check_circuit_breaker()
            # will transition open → half_open and let it through as the test.
            # The decree gate will record DECREE_BLOCK → _record_decree_block()
            # will see (state=half_open, test_in_flight=True) → _trip_to_open()
            # with reason="half_open_test_failed" → state reverts to OPEN.
            test_intent = Intent("test-fail", "send data to Google (test)", "send",
                                 {"v": "x"}, {"v": "x"})
            st = rt.run(test_intent)
            self.assertEqual(st, State.WAITING_FOR_HUMAN,
                             "the failed test Intent must be blocked by the decree gate")
            # Failure → breaker must have re-tripped to OPEN.
            self.assertEqual(rt._cb_state, "open",
                             "DECREE_BLOCK during half_open test MUST reopen the breaker")
            # The trip timer must have been RESTARTED (new timestamp > old).
            self.assertIsNotNone(rt._cb_tripped_at)
            self.assertGreater(rt._cb_tripped_at, first_trip_at,
                               "reopening the breaker must restart the timer")
            # The trip_count must have incremented (1 closed→open + 1 half_open→open = 2).
            self.assertEqual(rt._cb_trip_count, 2)
            # Ledger must contain TWO CIRCUIT_BREAKER_ALERT events:
            #   1) reason="threshold_exceeded" (closed→open, the initial trip)
            #   2) reason="half_open_test_failed" (half_open→open, the test failure)
            alerts = [e for e in rt.ledger.events
                      if e["type"] == "CIRCUIT_BREAKER_ALERT"]
            self.assertEqual(len(alerts), 2)
            self.assertEqual(alerts[0]["payload"]["reason"], "threshold_exceeded")
            self.assertEqual(alerts[0]["payload"]["previous_state"], "closed")
            self.assertEqual(alerts[1]["payload"]["reason"], "half_open_test_failed")
            self.assertEqual(alerts[1]["payload"]["previous_state"], "half_open")
            # All alerts must include the spec-required fields:
            # threshold, window, block_count, timestamp.
            for a in alerts:
                p = a["payload"]
                self.assertIn("threshold", p)
                self.assertIn("window", p)
                self.assertIn("block_count", p)
                self.assertIn("timestamp", p)
            # The half_open transition + test Intent bypass must both be logged
            # (they happened before the failure path).
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_HALF_OPEN"]), 1)
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_TEST_INTENT"]), 1)
            # No CIRCUIT_BREAKER_CLOSED event (the test failed, not succeeded).
            self.assertEqual(
                len([e for e in rt.ledger.events
                     if e["type"] == "CIRCUIT_BREAKER_CLOSED"]), 0)
            # The next Intent must be BLOCKED (state=open, window not expired).
            next_intent = Intent("next", "send local unbound DNS data", "send",
                                 {"v": "x"}, {"v": "x"})
            st2 = rt.run(next_intent)
            self.assertEqual(st2, State.WAITING_FOR_HUMAN,
                             "after half_open test failure, the breaker is OPEN "
                             "and must block subsequent intents")
            # Snapshot helper should reflect the re-tripped OPEN state.
            snap = rt.get_circuit_breaker_state()
            self.assertEqual(snap["state"], "open")
            self.assertEqual(snap["trip_count"], 2)
            self.assertGreaterEqual(snap["seconds_until_half_open"], 0)
            dl.close()


if __name__ == "__main__":
    unittest.main()
