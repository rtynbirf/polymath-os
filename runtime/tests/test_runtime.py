import unittest
from _helpers import *


class KernelTests(unittest.TestCase):
    def test_normal_task_confirms_only_after_verification(self):
        rt, remote, _ = make_runtime()
        self.assertEqual(rt.run(intent()), State.CONFIRMED)
        types = [e["type"] for e in rt.ledger.events]
        self.assertLess(types.index("ADAPTER_RETURN"), types.index("VERIFICATION"))

    def test_high_risk_without_consent_blocked_then_resumes_after_consent(self):
        rt, remote, local = make_runtime()
        i = intent("h", risk="high")
        # high risk exceeds remote ceiling(medium) but local ceiling is high
        self.assertEqual(rt.run(i), State.WAITING_FOR_HUMAN)
        self.assertEqual(remote.effect_count() + local.effect_count(), 0)
        rt.grant_consent("h")
        self.assertEqual(rt.resume(i), State.CONFIRMED)

    def test_missing_permission_blocked(self):
        rt, remote, local = make_runtime(permissions={"save"})
        self.assertEqual(rt.run(intent()), State.WAITING_FOR_HUMAN)
        self.assertEqual(remote.effect_count() + local.effect_count(), 0)

    def test_fault_after_effect_is_unknown_not_success(self):
        rt, remote, _ = make_runtime()
        self.assertEqual(rt.run(intent(), fault_after_effect=True), State.UNKNOWN)
        self.assertEqual(remote.effect_count(), 1)

    def test_recovery_readback_confirms_without_duplicate(self):
        rt, remote, _ = make_runtime()
        i = intent()
        rt.run(i, fault_after_effect=True)
        self.assertEqual(rt.recover(i), State.CONFIRMED)
        self.assertEqual(remote.effect_count(), 1)

    def test_unreadable_state_stays_unknown_and_never_retries(self):
        rt, remote, _ = make_runtime()
        remote.query_available = False
        remote.timeout_after_effect_n = 1
        i = intent()
        self.assertEqual(rt.run(i), State.UNKNOWN)
        self.assertEqual(rt.recover(i), State.UNKNOWN)
        self.assertEqual(remote.calls, 1)           # no blind retry

    def test_adapter_says_ok_but_state_unreadable_is_unknown_not_confirmed(self):
        rt, remote, _ = make_runtime()
        remote.query_available = False               # no exception, adapter happily returns accepted
        self.assertEqual(rt.run(intent()), State.UNKNOWN)
        self.assertEqual(remote.effect_count(), 1)   # the effect exists, but nobody can prove it

    def test_absent_is_distinct_from_unavailable_and_retry_is_safe(self):
        rt, remote, _ = make_runtime()
        remote.drop_n = 1                            # adapter lies once: accepted, nothing stored
        i = intent()
        self.assertEqual(rt.run(i), State.CONFIRMED)  # ABSENT -> same-key retry -> verified
        self.assertEqual(remote.calls, 2)
        self.assertEqual(remote.effect_count(), 1)

    def test_persistent_lying_adapter_ends_failed_not_success(self):
        rt, remote, _ = make_runtime()
        remote.drop_n = 99
        self.assertEqual(rt.run(intent()), State.FAILED)
        self.assertEqual(remote.calls, rt.max_attempts)

    def test_wrong_final_state_fails_verification(self):
        rt, remote, _ = make_runtime()
        remote.corrupt = True
        self.assertEqual(rt.run(intent()), State.FAILED)

    def test_duplicate_effects_are_detected_by_verifier(self):
        rt, _, _ = make_runtime()
        a = MemoryAdapter(dedup=False, adapter_id="simulated-remote")
        rt.adapters["simulated-remote"] = a
        a.execute(intent(), "a"); a.execute(intent(), "a")
        ev = rt.verifier.verify(intent(), a.read_state(intent(), "a"))
        self.assertEqual(ev.verdict, FAIL)
        self.assertIn("count", ev.note)

    def test_non_idempotent_absent_goes_to_human_not_retry(self):
        remote = SimulatedRemoteAdapter(dedup=False)
        caps = [Capability("r", "send", "simulated-remote", "medium", False, False)]
        def boom(point, _intent):
            if point == "before_execute":
                raise InjectedFault("lost before reaching adapter")
        rt = Runtime(caps, [remote], Policy({"send"}), redaction_key=KEY, fault_hook=boom)
        i = intent()
        self.assertEqual(rt.run(i), State.UNKNOWN)
        rt.fault_hook = None
        self.assertEqual(rt.recover(i), State.WAITING_FOR_HUMAN)   # ABSENT, but a retry could duplicate
        self.assertEqual(remote.calls, 0)

    def test_ledger_detects_tampering_and_truncation(self):
        rt, _, _ = make_runtime()
        rt.run(intent())
        cp = rt.ledger.checkpoint()
        self.assertTrue(rt.ledger.verify_against(cp))
        rt.ledger.events[0]["payload"]["operation"] = "tampered"
        self.assertFalse(rt.ledger.verify())
        rt2, _, _ = make_runtime()
        rt2.run(intent("b"))
        cp2 = rt2.ledger.checkpoint()
        rt2.ledger._events.pop()                     # truncate tail, then repair head
        rt2.ledger.head = rt2.ledger._events[-1]["hash"]
        self.assertTrue(rt2.ledger.verify())          # chain alone cannot see truncation...
        self.assertFalse(rt2.ledger.verify_against(cp2))   # ...a checkpoint can

    def test_invalid_transition_rejected(self):
        rt, _, _ = make_runtime()
        i = intent()
        rt.states[i.intent_id] = State.CREATED
        with self.assertRaises(InvalidTransition):
            rt._transition(i, State.CONFIRMED)

    def test_invalid_intent_rejected_by_schema_before_any_state(self):
        rt, _, _ = make_runtime()
        bad = Intent("z", "d", "send", {"value": 1}, {"value": 1}, risk="extreme")
        with self.assertRaises(ContractError):
            rt.run(bad)
        self.assertNotIn("z", rt.states)
        bad2 = Intent("z2", "d", "send", {"value": 1}, {"value": 1}, constraints={"teleport": True})
        with self.assertRaises(ContractError):
            rt.run(bad2)

    def test_duplicate_intent_id_requires_recovery(self):
        rt, _, _ = make_runtime()
        rt.run(intent())
        with self.assertRaises(RuntimeErrorBase):
            rt.run(intent())

    def test_ledger_never_contains_payload_values(self):
        rt, _, _ = make_runtime()
        secret = "S3CRET-PAYLOAD-VALUE"
        rt.run(intent("p", value=secret))
        self.assertNotIn(secret, json.dumps(rt.ledger.events))

    def test_changed_intent_cannot_resume_or_recover_an_accepted_task(self):
        rt, remote, _ = make_runtime()
        i = intent()
        rt.run(i, fault_after_effect=True)
        altered = intent(value="DIFFERENT")
        with self.assertRaises(ContractError):
            rt.recover(altered)

    def test_cancel_only_from_allowed_states(self):
        rt, _, _ = make_runtime()
        i = intent()
        rt.run(i)
        with self.assertRaises(InvalidTransition):
            rt.cancel(i)


class FailoverAndConstraintTests(unittest.TestCase):
    def test_failover_when_primary_guarantees_no_effect(self):
        rt, remote, local = make_runtime()
        remote.raise_not_executed = True
        self.assertEqual(rt.run(intent()), State.CONFIRMED)
        self.assertEqual((remote.effect_count(), local.effect_count()), (0, 1))

    def test_no_failover_after_ambiguous_failure(self):
        rt, remote, local = make_runtime()
        remote.timeout_after_effect_n = 1
        self.assertEqual(rt.run(intent()), State.UNKNOWN)
        self.assertEqual(local.calls, 0)             # second adapter untouched: it could duplicate

    def test_local_only_constraint_is_never_downgraded(self):
        rt, remote, local = make_runtime()
        i = intent(constraints={"local_only": True})
        self.assertEqual(rt.run(i), State.CONFIRMED)
        self.assertEqual((remote.effect_count(), local.effect_count()), (0, 1))
        local.raise_not_executed = True
        j = intent("b", constraints={"local_only": True})
        self.assertEqual(rt.run(j), State.FAILED)    # honest failure, remote still unused
        self.assertEqual(remote.effect_count(), 0)

    def test_no_compatible_capability_waits_for_human(self):
        caps = [Capability("r", "send", "simulated-remote", "medium", False, True)]
        rt = Runtime(caps, [SimulatedRemoteAdapter()], Policy({"send"}), redaction_key=KEY)
        self.assertEqual(rt.run(intent(constraints={"offline": True})), State.WAITING_FOR_HUMAN)

    def test_risk_ceiling_blocks_capability(self):
        rt, remote, local = make_runtime(consented={"r"})
        i = intent("r", risk="high")
        rt.run(i)
        self.assertEqual(remote.effect_count(), 0)   # remote ceiling is medium
        self.assertEqual(local.effect_count(), 1)    # local ceiling is high


class SchemaTests(unittest.TestCase):
    def test_validator_fails_closed_on_unknown_keyword(self):
        from schema_validate import SchemaError, validate
        with self.assertRaises(SchemaError):
            validate({}, {"type": "object", "oneOf": []})

    def test_schemas_match_dataclasses(self):
        from dataclasses import asdict
        from schema_validate import load_schema, validate
        cap = Capability("c", "op", "ad", "low", True, True)
        self.assertEqual(validate(asdict(cap), load_schema("capability.schema.json")), [])
        self.assertEqual(validate(asdict(intent()), load_schema("intent.schema.json")), [])


if __name__ == "__main__":
    unittest.main()
