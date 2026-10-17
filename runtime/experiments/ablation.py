"""Ablation ladder over a fixed fault-scenario matrix (deterministic, stdlib only).

Executors (each adds ONE link; EIR is the real kernel):
  B0  naive          : first capability, trust the adapter's return, blind retry on exception
  B1  +L1 policy     : permission / consent gate
  B2  +L2 contract   : hard-constraint-aware selection + failover on NotExecuted
  B3  +L3 verify     : independent final-state check (absent -> retry, unreadable -> UNKNOWN)
  EIR +L4 readback   : write-ahead ledger, restart => UNKNOWN, recovery by readback, no blind retry

HONESTY NOTE: scenarios are authored by the same party that built EIR, they are synthetic and
deterministic, and the baselines are deliberately simple. This demonstrates what each link
does in an instrumented environment. It is NOT evidence of emergence or of superiority on real
workloads (see docs/EXPERIMENT_PLAN.md for what would be).

Run:  python experiments/ablation.py     (rewrites docs/EXPERIMENT_RESULTS.md, results.csv, prototype/replay_data.js)
"""
from __future__ import annotations
import csv, json, sys, tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from singulyar_runtime import (Capability, Intent, MemoryAdapter, NotExecuted, Policy, PolicyBlocked,
                               PostconditionVerifier, Runtime, SQLiteEffectAdapter, SimulatedCrash,
                               State, ABSENT, FAIL, INCONCLUSIVE, PASS)
from sqlite_ledger import SQLiteEvidenceLedger

KEY = b"experiment-fixed-key-for-determinism"


@dataclass
class Scenario:
    sid: str
    title: str
    remote: Dict[str, Any] = field(default_factory=dict)   # fault knobs on the primary adapter
    intent_kw: Dict[str, Any] = field(default_factory=dict)
    permitted: bool = True
    consent: bool = False
    crash: bool = False            # process dies after the effect, before it is recorded/reported
    should_block: bool = False     # ground truth: NO effect may happen
    local_only: bool = False       # ground truth: data must not reach the remote adapter


SCENARIOS = [
    Scenario("S01", "normal completion"),
    Scenario("S02", "timeout after effect (idempotent receiver)", remote={"timeout_after_effect_n": 1}),
    Scenario("S03", "timeout after effect (receiver does NOT dedup)", remote={"timeout_after_effect_n": 1, "dedup": False}),
    Scenario("S04", "adapter lies permanently (accepted, nothing stored)", remote={"drop_n": 99}),
    Scenario("S05", "adapter lies once, then works", remote={"drop_n": 1}),
    Scenario("S06", "adapter stores a wrong value", remote={"corrupt": True}),
    Scenario("S07", "timeout after effect + state unreadable", remote={"timeout_after_effect_n": 1, "query_available": False}),
    Scenario("S08", "permission missing", permitted=False, should_block=True),
    Scenario("S09", "high risk without consent", intent_kw={"risk": "high"}, should_block=True),
    Scenario("S10", "hard constraint local_only, remote healthy", intent_kw={"constraints": {"local_only": True}}, local_only=True),
    Scenario("S11", "primary refuses before any effect (failover possible)", remote={"raise_not_executed": True}),
    Scenario("S12", "process dies after effect (idempotent receiver)", crash=True),
    Scenario("S13", "process dies after effect (receiver does NOT dedup)", remote={"dedup": False}, crash=True),
    Scenario("S14", "timeout after effect, no dedup, state unreadable", remote={"timeout_after_effect_n": 1, "dedup": False, "query_available": False}),
]

CAPS = [Capability("remote-v1", "send", "remote", "medium", False, True, False, 10),
        Capability("local-v1", "send", "local", "high", True, True, True, 20)]


def make_intent(sc: Scenario) -> Intent:
    return Intent(sc.sid, sc.title, "send", {"v": sc.sid}, {"v": sc.sid}, **sc.intent_kw)


def apply_knobs(ad, knobs):
    for k, v in knobs.items():
        setattr(ad, k, v)


@dataclass
class Outcome:
    reported: str            # SUCCESS | UNKNOWN | FAILED | BLOCKED
    effects_remote: int
    effects_local: int
    correct: int
    trace: List[Dict[str, Any]] = field(default_factory=list)
    restart_at: int = -1


# ------------------------------------------------------------------ baselines
def run_baseline(sc: Scenario, l1: bool, l2: bool, l3: bool) -> Outcome:
    remote, local = MemoryAdapter(adapter_id="remote"), MemoryAdapter(adapter_id="local")
    apply_knobs(remote, sc.remote)
    adapters = {"remote": remote, "local": local}
    policy = Policy({"send"} if sc.permitted else set(), {sc.sid} if sc.consent else set())
    intent, verifier = make_intent(sc), PostconditionVerifier()
    key = intent.intent_id
    reported = None
    if l1:
        try:
            policy.check_intent(intent)
        except PolicyBlocked:
            reported = "BLOCKED"
    cands = sorted(CAPS, key=lambda c: c.priority)
    if l2:
        cands = [c for c in cands if policy.capability_reason(intent, c) is None]
        if not cands and reported is None:
            reported = "BLOCKED"
    else:
        cands = cands[:1]
    state = {"crash_pending": sc.crash}

    def go() -> str:
        for cap in cands:
            ad = adapters[cap.adapter_id]
            ver_budget = 3
            while True:
                done = False
                for _ in range(3):                      # blind retry on exception
                    try:
                        ad.execute(intent, key)
                        if state["crash_pending"]:
                            state["crash_pending"] = False
                            raise SimulatedCrash()
                        done = True
                        break
                    except NotExecuted:
                        if l2:
                            break                       # fail over to next capability
                    except SimulatedCrash:
                        raise
                    except Exception:
                        continue
                if not done:
                    break                               # next capability (or fall out)
                if not l3:
                    return "SUCCESS"
                ev = verifier.verify(intent, ad.read_state(intent, key))
                if ev.verdict == PASS:
                    return "SUCCESS"
                if ev.verdict == INCONCLUSIVE:
                    return "UNKNOWN"
                ver_budget -= 1
                if ev.observed_status == ABSENT and ver_budget > 0:
                    continue
                return "FAILED"
        return "FAILED"

    if reported is None:
        try:
            reported = go()
        except SimulatedCrash:
            reported = go()                             # no durable state: restart from scratch
    return world(sc, reported, remote, local)


def world(sc, reported, remote, local, trace=None, restart_at=-1) -> Outcome:
    key = sc.sid
    want = {"v": sc.sid}
    items = remote._get(key) + local._get(key)
    return Outcome(reported, len(remote._get(key)), len(local._get(key)),
                   sum(1 for x in items if x == want), trace or [], restart_at)


# ------------------------------------------------------------------ EIR (the real kernel)
def brief(e) -> Dict[str, Any]:
    p, t = e["payload"], e["type"]
    d = {"type": t}
    if t == "STATE_TRANSITION":
        d.update({"from": p["from"], "to": p["to"], "detail": p.get("detail", "")})
    elif t in ("VERIFICATION", "RECOVERY_VERIFICATION"):
        d.update({"detail": f'{p["verdict"]} / {p["observed_status"]} - {p["note"]}'})
    elif t == "EXECUTION_STARTED":
        d.update({"detail": f'{p["capability_id"]} attempt {p["attempt"]}'})
    elif t == "RECOVERY_READBACK":
        d.update({"detail": f'readback: {p["observed_status"]}'})
    elif t == "CAPABILITY_REJECTED":
        d.update({"detail": "; ".join(f'{r["capability_id"]}: {r["reason"]}' for r in p["rejected"])})
    elif t == "POLICY_BLOCK":
        d.update({"detail": p["reason"]})
    elif t == "ADAPTER_EXCEPTION":
        d.update({"detail": p["error_type"]})
    elif t == "ADAPTER_NOT_EXECUTED":
        d.update({"detail": p["adapter"] + " guaranteed no effect"})
    elif t == "ADAPTER_RETURN":
        d.update({"detail": p["adapter"] + " returned"})
    return d


def run_eir(sc: Scenario) -> Outcome:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        def build(hook=None, first=True):
            ledger = SQLiteEvidenceLedger(tmp / "ledger.db")
            remote = SQLiteEffectAdapter(tmp / "remote.db", adapter_id="remote")
            local = SQLiteEffectAdapter(tmp / "local.db", adapter_id="local")
            apply_knobs(remote, sc.remote if first else {k: v for k, v in sc.remote.items() if k in ("dedup", "query_available")})
            policy = Policy({"send"} if sc.permitted else set(), {sc.sid} if sc.consent else set())
            return Runtime(CAPS, [remote, local], policy, ledger=ledger, redaction_key=KEY, fault_hook=hook), ledger, remote, local
        def die(point, _i):
            if point == "after_execute":
                raise SimulatedCrash()
        intent = make_intent(sc)
        rt, ledger, remote, local = build(die if sc.crash else None)
        restart_at = -1
        try:
            st = rt.run(intent)
            if st == State.UNKNOWN:                      # one automatic recovery pass (readback), as designed
                st = rt.recover(intent)
        except SimulatedCrash:
            restart_at = len(ledger.events)
            ledger.close(); remote.close(); local.close()
            rt, ledger, remote, local = build(None, first=False)
            st = rt.recover(intent)
        reported = {State.CONFIRMED: "SUCCESS", State.UNKNOWN: "UNKNOWN", State.FAILED: "FAILED",
                    State.WAITING_FOR_HUMAN: "BLOCKED"}[st]
        assert ledger.verify()
        out = world(sc, reported, remote, local, [brief(e) for e in ledger.events], restart_at)
        ledger.close(); remote.close(); local.close()
        return out


EXECUTORS = [("B0 naive", lambda s: run_baseline(s, False, False, False)),
             ("B1 +policy", lambda s: run_baseline(s, True, False, False)),
             ("B2 +contract/failover", lambda s: run_baseline(s, True, True, False)),
             ("B3 +final-state verify", lambda s: run_baseline(s, True, True, True)),
             ("EIR +write-ahead/readback", run_eir)]


def judge(sc: Scenario, o: Outcome) -> Dict[str, bool]:
    total = o.effects_remote + o.effects_local
    exact = total == 1 and o.correct == 1
    flags = {"false_success": o.reported == "SUCCESS" and not exact,
             "duplicate": total > 1,
             "unauthorized": sc.should_block and total > 0,
             "constraint_violation": sc.local_only and o.effects_remote > 0,
             "false_failure": o.reported == "FAILED" and exact}
    flags["completed"] = (o.reported == "SUCCESS" and exact and not flags["constraint_violation"]
                          and not flags["unauthorized"])
    flags["safe"] = not any(flags[k] for k in ("false_success", "duplicate", "unauthorized",
                                              "constraint_violation", "false_failure"))
    return flags


def main():
    results = {}
    for name, fn in EXECUTORS:
        results[name] = [(sc, fn(sc)) for sc in SCENARIOS]
    cols = ["completed", "safe", "false_success", "duplicate", "unauthorized", "constraint_violation", "false_failure"]
    n = len(SCENARIOS)
    lines = ["# Experiment results (generated by experiments/ablation.py - do not edit by hand)", "",
             f"Scenarios: {n}. Deterministic, synthetic, authored by the builder. See the honesty note below.", "",
             "## Aggregate (counts over all scenarios)", "",
             "| executor | completed correctly | safe | false success | duplicate effects | unauthorized effects | constraint violations | false failure |",
             "|---|---|---|---|---|---|---|---|"]
    csv_rows = [["executor", "scenario", "reported", "remote_effects", "local_effects"] + cols]
    for name, rows in results.items():
        agg = {c: 0 for c in cols}
        for sc, o in rows:
            j = judge(sc, o)
            for c in cols:
                agg[c] += int(j[c])
            csv_rows.append([name, sc.sid, o.reported, o.effects_remote, o.effects_local] + [int(j[c]) for c in cols])
        lines.append(f"| {name} | {agg['completed']}/{n} | {agg['safe']}/{n} | {agg['false_success']} | {agg['duplicate']} | "
                     f"{agg['unauthorized']} | {agg['constraint_violation']} | {agg['false_failure']} |")
    lines += ["", "## Per scenario (reported outcome; `!` marks an unsafe result)", "",
              "| scenario | " + " | ".join(name for name, _ in EXECUTORS) + " |",
              "|---|" + "---|" * len(EXECUTORS)]
    for idx, sc in enumerate(SCENARIOS):
        cells = []
        for name, _ in EXECUTORS:
            o = results[name][idx][1]
            j = judge(sc, o)
            cells.append(("! " if not j["safe"] else "") + o.reported + f" (r{o.effects_remote}/l{o.effects_local})")
        lines.append(f"| {sc.sid} {sc.title} | " + " | ".join(cells) + " |")
    lines += ["", "`rX/lY` = number of effects that actually exist on the remote / local adapter (ground truth).", "",
              "## How to read this honestly", "",
              "- Each row adds one link to the previous one, so differences are attributable to that link in THIS matrix.",
              "- EIR completes fewer tasks than B0 in S07 and S14: it reports UNKNOWN instead of guessing. That is the intended trade (unknown is not success), not a defect, but it is a real cost in completion rate.",
              "- The baselines are simple on purpose. A production workflow engine (Temporal, durable functions) would implement several of these links; this table says nothing about EIR vs those systems.",
              "- The scenarios were written by the same author as EIR, so they cannot show generalisation. `docs/EXPERIMENT_PLAN.md` lists what a falsifiable test needs (held-out scenarios, pre-registration, repeated trials, third-party authorship).",
              "- Result therefore supports only a narrow claim: each link measurably removes a specific failure class on the listed scenarios. It does not support 'emergence'."]
    (ROOT / "docs" / "EXPERIMENT_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (ROOT / "experiments" / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(csv_rows)
    replay = [{"id": sc.sid, "title": sc.title, "reported": o.reported, "remote": o.effects_remote,
               "local": o.effects_local, "restart_at": o.restart_at, "trace": o.trace}
              for sc, o in results["EIR +write-ahead/readback"]]
    (ROOT / "prototype" / "replay_data.js").write_text(
        "// GENERATED by experiments/ablation.py from real kernel runs. Do not edit.\nconst REPLAY = "
        + json.dumps(replay, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
