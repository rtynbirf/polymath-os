import os, sqlite3, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path
from _helpers import *
from sqlite_ledger import SQLiteEvidenceLedger, LedgerIntegrityError

SRC = str(Path(__file__).resolve().parents[1] / "src")


def build(tmp, hook=None):
    ledger = SQLiteEvidenceLedger(Path(tmp) / "ledger.db")
    remote = SQLiteEffectAdapter(Path(tmp) / "world.db")
    caps = [Capability("remote-v1", "send", "sqlite-remote", "medium", False, True, False, 10)]
    rt = Runtime(caps, [remote], Policy({"send"}), ledger=ledger, redaction_key=KEY, fault_hook=hook)
    return rt, ledger, remote


class LedgerTests(unittest.TestCase):
    def test_events_survive_reopen_and_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            l = SQLiteEvidenceLedger(Path(tmp) / "e.db")
            l.append("A", {"n": 1}); l.append("B", {"n": 2})
            head = l.head; l.close()
            l2 = SQLiteEvidenceLedger(Path(tmp) / "e.db")
            self.assertEqual((len(l2.events), l2.head, l2.verify()), (2, head, True))

    def test_tampered_payload_is_rejected_on_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "e.db"
            l = SQLiteEvidenceLedger(p); l.append("A", {"v": "orig"}); l.close()
            db = sqlite3.connect(p); db.execute("UPDATE evidence_events SET payload_json='{\"v\":\"x\"}'"); db.commit(); db.close()
            with self.assertRaises(LedgerIntegrityError):
                SQLiteEvidenceLedger(p)

    def test_tail_truncation_needs_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "e.db"
            l = SQLiteEvidenceLedger(p)
            for n in range(3): l.append("A", {"n": n})
            cp = l.checkpoint(); l.close()
            db = sqlite3.connect(p); db.execute("DELETE FROM evidence_events WHERE seq=2"); db.commit(); db.close()
            l2 = SQLiteEvidenceLedger(p)
            self.assertTrue(l2.verify())                     # chain still self-consistent
            self.assertFalse(l2.verify_against(cp))          # checkpoint exposes the truncation

    def test_two_handles_do_not_fork_the_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "e.db"
            a, b = SQLiteEvidenceLedger(p), SQLiteEvidenceLedger(p)
            for n in range(4):
                (a if n % 2 else b).append("A", {"n": n})
            self.assertTrue(a.verify() and b.verify())
            self.assertEqual([e["seq"] for e in a.events], [0, 1, 2, 3])

    def test_export_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            l = SQLiteEvidenceLedger(Path(tmp) / "e.db"); l.append("A", {"n": 1})
            out = l.export_jsonl(Path(tmp) / "e.jsonl")
            self.assertEqual(len(out.read_text(encoding="utf-8").splitlines()), 1)


class RestartTests(unittest.TestCase):
    def test_in_process_crash_then_rehydrate_and_recover_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            def die(point, _i):
                if point == "after_execute":
                    raise SimulatedCrash()
            rt, ledger, remote = build(tmp, die)
            i = intent()
            with self.assertRaises(SimulatedCrash):
                rt.run(i)
            ledger.close(); remote.close()
            rt2, ledger2, remote2 = build(tmp)               # "new process"
            self.assertEqual(rt2.states["a"], State.UNKNOWN)  # EXECUTING became UNKNOWN, not guessed
            self.assertEqual(rt2.recover(i), State.CONFIRMED)
            self.assertEqual(remote2.effect_count("a"), 1)
            self.assertTrue(ledger2.verify())

    def test_real_process_death_between_effect_and_ledger_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = textwrap.dedent(f"""
                import os, sys
                sys.path.insert(0, {SRC!r}); sys.path.insert(0, {str(Path(__file__).parent)!r})
                from test_durability import build, intent
                def die(point, _i):
                    if point == "after_execute":
                        os._exit(137)          # hard kill: no finally, no flush, no cleanup
                rt, _, _ = build({tmp!r}, die)
                rt.run(intent())
            """)
            r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True)
            self.assertEqual(r.returncode, 137, r.stderr)
            rt, ledger, remote = build(tmp)
            self.assertEqual(remote.effect_count("a"), 1)    # the world has the effect...
            self.assertNotIn("ADAPTER_RETURN", [e["type"] for e in ledger.events])  # ...the ledger never saw it
            self.assertEqual(rt.states["a"], State.UNKNOWN)
            self.assertEqual(rt.recover(intent()), State.CONFIRMED)
            self.assertEqual(remote.effect_count("a"), 1)    # still exactly one

    def test_crash_before_effect_recovers_by_safe_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            def die(point, _i):
                if point == "before_execute":
                    raise SimulatedCrash()
            rt, l, r = build(tmp, die)
            with self.assertRaises(SimulatedCrash):
                rt.run(intent())
            l.close(); r.close()
            rt2, _, remote2 = build(tmp)
            self.assertEqual(remote2.effect_count("a"), 0)
            self.assertEqual(rt2.recover(intent()), State.CONFIRMED)   # ABSENT + idempotent -> retry
            self.assertEqual(remote2.effect_count("a"), 1)

    def test_consent_is_not_restored_after_restart_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = SQLiteEvidenceLedger(Path(tmp) / "l.db")
            caps = [Capability("c", "send", "memory", "high", True, True, True)]
            rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), ledger=ledger, redaction_key=KEY)
            i = intent(risk="high")
            self.assertEqual(rt.run(i), State.WAITING_FOR_HUMAN)
            rt.grant_consent("a"); ledger.close()
            rt2 = Runtime(caps, [MemoryAdapter()], Policy({"send"}),
                          ledger=SQLiteEvidenceLedger(Path(tmp) / "l.db"), redaction_key=KEY)
            self.assertEqual(rt2.resume(i), State.WAITING_FOR_HUMAN)   # must be granted again

    def test_wrong_redaction_key_cannot_bind_to_existing_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            rt, l, r = build(tmp)
            rt.run(intent(), fault_after_effect=True); l.close(); r.close()
            ledger = SQLiteEvidenceLedger(Path(tmp) / "ledger.db")
            caps = [Capability("remote-v1", "send", "sqlite-remote", "medium", False, True)]
            rt2 = Runtime(caps, [SQLiteEffectAdapter(Path(tmp) / "world.db")], Policy({"send"}),
                          ledger=ledger, redaction_key=b"other-key")
            with self.assertRaises(ContractError):
                rt2.recover(intent())


if __name__ == "__main__":
    unittest.main()
