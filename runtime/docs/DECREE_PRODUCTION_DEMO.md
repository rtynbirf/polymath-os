# Decree Enforcement — Production Demo

This is a **production-style demonstration** that `Runtime.set_decree_log(dl)`
is wired into a real Singulyar EIR kernel run, enforcing the human's
foundational decrees stored at `~/.polymath-os/decrees.db`.

Per **ADR-0021** (`ВОЛЯ = НАКАЗ`) and **ADR-0022**, the decree log is the
**supreme law layer** — above policy, above capability selection, above the
kernel. The decree gate runs inside `Runtime._advance()` **before**
`self.policy.check_intent(intent)`. A non-compliant decree hard-blocks the
intent → emits a `DECREE_BLOCK` ledger event → transitions the intent to
`WAITING_FOR_HUMAN`. It is never silently downgraded to a softer state.

## What the demo does

1. Opens the **real** `DecreeLog` at `~/.polymath-os/decrees.db`
   (the 7 foundational decrees — `ЧЕЛОВЕК=PID=1`, `PAROLE>LANGUE`, prohibitions
   against Google DNS / Cloudflare / Chrome+Firefox+Edge+Safari, `UNKNOWN`
   first-class, `Default-deny`).
2. Verifies the hash chain on open (fail-closed per ADR-0006).
3. Prints a summary of the active laws / prohibitions (count + first 50 chars
   of each).
4. Constructs a `Runtime` with one `Capability` for operation `send` bound to
   `MemoryAdapter` (`adapter_id="memory"`, `risk_ceiling="low"`,
   `idempotent=True`), with `Policy({"send"})` and `redaction_key=b"demo-key"`.
5. Calls `rt.set_decree_log(dl)` to attach the decree log to the Runtime.
6. **Intent 1** — `"publish note about default-deny"`:
   no prohibition matches → passes the decree gate → passes policy →
   adapter executes → postcondition `{"v": "x"}` matches →
   **`CONFIRMED`**.
7. **Intent 2** — `"send data to Google API"`:
   matches decree #3 `"never use Google DNS"` (prohibition, term: `google`)
   → `DECREE_BLOCK` ledger event → **`WAITING_FOR_HUMAN`**.
8. Queries `dl.check_compliance("send data to Google API")` directly to show
   the human which decree fired (decree #, decree text, violation reason).
9. Prints a final summary table including ledger event count, ledger chain
   validity, and the count of `DECREE_BLOCK` events.

## How to run

```bash
# From the repo root:
python3 runtime/src/demo_with_decree.py
```

### Prerequisites

- The decree database **must exist** at `~/.polymath-os/decrees.db`.
  If it does not, the demo exits with code `2` and prints a hint to run
  `python3 scripts/issue_decrees.py` first.
- The 7 foundational decrees must be present (the demo does **not** modify
  the decree database — it is read-only with respect to the decrees).
- Python 3.9+ (standard library only — no external deps).

## Expected output (shape)

```
================================================================
 SINGULYAR EIR — PRODUCTION DECREE ENFORCEMENT DEMO
 Real DecreeLog @ ~/.polymath-os/decrees.db
 Decree gate wired into Runtime._advance() (ADR-0021 + ADR-0022)
================================================================

[DECREE LOG] 7 active law(s)/prohibition(s) loaded:
  # 1 [law        ] ЧЕЛОВЕК = PID=1. Каждый инструмент — fork-exec от чел
  # 2 [law        ] PAROLE > LANGUE. Индивидуальное слово выше коллективн
  # 3 [prohibition] never use Google DNS
  # 4 [prohibition] never use Cloudflare
  # 5 [prohibition] never use Chrome Firefox Edge Safari
  # 6 [law        ] UNKNOWN first-class. Таймаут не равен failure не рав
  # 7 [law        ] Default-deny. Публикуется только явное publish:true.
[DECREE LOG] chain integrity: OK (total decrees recorded: 7)

...

→ Issuing Intent 1: 'publish note about default-deny'
  (should be CONFIRMED — no prohibition matches)
  resulting state: CONFIRMED

→ Issuing Intent 2: 'send data to Google API'
  (should be WAITING_FOR_HUMAN — decree #3 'never use Google DNS'
   blocks via 'google' match)
  resulting state: WAITING_FOR_HUMAN

[DIRECT QUERY] dl.check_compliance('send data to Google API'):
  compliant   : False
  laws_checked: 7
  violations  : 1 found
    - decree#3: 'never use Google DNS'
      → intent contains prohibited term: google

================================================================
 SUMMARY — Decree Enforcement Production Demo
================================================================
...
Ledger events emitted: <N>
Ledger chain valid   : True
DECREE_BLOCK events  : 1 (Intent 2 blocked by decree#3)
================================================================
RESULT: Decree enforcement is VISIBLE and DEMONSTRABLE in a
        production-style run. The kernel obeyed the human's law.
================================================================
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Demo ran cleanly. Intent 1 → `CONFIRMED`, Intent 2 → `WAITING_FOR_HUMAN`, decrees enforced. |
| `2`  | Decree database not found at `~/.polymath-os/decrees.db`. |
| `1`  | Assertion failure — expected state did not match (indicates a regression in decree enforcement). |

## What this is NOT

- This is **not** a unit test. It is a **production-style demonstration**
  that the wiring is real and visible. Unit tests for the decree gate live
  in `runtime/tests/test_decree_runtime_integration.py`.
- This demo does **not** modify `~/.polymath-os/decrees.db`. The 7
  foundational decrees remain unchanged.
- This demo does **not** modify the existing `runtime/src/demo.py`. That
  file is preserved as the original failover/crash-window recovery demo.
- The decree matcher is v0.4 keyword matching (per `decree_log.py` line
  161). It is intentionally simple and deterministic — no LLM, no external
  services. Semantic NLP matching is scheduled for v0.5.

## Related files

| File | Role |
|------|------|
| `runtime/src/demo_with_decree.py` | This demo (production-style decree enforcement). |
| `runtime/src/demo.py` | Original demo — failover, crash-window recovery, honest UNKNOWN (preserved, untouched). |
| `runtime/src/decree_log.py` | The `DecreeLog` class — append-only hash-chained SQLite log of the human's decrees. |
| `runtime/src/singulyar_runtime.py` | `Runtime.set_decree_log(dl)` + decree gate inside `_advance()`. |
| `runtime/tests/test_decree_runtime_integration.py` | Unit tests for the decree gate (106/106 pass, 4 skipped — expected). |
| `apps/browser/decree-bridge.js` | Node bridge from the Decree Portal UI to this Python `DecreeLog`. |
| `scripts/issue_decrees.py` | Idempotent script that issues the 7 foundational decrees (re-runnable). |
