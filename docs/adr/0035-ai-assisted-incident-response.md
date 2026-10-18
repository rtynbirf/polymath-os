# ADR-0035 — AI-Assisted Incident Response

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** observability, circuit-breaker, llm, incident-response, v3.20.0
**Deciders:** @USER (Командир корабля)
**Supersedes:** None (extends ADR-0029 §12 — Martin Fowler 3-state circuit breaker)

## Context

Per ADR-0029 §12, the SINGULYAR EIR kernel implements a **Martin Fowler
3-state circuit breaker** (CLOSED → OPEN → HALF-OPEN → CLOSED) that
trips when a rolling window accumulates `threshold` `DECREE_BLOCK`
events. When the breaker trips, every new Intent short-circuits to
`WAITING_FOR_HUMAN` — the kernel halts, exactly like a stock-market
circuit breaker halts trading.

The halt is the **easy** half of the problem. The **hard** half is:
*what should the human do next?* Today the human must:
1. Open the Evidence Ledger.
2. Manually scan every `DECREE_BLOCK` event (which can be dozens).
3. Mentally aggregate: which decrees fired? which terms matched? which
   intents/agents keep colliding with the same prohibition?
4. Pick a remediation: `resume_from_circuit_breaker()`, supersede the
   decree (ADR-0028), or investigate the source.

This is exactly the kind of pattern-recognition + summarisation task
that a local LLM (per ADR-0012, LLMLocalAdapter) is good at — and
exactly the kind of repetitive triage the human should NOT have to do
by hand. The breaker already has all the raw evidence in the
**Evidence Ledger**; we just need a thin analyser that:

1. Reads the breaker state.
2. Pulls the last N `DECREE_BLOCK` events from the ledger.
3. Aggregates them (which decrees, which matched terms, which
   intent_ids).
4. Asks the LLM to suggest remediation (if available), OR falls back
   to a deterministic rule-based analysis (most-common matched_term +
   most-common decree_seq).
5. Returns a structured list of suggested actions the human can take
   with one click.

## Decision

Implement **`runtime/src/incident_response.py`** with a single class
`IncidentAnalyzer` and two public methods.

### `IncidentAnalyzer(runtime, decree_log, llm_adapter=None)`

- `runtime` — a `singulyar_runtime.Runtime` instance. The analyser
  reads the breaker state via `runtime.get_circuit_breaker_state()`
  and reads the Evidence Ledger via `runtime.ledger.events`.
- `decree_log` — a `decree_log.DecreeLog` instance. Used to resolve
  `decree_seq → decree_text` for richer analysis (and to identify
  decrees that have already been superseded per ADR-0028). May be
  `None` (the analyser still works, just with less decree metadata).
- `llm_adapter` — optional. Duck-typed: any object exposing
  `.complete(prompt: str) -> str` (or `.chat(prompt) -> str`). When
  provided, the analyser asks the LLM to analyse the cascade and
  suggest remediation. When `None`, the analyser falls back to a
  deterministic rule-based analysis. This mirrors the LLMLocalAdapter
  pattern: rule-layer works without weights; LLM is an enhancement.

### `analyze_circuit_breaker_trip() -> dict`

The entry point. Returns one of two shapes:

```python
# Not tripped (breaker is CLOSED or no DECREE_BLOCKs at all):
{
    "tripped": False,
    "state":   "closed",   # snapshot of breaker state for context
}

# Tripped (breaker is OPEN or HALF-OPEN):
{
    "tripped":     True,
    "state":       "open" | "half_open",
    "block_count": int,   # number of DECREE_BLOCK events in the ledger window
    "analysis":    {       # structured pattern aggregation
        "decree_seq_counts":   {seq: count, ...},   # which decrees fired
        "matched_term_counts": {term: count, ...},  # which terms matched
        "intent_ids":          [iid, ...],         # which intents collided
        "unique_intent_count":  int,
        "most_common_decree_seq": int | None,       # rule-based winner
        "most_common_term":       str | None,       # rule-based winner
        "source":               "rule-based" | "llm",
        "llm_response":         str | None,         # raw LLM text (if used)
    },
    "suggestions": [       # list of suggested remediation actions
        {"action": "resume",     "description": "..."},
        {"action": "supersede",  "decree_seq": N, "reason": "..."},
        {"action": "investigate","description": "..."},
        # (+ optionally an "llm_recommendation" action with the raw text)
    ],
}
```

Algorithm:
1. `state = runtime.get_circuit_breaker_state()`.
2. If `state["state"] == "closed"` → return `{"tripped": False, "state": "closed"}`.
3. Otherwise (OPEN or HALF-OPEN): gather the last N (default 10)
   `DECREE_BLOCK` events from `runtime.ledger.events`. Each event's
   `payload["violations"]` is a list of `{decree_seq, decree_text,
   violation, matched_term}` dicts — flatten them into the
   per-event aggregation.
4. Compute `decree_seq_counts`, `matched_term_counts`, `intent_ids`,
   `unique_intent_count`. Pick `most_common_decree_seq` and
   `most_common_term` (ties broken by first-seen order).
5. If `llm_adapter` is not None: build a compact prompt containing
   the aggregated counts + the raw DECREE_BLOCK summaries, call
   `llm_adapter.complete(prompt)`, store the raw text in
   `analysis["llm_response"]`, set `analysis["source"] = "llm"`.
6. Else: `analysis["source"] = "rule-based"`, `llm_response = None`.
7. `suggestions = self.suggest_remediation(analysis)`.
8. Return the tripped dict.

### `suggest_remediation(analysis) -> list[dict]`

Returns a deterministic list of suggested actions, derived from the
aggregated `analysis` dict:

1. **`{"action": "investigate", "description": "Check Evidence Ledger for source"}`**
   — always present. The human should review the raw events first.
2. **`{"action": "resume", "description": "Resume from circuit breaker"}`**
   — always present. Maps to `runtime.resume_from_circuit_breaker()`.
3. **`{"action": "supersede", "decree_seq": N, "reason": "..."}`**
   — present only when `analysis["most_common_decree_seq"]` is not
   None. Maps to `decree_log.supersede(N, reason)` (per ADR-0028).
   The `reason` is templated from the most-common matched term.
4. **`{"action": "llm_recommendation", "description": <raw LLM text>}`**
   — present only when `analysis["llm_response"]` is not None.
   Surfaces the LLM's free-text recommendation verbatim.

The list ordering is intentionally **investigate → resume → supersede
→ llm_recommendation**: investigate is the safest default, resume is
the lightest intervention, supersede is heavier (irreversible per
ADR-0028), and the LLM recommendation is appended (never replaces the
deterministic options).

### Why a separate module (not in `singulyar_runtime.py`)?

- **Single Responsibility.** The runtime kernel owns the breaker
  *state machine* (CLOSED → OPEN → HALF-OPEN). Incident *analysis* is
  a downstream consumer — it reads the ledger, never mutates the
  breaker. Mixing them would bloat `singulyar_runtime.py` (already
  ~950 lines) and couple the kernel to the LLM adapter.
- **Testability.** A separate module can be unit-tested with the same
  `Runtime + DecreeLog + MemoryAdapter` scaffolding used by
  `test_circuit_breaker.py`, without touching kernel internals.
- **Forward-compat.** Future incident-response features (auto-remediation
  policies, Slack/PagerDuty webhooks, post-mortem generation) extend
  this module without touching the kernel.

### Why duck-typed `llm_adapter`?

The existing `LLMLocalAdapter` implements the kernel's `Adapter`
contract (`execute(intent, key)`, `read_state(intent, key)`) — which is
awkward to invoke for a free-text "analyse this cascade" query (it
requires constructing an `Intent` object, going through the kernel's
policy + capability gates, etc.). For incident analysis we want a
direct `complete(prompt) -> str` call. Duck-typing keeps the module
decoupled from any specific LLM client (LLMLocalAdapter, a future
cloud LLM client, or a mock for tests).

## Consequences

**Positive:**
- **Closes the "what now?" gap** after a breaker trip — the human
  gets a structured, ordered list of remediation options instead of
  having to read the raw ledger by hand.
- **Optional LLM.** The analyser degrades gracefully: with no
  `llm_adapter` it still produces a useful rule-based analysis
  (most-common term + most-common decree). With an LLM it adds a
  free-text recommendation on top. This mirrors the LLMLocalAdapter
  "rule-layer always works, LLM is enhancement" pattern (per
  ADR-0012).
- **No kernel coupling.** The analyser reads `runtime.ledger` and
  `runtime.get_circuit_breaker_state()` only — it never mutates
  kernel state. The suggested `resume` / `supersede` actions are
  executed by the human (or by a future automation layer), not by the
  analyser itself.
- **Audit-friendly.** Every analysis is a JSON-serialisable dict —
  easy to log, display in the Decree Portal UI, or attach to a
  post-mortem. The `analysis["source"]` field records whether the
  analysis was rule-based or LLM-assisted (auditability per ADR-0019).

**Negative:**
- **`agent_id` is not in the current `DECREE_BLOCK` payload.** The
  existing event schema has `intent_id` but no `agent_id`. The
  analyser uses `intent_id` as a best-effort proxy for "which agents?"
  until the kernel payload is extended (a separate change). This is a
  known limitation — surfaced in the analysis dict as `intent_ids`
  rather than `agents`.
- **LLM is non-deterministic.** When `llm_adapter` is provided, the
  `llm_response` text varies run-to-run. The deterministic
  suggestions (investigate/resume/supersede) are computed independently
  of the LLM, so the human always has a stable fallback regardless of
  what the LLM says.
- **`supersede` is irreversible.** The `supersede` suggestion uses
  `decree_seq` from the analysis, which is correct — but the human
  must confirm before acting (the analyser does NOT auto-supersede;
  it only suggests). Auto-supersession is explicitly out of scope.

**Neutral:**
- The `N` parameter (default 10 — how many recent `DECREE_BLOCK`
  events to aggregate) is configurable via the analyser's internal
  `_max_events` attribute. It defaults to 10 because the breaker
  threshold defaults to 10 (per `Runtime.set_circuit_breaker`).
- The analyser is **read-only** w.r.t. the kernel: it cannot resume
  the breaker, supersede decrees, or modify any state. All suggested
  actions are executed by the caller (human or higher-level
  automation).

## Verification

- `runtime/tests/test_incident_response.py` — 4 tests:
  1. `test_analyze_not_tripped` — closed breaker → `{"tripped": False}`.
  2. `test_analyze_tripped_returns_analysis` — tripped breaker →
     `{"tripped": True, "block_count": N, "analysis": {...}, "suggestions": [...]}`.
  3. `test_suggest_remediation_includes_resume` — `suggest_remediation(analysis)`
     always returns a `{"action": "resume", ...}` entry.
  4. `test_rule_based_analysis_finds_most_common_term` — without an
     LLM, the rule-based analysis correctly identifies the
     most-common `matched_term` ("google") from a cascade of
     Google-prohibition DECREE_BLOCKs.
- All tests use the same `tempfile.TemporaryDirectory + DecreeLog +
  Runtime + MemoryAdapter` scaffolding as `test_circuit_breaker.py`
  — no new test fixtures required.
- `make verify` (open-source contract) is unchanged — this ADR adds
  a new module + tests, it does not add or remove any verifiable
  claim.

## Alternatives considered

1. **Auto-resume on trip** — rejected: the breaker exists precisely
   to *halt* and force human review (per ADR-0029 §12, "cascade-failure
   protection, like a stock-market halt"). Auto-resume defeats the
   purpose; the human must always be in the loop.

2. **Auto-supersede the most-violated decree** — rejected: supersession
   is irreversible (per ADR-0028) and the matched_term may be a false
   positive (the v0.4 substring matcher had this problem; the v0.6
   word-boundary matcher is better but still not perfect). Surfacing
   the suggestion and letting the human decide is the right default.

3. **Embed the analyser in `singulyar_runtime.py`** — rejected: see
   "Why a separate module" above (SRP + testability + forward-compat).

4. **Mandatory LLM** (no rule-based fallback) — rejected: the
   LLMLocalAdapter explicitly supports running without model weights
   (rule-layer only, per ADR-0012). Incident response must work in
   the same offline/no-weights environment. The rule-based fallback
   also serves as a deterministic baseline against which LLM
   suggestions can be compared.

5. **Parse the LLM response into structured actions** — rejected for
   v3.20.0: LLM output is non-deterministic and parsing it into
   action dicts would require a schema + retry logic. v1 surface the
   raw text as an `llm_recommendation` action; v2+ can add structured
   parsing if the LLM turns out to be reliable enough.

## References

- ADR-0029 (СИНГУЛЯР Security Model) — §12 defines the 3-state circuit
  breaker this analyser consumes.
- ADR-0021 (Decree as Supreme Law) — DECREE_BLOCK events are emitted
  by the decree gate in `Runtime._advance()` when a prohibition
  decree blocks an Intent.
- ADR-0028 (Decree Supersession Mechanism) — the `supersede` suggested
  action maps to `DecreeLog.supersede(target_seq, reason)`.
- ADR-0012 (SINGULYAR EIR as Layer 5) — `LLMLocalAdapter` is the
  reference implementation for the optional `llm_adapter` parameter.
- ADR-0019 (Observability First) — every analysis is a structured,
  JSON-serialisable dict, ready for dashboards and post-mortems.
- ADR-0007 (Multi-Agent Research vs Execution) — the analyser is
  read-only w.r.t. the kernel (research), it does not execute
  remediation (execution is the human's job).
- `runtime/src/singulyar_runtime.py` — `Runtime`,
  `EvidenceLedger`, `get_circuit_breaker_state()`,
  `resume_from_circuit_breaker()`, `DECREE_BLOCK` event payload.
- `runtime/src/decree_log.py` — `DecreeLog.check_compliance()` return
  shape (the source of `matched_term` + `decree_seq` in `DECREE_BLOCK`
  event payloads), and `DecreeLog.supersede()`.
- `runtime/src/incident_response.py` — implementation.
- `runtime/tests/test_incident_response.py` — tests.

## Self-reference

This ADR can be superseded by a future decree-driven amendment (per
ADR-0026). For example, a decree may add structured LLM-response
parsing (Alternative 5 above) — the `llm_recommendation` action would
then be replaced by parsed `supersede` / `resume` / `investigate`
actions derived from the LLM's text, and the rule-based fallback
would remain as a deterministic baseline.
