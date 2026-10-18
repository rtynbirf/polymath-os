"""runtime/src/decree_aware_agent.py — Decree-Aware Agent Behavior (per ADR-0033).

When an AI agent's Intent gets DECREE_BLOCKed by the AgentMesh decree
gate (per ADR-0024), the agent should ADAPT — try a different approach
that doesn't violate the decree. This is the "agency within the law"
property: the human's decree is supreme (PAROLE > LANGUE per
ADR-0021), but the agent is not paralyzed by a single block — it learns
which specific term triggered the block and retries with a modified
description.

The DecreeAwareAgent wraps an existing agent in an AgentMesh. It is a
thin orchestration layer above `AgentMesh.send()`:

    mesh = AgentMesh(decree_log=dl)
    mesh.register(SINGULYAR_EIR_CARD, execute_fn)
    agent = DecreeAwareAgent(mesh, "singulyar-eir.local", llm_adapter=my_llm)
    result = agent.propose_with_adaptation(
        description="send data to Google Cloud Storage",
        operation="storage.write",
        payload={"data": "x"},
    )
    # result["blocked"] == False  (after adapting 'google' → '[redacted]')
    # result["adaptation_history"] == [
    #     {attempt: 1, description: "send data to Google Cloud Storage",
    #      blocked: True, ...},
    #     {attempt: 2, description: "send data to [redacted] Cloud Storage",
    #      blocked: False, ...},
    # ]

Adaptation strategies (per ADR-0033 §Decision):

1. LLM-available path — when an llm_adapter is attached, the agent
   asks the LLM for an alternative description that avoids the matched
   term. The LLM is treated as an oracle: callable(prompt) -> str OR
   an object with .generate(prompt) / .answer(prompt) methods. This is
   the "smart" path — the LLM can suggest semantically equivalent
   alternatives ("send to Fastly" instead of "send to Cloudflare").

2. No-LLM path — when no llm_adapter is attached, the agent falls
   back to simple string replacement: remove the matched term
   (case-insensitive regex) and substitute a generic placeholder
   ('[redacted]'). If the entire description was the matched term,
   return a generic alternative. This is the "dumb" path — it
   guarantees progress but may produce a less natural alternative.

In both paths, the adapted description is re-submitted through the
SAME decree gate — the decree is supreme, the agent's adaptation must
still pass it. If the adapted description is ALSO blocked (e.g. a
multi-term prohibition), the agent adapts AGAIN, up to max_retries.

This ADR closes the "agent paralysis" gap: before ADR-0033, a
DECREE_BLOCK was a hard stop — the agent could not proceed. Now the
agent can adapt and retry, respecting the decree while still making
progress on the human's goal. The decree remains supreme: the
adaptation MUST pass the decree gate. If no compliant alternative is
found within max_retries, the agent gives up (DECREE_BLOCKED) — never
violates the decree.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

from agent_mesh import AgentMesh, IntentRequest


class DecreeAwareAgent:
    """Wraps an agent in an AgentMesh with decree-aware adaptation behavior.

    Per ADR-0033. When `mesh.send()` returns a DECREE_BLOCK response,
    this agent records the violation and produces an adapted description
    that avoids the matched_term. The adapted description can then be
    retried via `propose_with_adaptation()`.

    The decree's supremacy is preserved: every adaptation MUST re-pass
    the same decree gate. This is **agency within the law**, not a
    backdoor.

    Args:
        mesh: AgentMesh instance — the decree-enforced routing layer
            (per ADR-0024). The wrapped agent must already be registered
            in this mesh under `agent_id`.
        agent_id: id of the wrapped agent (must be registered in mesh).
        llm_adapter: optional LLM for "smart" adaptation. Can be:
            - a callable `(prompt: str) -> str`
            - an object with `.generate(prompt: str) -> str`
            - an object with `.answer(prompt: str) -> str`
            If None, falls back to simple string replacement (the
            "dumb" path).
    """

    def __init__(
        self,
        mesh: AgentMesh,
        agent_id: str,
        llm_adapter: Optional[Any] = None,
    ) -> None:
        self.mesh = mesh
        self.agent_id = agent_id
        self.llm_adapter = llm_adapter
        # Persistent records — survive across propose() calls (audit trail).
        self.violation_history: List[Dict[str, Any]] = []
        self.adaptation_history: List[Dict[str, Any]] = []
        # Per-instance counter for unique IntentRequest ids.
        self._req_counter = 0

    # ─── Public API ──────────────────────────────────────────────────

    def propose(
        self,
        description: str,
        operation: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Propose an Intent to the wrapped agent via the mesh.

        Per ADR-0033. Builds an `IntentRequest`, sends via
        `mesh.send()`. If the response is `DECREE_BLOCK`, records the
        violation and produces an adaptation (via `adapt()`) — but does
        NOT retry. The caller can inspect `result["adaptations"]` for
        the suggested alternative and call `propose()` again with it,
        OR call `propose_with_adaptation()` for automatic retry.

        Args:
            description: the natural-language description of the intent.
            operation: the operation to perform (e.g. "storage.write").
            payload: optional payload dict for the operation.

        Returns:
            {
                "state": "CONFIRMED" | "DECREE_BLOCKED" | ...,
                "blocked": bool,
                "violations": [ {decree_seq, matched_term, decree_text, ...} ],
                "adaptations": [str, ...]  # 1 entry if blocked, 0 if passed
            }
        """
        request = self._build_request(description, operation, payload)
        response = self.mesh.send(self.agent_id, request)

        if response.is_blocked():
            # DECREE_BLOCK — record violation + adapt.
            violation = self._extract_violation(response)
            self.violation_history.append(violation)
            adapted = self.adapt(description, [violation])
            self.adaptation_history.append({
                "original": description,
                "adapted": adapted,
                "violation": violation,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            return {
                "state": "DECREE_BLOCKED",
                "blocked": True,
                "violations": [violation],
                "adaptations": [adapted] if adapted else [],
            }

        # Passed the decree gate — return result.
        state = "CONFIRMED"
        if response.result and isinstance(response.result, dict):
            state = response.result.get("state", "CONFIRMED")
        return {
            "state": state,
            "blocked": False,
            "violations": [],
            "adaptations": [],
        }

    def adapt(
        self,
        original_description: str,
        violations: List[Dict[str, Any]],
    ) -> str:
        """Produce an adapted description that avoids the matched term.

        Per ADR-0033 §Decision. Two paths:

        1. LLM path — if `llm_adapter` is attached, ask it:
            "The intent '{description}' was blocked by decree #{seq}
            ({matched_term}). Suggest an alternative that avoids
            '{matched_term}'."
           The LLM's response is the adapted description. As a safety
           net, if the LLM output STILL contains the matched_term
           (LLMs sometimes ignore the instruction), we apply simple
           replacement on top of the LLM output.

        2. No-LLM path — simple string replacement: remove the matched
           term (case-insensitive regex) and substitute a generic
           placeholder ('[redacted]'). If the entire description was
           the matched term, return a generic alternative.

        Args:
            original_description: the description that was blocked.
            violations: list of violation dicts (uses violations[0]).

        Returns:
            Adapted description string. Never raises — on LLM failure,
            falls back to simple replacement.
        """
        if not violations:
            return original_description

        v = violations[0]
        matched_term = (v.get("matched_term") or "").strip()
        seq = v.get("decree_seq", "?")

        # LLM path — try the LLM first, fall back on any exception.
        if self.llm_adapter is not None:
            prompt = (
                f"The intent '{original_description}' was blocked by "
                f"decree #{seq} ({matched_term}). Suggest an alternative "
                f"that avoids '{matched_term}'."
            )
            try:
                adapted = self._call_llm(prompt)
                if adapted and isinstance(adapted, str) and adapted.strip():
                    adapted = adapted.strip()
                    # Safety net: if the LLM ignored the instruction and
                    # still produced a description containing the
                    # matched_term, apply simple replacement on top of
                    # the LLM output. The decree is supreme — we cannot
                    # ship a description that still violates it.
                    if matched_term and re.search(
                        re.escape(matched_term), adapted, re.IGNORECASE
                    ):
                        adapted = self._simple_adapt(adapted, matched_term)
                    return adapted
            except Exception:
                # LLM failed — fall through to simple replacement.
                # Per ADR-0006 (falsifiable self-properties): honest
                # failure, never silent violation of the decree.
                pass

        # No-LLM path (or LLM failed).
        return self._simple_adapt(original_description, matched_term)

    def propose_with_adaptation(
        self,
        description: str,
        operation: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Try original → if blocked → adapt → try adapted → up to max_retries.

        Per ADR-0033. The agent's full adaptation loop: it keeps
        trying until either (a) an adapted description passes the
        decree gate, (b) `max_retries` is exhausted, or (c) adaptation
        produces no change (the simple replacement can't help further).

        Args:
            description: initial description.
            operation: operation to perform.
            payload: optional payload dict.
            max_retries: maximum number of `propose()` calls to make.
                Default 3 (enough for typical multi-term prohibitions,
                low enough to bound runtime).

        Returns:
            The final `propose()` result, enriched with:
            - "adaptation_history": list of {attempt, description,
              blocked, state, violations, adaptations} per iteration
            - "attempts": int — number of `propose()` calls actually
              made (1 if the original passed first try, up to max_retries)
            - "final_description": the description that finally passed
              (or the last one tried if all blocked)
            - "reason": present only if the loop exited without success
              ("adaptation produced no change" | "max_retries exhausted")
        """
        history: List[Dict[str, Any]] = []
        current_description = description
        last_result: Optional[Dict[str, Any]] = None
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            result = self.propose(current_description, operation, payload)
            history.append({
                "attempt": attempt,
                "description": current_description,
                "blocked": result["blocked"],
                "state": result["state"],
                "violations": result["violations"],
                "adaptations": result["adaptations"],
            })
            last_result = result

            if not result["blocked"]:
                # Success — return with full history.
                return {
                    **result,
                    "adaptation_history": history,
                    "attempts": attempt,
                    "final_description": current_description,
                }

            # Blocked — adapt for the next iteration.
            adapted = result["adaptations"][0] if result["adaptations"] else ""
            if not adapted or adapted.strip() == current_description.strip():
                # Adaptation produced no change — can't make progress.
                # Don't loop forever; return last result.
                return {
                    **result,
                    "adaptation_history": history,
                    "attempts": attempt,
                    "final_description": current_description,
                    "reason": "adaptation produced no change",
                }
            current_description = adapted

        # Exhausted retries — return last result with failure reason.
        return {
            "state": last_result["state"] if last_result else "DECREE_BLOCKED",
            "blocked": True,
            "violations": last_result["violations"] if last_result else [],
            "adaptations": last_result["adaptations"] if last_result else [],
            "adaptation_history": history,
            "attempts": attempt,
            "final_description": current_description,
            "reason": "max_retries exhausted",
        }

    # ─── Internal helpers ───────────────────────────────────────────

    def _build_request(
        self,
        description: str,
        operation: str,
        payload: Optional[Dict[str, Any]],
    ) -> IntentRequest:
        """Build an IntentRequest with a unique id and intent_id.

        Per ADR-0024 — JSON-RPC 2.0 style request with description,
        operation, payload in params.
        """
        self._req_counter += 1
        req_id = f"decree-aware-{self.agent_id}-{self._req_counter}"
        intent_id = f"intent-{int(time.time() * 1000)}-{self._req_counter}"
        return IntentRequest(
            id=req_id,
            params={
                "intent_id": intent_id,
                "description": description,
                "operation": operation,
                "payload": payload or {},
            },
        )

    def _extract_violation(self, response) -> Dict[str, Any]:
        """Pull a clean violation record from a DECREE_BLOCK response.

        AgentMesh.send() returns an IntentResponse with .error.data on
        block (per ADR-0024). We pull out the decree-specific fields and
        preserve the full block_message + all_violations for audit.
        """
        data: Dict[str, Any] = {}
        if response.error is not None:
            data = getattr(response.error, "data", {}) or {}
        return {
            "decree_seq": data.get("decree_seq"),
            "decree_text": data.get("decree_text"),
            "matched_term": data.get("matched_term"),
            "violation": data.get("violation"),
            "block_message": response.error.message if response.error else "",
            "all_violations": data.get("all_violations", []),
        }

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM adapter with the given prompt.

        Supports three adapter shapes (in priority order):
            - object with `.generate(prompt: str) -> str` method
              (e.g. a hypothetical LLMLocalAdapter wrapper)
            - object with `.answer(prompt: str) -> str` method
            - object with `.respond(prompt: str) -> str` method
            - plain callable `(prompt: str) -> str`

        Raises TypeError if the adapter matches none of the above
        (caught by `adapt()`, which then falls back to simple
        replacement).
        """
        adapter = self.llm_adapter
        if adapter is None:
            raise TypeError("llm_adapter is None")
        # Prefer named methods when present (covers adapter objects).
        for method_name in ("generate", "answer", "respond"):
            method = getattr(adapter, method_name, None)
            if callable(method):
                return method(prompt)
        # Fall back to direct call (adapter is a plain callable).
        if callable(adapter):
            return adapter(prompt)
        raise TypeError(
            f"Unsupported llm_adapter type: {type(adapter).__name__} — "
            f"expected callable or object with .generate/.answer/.respond"
        )

    @staticmethod
    def _simple_adapt(description: str, matched_term: str) -> str:
        """No-LLM fallback: remove the matched term, substitute a placeholder.

        If the entire description was the matched term, return a generic
        compliant alternative. The placeholder is intentionally generic
        ('[redacted]') rather than a specific synonym — without an LLM
        we don't know what the user meant, so we preserve sentence
        structure but mark the prohibited slot. Downstream consumers
        can recognize '[redacted]' and ask the human for clarification
        if needed.
        """
        if not matched_term:
            return description
        pattern = re.compile(re.escape(matched_term), re.IGNORECASE)
        cleaned = pattern.sub("[redacted]", description).strip()
        # Collapse whitespace left by the substitution (e.g. double spaces
        # where the matched_term had surrounding spaces).
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # If the entire description was the matched term, the result is
        # just "[redacted]" — not a useful intent. Return a generic one.
        if not cleaned or cleaned == "[redacted]":
            return "perform a compliant alternative action"
        return cleaned
