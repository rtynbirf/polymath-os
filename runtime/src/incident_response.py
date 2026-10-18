"""runtime/src/incident_response.py — AI-Assisted Incident Response (ADR-0035).

When the SINGULYAR EIR circuit breaker trips (a cascade of DECREE_BLOCK
events pushes the count past `Runtime.set_circuit_breaker(threshold=...)`),
the kernel halts: every new Intent short-circuits to WAITING_FOR_HUMAN
(per ADR-0029 §12 — Martin Fowler's 3-state circuit breaker pattern,
https://martinfowler.com/bliki/CircuitBreaker.html).

The halt is the easy half. The hard half is: *what should the human do
next?* Today the human must open the Evidence Ledger, manually scan
every DECREE_BLOCK event, mentally aggregate (which decrees fired?
which terms matched? which intents keep colliding?), and pick a
remediation (resume, supersede, or investigate).

This module implements ADR-0035 — an `IncidentAnalyzer` that does the
aggregation for the human, optionally asks an LLM for a remediation
suggestion, and returns a structured list of suggested actions:

  1. {"action": "investigate", "description": "Check Evidence Ledger for source"}
  2. {"action": "resume",      "description": "Resume from circuit breaker"}
  3. {"action": "supersede",   "decree_seq": N, "reason": "..."}
  4. {"action": "llm_recommendation", "description": "<raw LLM text>"}  (optional)

The analyser is **read-only** w.r.t. the kernel: it reads the breaker
state via `runtime.get_circuit_breaker_state()` and reads DECREE_BLOCK
events from `runtime.ledger.events`, but it NEVER mutates the breaker
state, NEVER issues or supersedes decrees, and NEVER resumes the
kernel. All suggested actions are executed by the caller (the human or
a higher-level automation layer). This separation mirrors ADR-0007
(research vs execution) — the analyser is research, the caller is
execution.

Why a separate module (not in `singulyar_runtime.py`)?
  - Single Responsibility: the kernel owns the breaker state machine
    (CLOSED -> OPEN -> HALF-OPEN -> CLOSED); incident analysis is a
    downstream consumer.
  - Testability: this module can be unit-tested with the same
    `Runtime + DecreeLog + MemoryAdapter` scaffolding as
    `test_circuit_breaker.py`, without touching kernel internals.
  - Forward-compat: future incident-response features (auto-remediation
    policies, Slack/PagerDuty webhooks, post-mortem generation) extend
    this module without bloating the kernel.

Per ADR-0012 (SINGULYAR EIR as Layer 5), the optional `llm_adapter`
follows the same pattern as `LLMLocalAdapter`: rule-layer works
without weights; the LLM is an enhancement. When `llm_adapter is None`,
the analyser falls back to a deterministic rule-based analysis
(most-common matched_term + most-common decree_seq). When an LLM is
provided, the analyser asks it to analyse the cascade and appends its
free-text recommendation as an extra `llm_recommendation` action.

Duck-typed `llm_adapter` contract:
  Any object exposing `.complete(prompt: str) -> str` (or `.chat(prompt)
  -> str`). The analyser tries `.complete()` first, then `.chat()` as a
  fallback. This decouples the module from any specific LLM client
  (LLMLocalAdapter, a future cloud LLM client, or a mock for tests).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Optional


# How many recent DECREE_BLOCK events to aggregate by default. Matches
# the default circuit-breaker threshold (Runtime.set_circuit_breaker
# defaults to threshold=10). Caller can override via the `_max_events`
# attribute on the analyser instance (kept simple for v3.20.0).
_DEFAULT_MAX_EVENTS = 10


class IncidentAnalyzer:
    """Analyse a tripped circuit breaker and suggest remediation.

    Construct with a `Runtime` (provides breaker state + Evidence
    Ledger), an optional `DecreeLog` (provides decree metadata for
    richer analysis), and an optional `llm_adapter` (provides
    free-text remediation suggestions).

    Usage:
        rt = Runtime(...)
        rt.set_decree_log(dl)
        rt.set_circuit_breaker(threshold=3, window=60)
        # ... trip the breaker by issuing DECREE_BLOCK-violating intents ...
        analyzer = IncidentAnalyzer(rt, dl)  # rule-based (no LLM)
        report = analyzer.analyze_circuit_breaker_trip()
        if report["tripped"]:
            for suggestion in report["suggestions"]:
                print(suggestion)
    """

    def __init__(
        self,
        runtime: Any,
        decree_log: Optional[Any] = None,
        llm_adapter: Optional[Any] = None,
    ) -> None:
        # We deliberately avoid hard-typing `runtime` and `decree_log`
        # — duck-typed contracts keep the module testable with mocks
        # and decoupled from kernel internals (per ADR-0007: research
        # layer should not import the execution layer's concrete types).
        self.runtime = runtime
        self.decree_log = decree_log
        self.llm_adapter = llm_adapter
        # Overridable per-instance (kept simple for v3.20.0; future
        # versions may expose this as a constructor parameter).
        self._max_events: int = _DEFAULT_MAX_EVENTS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_circuit_breaker_trip(self) -> Dict[str, Any]:
        """Analyse the circuit breaker's current state and the cascade
        of DECREE_BLOCK events that triggered it.

        Returns one of two shapes:

          # Breaker is CLOSED (no trip):
          {"tripped": False, "state": "closed"}

          # Breaker is OPEN or HALF-OPEN (tripped):
          {
            "tripped":     True,
            "state":       "open" | "half_open",
            "block_count": int,         # DECREE_BLOCK events in the window
            "analysis": {
              "decree_seq_counts":   {seq: count, ...},
              "matched_term_counts": {term: count, ...},
              "intent_ids":          [iid, ...],
              "unique_intent_count": int,
              "most_common_decree_seq": int | None,
              "most_common_term":       str | None,
              "source":               "rule-based" | "llm",
              "llm_response":         str | None,
            },
            "suggestions": [<list of action dicts; see suggest_remediation>],
          }

        Algorithm:
          1. Snapshot the breaker state via runtime.get_circuit_breaker_state().
          2. If state == "closed" → return {"tripped": False, "state": "closed"}.
          3. Otherwise: gather the last N DECREE_BLOCK events from the
             Evidence Ledger (runtime.ledger.events). Each event's
             payload has a "violations" list of {decree_seq, decree_text,
             violation, matched_term} dicts — flatten these into the
             per-event aggregation.
          4. Compute decree_seq_counts, matched_term_counts, intent_ids,
             unique_intent_count. Pick most_common_decree_seq and
             most_common_term (ties broken by first-seen order —
             deterministic for reproducibility per ADR-0019).
          5. If llm_adapter is not None: build a compact prompt
             containing the aggregated counts + the raw DECREE_BLOCK
             summaries, call llm_adapter.complete(prompt) (with
             .chat(prompt) as a fallback), store the raw text in
             analysis["llm_response"], set analysis["source"] = "llm".
          6. Else: analysis["source"] = "rule-based", llm_response = None.
          7. suggestions = self.suggest_remediation(analysis).
          8. Return the tripped dict.
        """
        # 1. Snapshot the breaker state.
        cb_state = self.runtime.get_circuit_breaker_state()
        state = cb_state.get("state", "closed")

        # 2. Not tripped → short-circuit.
        if state == "closed":
            return {
                "tripped": False,
                "state": "closed",
                "block_count": int(cb_state.get("block_count", 0)),
            }

        # 3. Tripped — gather the last N DECREE_BLOCK events from the
        # Evidence Ledger. We read runtime.ledger.events directly
        # (the ledger is a hash-linked event list per
        # singulyar_runtime.EvidenceLedger; .events is the live list).
        blocks = self._gather_decree_block_events()

        # 4. Aggregate patterns: which decrees fired? which terms
        # matched? which intents collided?
        analysis = self._rule_based_analysis(blocks)

        # 5. Optional LLM analysis: ask the LLM to analyse the cascade
        # and suggest remediation. We keep the deterministic analysis
        # (step 4) as a stable baseline and add the LLM's free-text
        # recommendation on top — never replace.
        llm_response: Optional[str] = None
        if self.llm_adapter is not None:
            llm_response = self._llm_analyze(blocks, analysis)
            analysis["source"] = "llm"
        else:
            analysis["source"] = "rule-based"
        analysis["llm_response"] = llm_response

        # 7. Build the suggestions list from the analysis dict.
        suggestions = self.suggest_remediation(analysis)

        # 8. Return the tripped report.
        return {
            "tripped": True,
            "state": state,
            "block_count": len(blocks),
            "analysis": analysis,
            "suggestions": suggestions,
        }

    def suggest_remediation(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return a list of suggested remediation actions for the human.

        The list is ordered safest-first:
          1. investigate — always present. The human should review the
             raw Evidence Ledger events first.
          2. resume — always present. Maps to
             runtime.resume_from_circuit_breaker() (force-closes the
             breaker, per ADR-0029 §12).
          3. supersede — present only when analysis has a
             most_common_decree_seq. Maps to
             decree_log.supersede(seq, reason) (per ADR-0028).
          4. llm_recommendation — present only when analysis has an
             llm_response. Surfaces the LLM's free-text recommendation
             verbatim.

        The analyser NEVER executes any of these — it only suggests.
        Execution is the caller's job (human or higher-level automation).
        """
        suggestions: List[Dict[str, Any]] = []

        # 1. investigate — always present (safest default).
        suggestions.append({
            "action": "investigate",
            "description": "Check Evidence Ledger for source",
        })

        # 2. resume — always present (lightest intervention).
        suggestions.append({
            "action": "resume",
            "description": "Resume from circuit breaker",
        })

        # 3. supersede — present only when we have a most-common decree
        # to supersede. The reason is templated from the most-common
        # matched term so the human (or AdrAmender) has context.
        most_common_seq = analysis.get("most_common_decree_seq")
        most_common_term = analysis.get("most_common_term")
        if most_common_seq is not None:
            term_clause = (
                f" (matched term: {most_common_term!r})"
                if most_common_term else ""
            )
            suggestions.append({
                "action": "supersede",
                "decree_seq": int(most_common_seq),
                "reason": (
                    f"Decree #{most_common_seq} fired the most during "
                    f"the cascade{term_clause}; supersede to unblock "
                    f"the breaker (per ADR-0028)."
                ),
            })

        # 4. llm_recommendation — present only when an LLM was used.
        # The raw text is surfaced verbatim (v3.20.0 does NOT parse
        # it into structured actions — see ADR-0035 Alternatives §5).
        llm_response = analysis.get("llm_response")
        if llm_response:
            suggestions.append({
                "action": "llm_recommendation",
                "description": str(llm_response),
            })

        return suggestions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gather_decree_block_events(self) -> List[Dict[str, Any]]:
        """Pull the last N DECREE_BLOCK events from the Evidence Ledger.

        Returns the events in chronological order (oldest first). Each
        returned item is the full ledger event dict (with `type`,
        `payload`, `hash`, etc.). The caller (`_rule_based_analysis`)
        reads `event["payload"]["violations"]` for the per-event
        aggregation.
        """
        ledger = getattr(self.runtime, "ledger", None)
        if ledger is None:
            return []
        events = getattr(ledger, "events", [])
        # Filter to DECREE_BLOCK events only, take the last N, preserve
        # chronological order.
        decree_blocks = [
            e for e in events
            if isinstance(e, dict) and e.get("type") == "DECREE_BLOCK"
        ]
        return decree_blocks[-self._max_events:]

    def _rule_based_analysis(
        self, blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Deterministic aggregation of DECREE_BLOCK events.

        For each event we read payload["violations"] — a list of
        {decree_seq, decree_text, violation, matched_term} dicts
        (the shape produced by DecreeLog.check_compliance() and
        recorded by Runtime._advance() in the DECREE_BLOCK event).

        Aggregates:
          - decree_seq_counts: Counter[decree_seq -> count]
          - matched_term_counts: Counter[matched_term -> count]
          - intent_ids: list of every intent_id that hit DECREE_BLOCK
            (best-effort proxy for "which agents?" — the current
            DECREE_BLOCK payload has intent_id but no agent_id; see
            ADR-0035 Negative Consequences)
          - unique_intent_count: len(set(intent_ids))
          - most_common_decree_seq: int | None (ties: first-seen)
          - most_common_term: str | None (ties: first-seen)

        Ties are broken by **first-seen order** (not by Counter's
        internal ordering, which is insertion-order in CPython but
        not guaranteed by the language spec). This makes the analysis
        reproducible across runs (per ADR-0019 — observability first).
        """
        decree_seq_counts: Counter = Counter()
        matched_term_counts: Counter = Counter()
        intent_ids: List[str] = []
        # Track first-seen order for deterministic tie-breaking.
        seq_first_seen: List[int] = []
        term_first_seen: List[str] = []

        for event in blocks:
            payload = event.get("payload", {}) if isinstance(event, dict) else {}
            iid = payload.get("intent_id")
            if iid is not None:
                intent_ids.append(str(iid))
            violations = payload.get("violations", []) or []
            for v in violations:
                if not isinstance(v, dict):
                    continue
                seq = v.get("decree_seq")
                if seq is not None:
                    try:
                        seq_int = int(seq)
                    except (TypeError, ValueError):
                        continue
                    decree_seq_counts[seq_int] += 1
                    if seq_int not in seq_first_seen:
                        seq_first_seen.append(seq_int)
                term = v.get("matched_term")
                if term:
                    term = str(term)
                    matched_term_counts[term] += 1
                    if term not in term_first_seen:
                        term_first_seen.append(term)

        # Deterministic "most common" — highest count wins; ties
        # broken by first-seen order. Counter.most_common(1) would
        # break ties by insertion order in CPython, but we implement
        # the tie-break explicitly so the contract is language-spec
        # independent (per ADR-0019 — reproducibility).
        most_common_decree_seq = self._most_common_first_seen(
            decree_seq_counts, seq_first_seen
        )
        most_common_term = self._most_common_first_seen(
            matched_term_counts, term_first_seen
        )

        return {
            "decree_seq_counts": dict(decree_seq_counts),
            "matched_term_counts": dict(matched_term_counts),
            "intent_ids": intent_ids,
            "unique_intent_count": len(set(intent_ids)),
            "most_common_decree_seq": most_common_decree_seq,
            "most_common_term": most_common_term,
        }

    @staticmethod
    def _most_common_first_seen(
        counts: Counter, first_seen: List[Any]
    ) -> Optional[Any]:
        """Return the item with the highest count; ties broken by
        first-seen order. Returns None if `counts` is empty.
        """
        if not counts:
            return None
        max_count = max(counts.values())
        # Iterate in first-seen order so the tie-break is deterministic.
        for item in first_seen:
            if counts.get(item, 0) == max_count:
                return item
        # Defensive: if first_seen is somehow empty but counts isn't,
        # fall back to Counter's most_common (CPython insertion order).
        return counts.most_common(1)[0][0]

    def _llm_analyze(
        self,
        blocks: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> Optional[str]:
        """Ask the LLM to analyse the cascade and suggest remediation.

        Builds a compact prompt with the aggregated counts + the raw
        DECREE_BLOCK summaries, calls `llm_adapter.complete(prompt)`
        (with `.chat(prompt)` as a fallback), and returns the raw text.
        Returns None if the LLM call raises (we never let an LLM
        failure break the analysis — the rule-based analysis is always
        returned alongside).
        """
        prompt = self._build_llm_prompt(blocks, analysis)
        try:
            # Duck-typed: try .complete() first, then .chat() (some LLM
            # clients use one name, some the other).
            if hasattr(self.llm_adapter, "complete"):
                return str(self.llm_adapter.complete(prompt))
            if hasattr(self.llm_adapter, "chat"):
                return str(self.llm_adapter.chat(prompt))
            return None
        except Exception:
            # Per ADR-0006 (falsifiable self-properties): honest
            # failure, not silent. The rule-based analysis is still
            # returned; llm_response stays None.
            return None

    def _build_llm_prompt(
        self,
        blocks: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> str:
        """Build a compact JSON prompt for the LLM.

        Format:
          You are an incident-response assistant for the SINGULYAR EIR
          kernel. The circuit breaker tripped after a cascade of
          DECREE_BLOCK events. Analyse the cascade and suggest
          remediation in 2-3 sentences.

          Aggregate counts:
          <JSON of decree_seq_counts, matched_term_counts, etc.>

          Recent DECREE_BLOCK events:
          <JSON list of {intent_id, reason, violations} dicts>

          Suggest: should the human resume the breaker, supersede a
          decree (which seq?), or investigate further?
        """
        # Compact summary of the recent DECREE_BLOCK events (avoid
        # dumping full payloads — keep the prompt small for local LLMs
        # with limited context, per ADR-0012).
        recent = []
        for event in blocks:
            payload = event.get("payload", {}) if isinstance(event, dict) else {}
            recent.append({
                "intent_id": payload.get("intent_id"),
                "reason": payload.get("reason"),
                "violations": payload.get("violations", []),
            })

        # Only include the analysis fields the LLM needs (avoid
        # recursion: llm_response is not yet set when we build this).
        analysis_summary = {
            "decree_seq_counts": analysis.get("decree_seq_counts", {}),
            "matched_term_counts": analysis.get("matched_term_counts", {}),
            "unique_intent_count": analysis.get("unique_intent_count", 0),
            "most_common_decree_seq": analysis.get("most_common_decree_seq"),
            "most_common_term": analysis.get("most_common_term"),
        }

        return (
            "You are an incident-response assistant for the SINGULYAR EIR "
            "kernel. The circuit breaker tripped after a cascade of "
            "DECREE_BLOCK events. Analyse the cascade and suggest "
            "remediation in 2-3 sentences.\n\n"
            "Aggregate counts:\n"
            f"{json.dumps(analysis_summary, ensure_ascii=False, indent=2)}\n\n"
            "Recent DECREE_BLOCK events:\n"
            f"{json.dumps(recent, ensure_ascii=False, indent=2)}\n\n"
            "Suggest: should the human resume the breaker, supersede a "
            "decree (which seq?), or investigate further?"
        )


__all__ = ["IncidentAnalyzer"]
