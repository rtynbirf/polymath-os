"""Production-style decree enforcement demo for the SINGULYAR EIR kernel.

This demo wires `Runtime.set_decree_log(dl)` against the REAL foundational
decree log at `~/.polymath-os/decrees.db` (the 7 decrees issued by the human
via the Decree Portal). It shows decree enforcement VISIBLE at runtime:

  * Intent 1 — "publish note about default-deny" → no prohibition matches
    → passes the decree gate → passes policy → CONFIRMED.
  * Intent 2 — "send data to Google API" → matches decree #3
    "never use Google DNS" (prohibition, term: google) → DECREE_BLOCK
    ledger event → WAITING_FOR_HUMAN (never downgraded to a softer state).

Per ADR-0021 (ВОЛЯ = НАКАЗ) + ADR-0022: the decree log is the human's
supreme law layer — ABOVE policy, ABOVE capability selection, ABOVE the
kernel. The decree gate runs inside `Runtime._advance()` BEFORE
`self.policy.check_intent(intent)`. A non-compliant decree hard-blocks the
intent; it is never silently downgraded.

Run:
    python3 runtime/src/demo_with_decree.py
"""
import os
import sys
from pathlib import Path

# Ensure sibling modules (singulyar_runtime, decree_log, schema_validate)
# are importable when invoked via an absolute path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from decree_log import DecreeLog  # noqa: E402
from singulyar_runtime import (  # noqa: E402
    Capability,
    Intent,
    MemoryAdapter,
    Policy,
    Runtime,
    State,
)


BANNER = (
    "================================================================\n"
    " SINGULYAR EIR — PRODUCTION DECREE ENFORCEMENT DEMO\n"
    " Real DecreeLog @ ~/.polymath-os/decrees.db\n"
    " Decree gate wired into Runtime._advance() (ADR-0021 + ADR-0022)\n"
    "================================================================"
)


def _print_laws_summary(dl: DecreeLog) -> None:
    laws = dl.get_active_laws()
    print(f"\n[DECREE LOG] {len(laws)} active law(s)/prohibition(s) loaded:")
    for law in laws:
        snippet = law["text"][:50]
        print(f"  #{law['seq']:>2} [{law['category']:<11}] {snippet}")
    print(f"[DECREE LOG] chain integrity: {'OK' if dl.verify() else 'BROKEN'} "
          f"(total decrees recorded: {dl.count()})")


def _build_runtime() -> Runtime:
    # One Capability for operation "send" bound to MemoryAdapter
    # (adapter_id == "memory" — matches MemoryAdapter.adapter_id default).
    cap = Capability(
        capability_id="demo-send-cap",
        operation="send",
        adapter_id="memory",
        risk_ceiling="low",
        offline=False,
        idempotent=True,
        local_only=False,
        priority=100,
    )
    adapter = MemoryAdapter()
    policy = Policy(permissions={"send"})
    rt = Runtime(
        capabilities=[cap],
        adapters=[adapter],
        policy=policy,
        redaction_key=b"demo-key",
    )
    return rt


def main() -> int:
    print(BANNER)

    db_path = os.path.expanduser("~/.polymath-os/decrees.db")
    if not os.path.exists(db_path):
        print(f"\n[FATAL] Decree database not found at: {db_path}")
        print("Run `python3 scripts/issue_decrees.py` first to issue the 7")
        print("foundational decrees before re-running this demo.")
        return 2

    dl = DecreeLog(db_path)
    _print_laws_summary(dl)

    # --- Construct the Runtime + attach the real decree log --------------
    rt = _build_runtime()
    rt.set_decree_log(dl)
    print("\n[RUNTIME] Runtime constructed:")
    print(f"  capabilities : 1 (operation=send, adapter=memory, risk=low)")
    print(f"  policy       : permissions={{'send'}}")
    print(f"  redaction_key: b'demo-key'")
    print(f"  decree_log   : attached (supreme law layer, above policy)")

    # --- Intent 1: should be CONFIRMED ----------------------------------
    print("\n" + "-" * 64)
    print("→ Issuing Intent 1: 'publish note about default-deny'")
    print("  (should be CONFIRMED — no prohibition matches)")
    intent1 = Intent(
        intent_id="demo-allowed",
        description="publish note about default-deny",
        operation="send",
        payload={"v": "x"},
        expected={"v": "x"},
    )
    state1 = rt.run(intent1)
    print(f"  resulting state: {state1.value}")
    assert state1 == State.CONFIRMED, (
        f"Expected CONFIRMED for Intent 1, got {state1.value}"
    )

    # --- Intent 2: should be WAITING_FOR_HUMAN --------------------------
    print("\n" + "-" * 64)
    print("→ Issuing Intent 2: 'send data to Google API'")
    print("  (should be WAITING_FOR_HUMAN — decree #3 'never use Google DNS'")
    print("   blocks via 'google' match)")
    intent2 = Intent(
        intent_id="demo-blocked",
        description="send data to Google API",
        operation="send",
        payload={"v": "x"},
        expected={"v": "x"},
    )
    state2 = rt.run(intent2)
    print(f"  resulting state: {state2.value}")
    assert state2 == State.WAITING_FOR_HUMAN, (
        f"Expected WAITING_FOR_HUMAN for Intent 2, got {state2.value}"
    )

    # --- Direct decree compliance query (show the human which decree fired)
    print("\n" + "-" * 64)
    print("[DIRECT QUERY] dl.check_compliance('send data to Google API'):")
    result = dl.check_compliance("send data to Google API")
    print(f"  compliant   : {result['compliant']}")
    print(f"  laws_checked: {result['laws_checked']}")
    print(f"  violations  : {len(result['violations'])} found")
    for v in result["violations"]:
        print(f"    - decree#{v['decree_seq']}: {v['decree_text']!r}")
        print(f"      → {v['violation']}")

    # --- Final summary table -------------------------------------------
    print("\n" + "=" * 64)
    print(" SUMMARY — Decree Enforcement Production Demo")
    print("=" * 64)
    header = f"{'Intent':<10} {'Description':<35} {'Expected':<22} {'Actual':<22}"
    print(header)
    print("-" * len(header))
    print(f"{'demo-…1':<10} {'publish note about default-deny':<35} "
          f"{'CONFIRMED':<22} {state1.value:<22}")
    print(f"{'demo-…2':<10} {'send data to Google API':<35} "
          f"{'WAITING_FOR_HUMAN':<22} {state2.value:<22}")
    print("-" * len(header))
    print(f"Ledger events emitted: {len(rt.ledger.events)}")
    print(f"Ledger chain valid   : {rt.ledger.verify()}")
    decree_block_events = [e for e in rt.ledger.events
                           if e["type"] == "DECREE_BLOCK"]
    print(f"DECREE_BLOCK events  : {len(decree_block_events)} "
          f"(Intent 2 blocked by decree#{result['violations'][0]['decree_seq']})")
    print("=" * 64)
    print("RESULT: Decree enforcement is VISIBLE and DEMONSTRABLE in a")
    print("        production-style run. The kernel obeyed the human's law.")
    print("=" * 64)

    dl.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
