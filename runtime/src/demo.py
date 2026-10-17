"""Demo: failover, crash-window recovery, honest UNKNOWN. Run: python src/demo.py"""
import tempfile
from pathlib import Path
from singulyar_runtime import (Capability, Intent, MemoryAdapter, Policy, Runtime, SimulatedRemoteAdapter)


def main():
    remote, local = SimulatedRemoteAdapter(), MemoryAdapter(adapter_id="local-queue")
    caps = [Capability("remote-v1", "send", "simulated-remote", "medium", False, True, False, 10),
            Capability("local-v1", "send", "local-queue", "medium", True, True, True, 20)]
    rt = Runtime(caps, [remote, local], Policy({"send"}))
    i1 = Intent("m1", "send, remote preferred", "send", {"text": "hi"}, {"text": "hi"})
    remote.raise_not_executed = True
    print("remote down, failover      ->", rt.run(i1).value, "| local effects:", local.effect_count())
    remote.raise_not_executed = False
    i2 = Intent("m2", "send, data must stay local", "send", {"text": "hi"}, {"text": "hi"}, constraints={"local_only": True})
    print("local_only constraint      ->", rt.run(i2).value, "| remote effects:", remote.effect_count())
    i3 = Intent("m3", "timeout after effect", "send", {"text": "x"}, {"text": "x"})
    remote.timeout_after_effect_n = 1
    print("timeout after effect       ->", rt.run(i3).value)
    print("recover by readback        ->", rt.recover(i3).value, "| remote effects for m3:", remote.effect_count("m3"))
    remote.query_available = False
    i4 = Intent("m4", "timeout + unreadable", "send", {"text": "y"}, {"text": "y"})
    remote.timeout_after_effect_n = 1
    print("timeout, state unreadable  ->", rt.run(i4).value, "->", rt.recover(i4).value, "(never guessed)")
    print("ledger valid:", rt.ledger.verify(), "| events:", len(rt.ledger.events))


if __name__ == "__main__":
    main()
