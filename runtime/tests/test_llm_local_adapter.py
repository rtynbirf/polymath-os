"""runtime/tests/test_llm_local_adapter.py — Tests for the FIRST real
SINGULYAR EIR consumer (Gate-3, ADR-0012 Layer 5 integration).

Verifies that LLMLocalAdapter:
  - Implements Adapter contract (execute + read_state → Observation)
  - Honors tri-state Observation (PRESENT/ABSENT/UNAVAILABLE)
  - Rule-layer fallback works without LLM weights
  - Free-speech returns NotExecuted when no model (per ADR-007)
  - Idempotency: same key → cached response (no double execute)
  - S15 contract: sibling key in cache doesn't pollute absent key's read_state
  - Capabilities declared: 4 (llm.command/check_status/answer/generate)
"""

import os, sys, unittest, tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_SRC_ADAPTERS = _SRC / "adapters"
if str(_SRC_ADAPTERS) not in sys.path:
    sys.path.insert(0, str(_SRC_ADAPTERS))

from singulyar_runtime import (
    Intent, Capability, Observation, State,
    PRESENT, ABSENT, UNAVAILABLE,
    NotExecuted, Runtime, Policy,
)
from adapters.llm_local_adapter import (
    LLMLocalAdapter, CAPABILITIES, ADAPTER_ID, RULES_VERSION,
    default_adapter, default_capabilities,
)
from adapters import rule_layer


class LLMLocalAdapterTests(unittest.TestCase):

    def _make_intent(self, phrase="пинг", iid="test-1", operation="execute_command"):
        return Intent(
            intent_id=iid,
            description=f"voice command: {phrase}",
            operation=operation,
            payload={"phrase": phrase},
            expected={},  # rule-layer response is non-deterministic in content; we just expect an effect to be recorded
        )

    def test_adapter_id_constant(self):
        self.assertEqual(ADAPTER_ID, "llm.local")

    def test_capabilities_count_and_fields(self):
        caps = CAPABILITIES
        self.assertEqual(len(caps), 4)
        for c in caps:
            self.assertEqual(c.adapter_id, ADAPTER_ID)
            self.assertTrue(c.offline, "all capabilities must be offline=True (sovereign core per ADR-0002)")
            self.assertTrue(c.local_only, "all capabilities must be local_only=True (data doesn't leave device)")
            self.assertTrue(c.idempotent, "all capabilities must be idempotent=True (safe retry per ADR-007)")

    def test_default_adapter_unavailable_state(self):
        ad = default_adapter()
        st = ad.status()
        self.assertEqual(st["state"], "UNAVAILABLE")
        self.assertIn("не загружены", st["reason"])
        self.assertEqual(st["rules_version"], RULES_VERSION)

    def test_rule_layer_ping(self):
        ad = default_adapter()
        intent = self._make_intent(phrase="пинг", iid="ping-1")
        result = ad.execute(intent, "ping-1")
        self.assertEqual(result, "понг")
        # Idempotency: same key returns cached
        result2 = ad.execute(intent, "ping-1")
        self.assertEqual(result2, "понг")
        self.assertEqual(ad.calls(), 1, "idempotent: only 1 execute() call")

    def test_rule_layer_open_with_arg(self):
        ad = default_adapter()
        intent = self._make_intent(phrase="открой зал", iid="open-hall-1")
        result = ad.execute(intent, "open-hall-1")
        self.assertEqual(result, "открываю зал")

    def test_rule_layer_identity(self):
        ad = default_adapter()
        intent = self._make_intent(phrase="кто ты", iid="identity-1")
        result = ad.execute(intent, "identity-1")
        self.assertIn("СИНГУЛЯРА", result)
        self.assertIn("РВУЛСОН" if False else "РУВСОН", result)

    def test_read_state_present_after_execute(self):
        ad = default_adapter()
        intent = self._make_intent(phrase="стоп", iid="stop-1")
        ad.execute(intent, "stop-1")
        obs = ad.read_state(intent, "stop-1")
        self.assertEqual(obs.status, PRESENT)
        self.assertEqual(obs.count, 1)
        self.assertEqual(obs.value["via"], "rule-layer")

    def test_read_state_absent_for_never_executed_key(self):
        ad = default_adapter()
        intent = self._make_intent(phrase="пинг", iid="never-run-1")
        # No execute() called for "never-run-1"
        obs = ad.read_state(intent, "never-run-1")
        self.assertEqual(obs.status, ABSENT)
        self.assertEqual(obs.count, 0)

    def test_s15_partial_cache_miss_does_not_pollute_sibling(self):
        """ADR-0010 S15 (cross-check with test_durability):
        Sibling key in cache does NOT cause absent key to return PRESENT."""
        ad = default_adapter()
        # Pre-populate sibling key via direct execute
        sibling_intent = self._make_intent(phrase="пинг", iid="sibling")
        ad.execute(sibling_intent, "sibling-key")
        self.assertEqual(ad.cache_size(), 1)

        # Query ABSENT key
        absent_intent = self._make_intent(phrase="стоп", iid="absent")
        obs = ad.read_state(absent_intent, "absent-key")
        self.assertEqual(obs.status, ABSENT, "absent key MUST NOT infer PRESENT from sibling")
        self.assertEqual(obs.count, 0)

        # And sibling still PRESENT
        obs = ad.read_state(sibling_intent, "sibling-key")
        self.assertEqual(obs.status, PRESENT)
        self.assertEqual(obs.count, 1)

    def test_free_speech_without_model_raises_not_executed(self):
        """Per ADR-007: free speech (no rule-layer match) + no LLM = NotExecuted.
        Kernel treats as no-effect, can fail over to other adapters or
        WAITING_FOR_HUMAN. MUST NOT hallucinate."""
        ad = default_adapter()
        # Free speech — phrase that doesn't match any rule-layer pattern
        intent = self._make_intent(phrase="расскажи мне про концепцию эмерджентности", iid="free-1")
        with self.assertRaises(NotExecuted) as ctx:
            ad.execute(intent, "free-1")
        self.assertIn("rule-layer no match", str(ctx.exception))
        self.assertIn("model not loaded", str(ctx.exception))

    def test_load_model_without_llama_cpp_raises(self):
        """If llama-cpp-python not installed, load_model() fails honestly
        (RuntimeError, not silent success). Rule-layer still works after."""
        ad = default_adapter()
        from adapters.llm_local_adapter import _HAS_LLAMA_CPP
        if _HAS_LLAMA_CPP:
            self.skipTest("llama-cpp-python installed; can't test failure path")
        with self.assertRaises(RuntimeError) as ctx:
            ad.load_model("/nonexistent/model.gguf")
        self.assertIn("llama-cpp-python not installed", str(ctx.exception))
        # State remains not_loaded
        self.assertEqual(ad._state, "not_loaded")
        # But rule-layer still works
        intent = self._make_intent(phrase="пинг", iid="post-fail-1")
        self.assertEqual(ad.execute(intent, "post-fail-1"), "понг")


class RuleLayerTests(unittest.TestCase):
    """Tests for the rule-layer deterministic fallback."""

    def test_parse_ping(self):
        result = rule_layer.parse("пинг")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "ping")

    def test_parse_open_with_arg(self):
        result = rule_layer.parse("открой зал")
        self.assertEqual(result, ("open", "зал"))

    def test_parse_send_with_arg(self):
        result = rule_layer.parse("отправь: привет миру")
        self.assertEqual(result, ("send", "привет миру"))

    def test_parse_free_speech_returns_none(self):
        self.assertIsNone(rule_layer.parse("расскажи про эмерджентность"))

    def test_execute_ping(self):
        result = rule_layer.execute("пинг")
        self.assertEqual(result["intent"], "ping")
        self.assertEqual(result["response"], "понг")
        self.assertEqual(result["via"], "rule-layer")

    def test_execute_unknown_returns_none(self):
        self.assertIsNone(rule_layer.execute("абракадабра"))


class IntegrationWithRuntimeTests(unittest.TestCase):
    """End-to-end: LLMLocalAdapter wired into Runtime — first real consumer
    of the SINGULYAR EIR kernel (per ADR-0012 Layer 5)."""

    def _make_caps(self):
        return list(CAPABILITIES)

    def test_runtime_with_llm_local_adapter_command(self):
        """Execute a known command via the full Runtime → LLMLocalAdapter path."""
        ad = default_adapter()
        caps = self._make_caps()
        rt = Runtime(caps, [ad], Policy({"execute_command", "answer_question", "generate_response", "check_status"}))
        intent = Intent(
            intent_id="rt-ping-1",
            description="voice command: пинг",
            operation="execute_command",
            payload={"phrase": "пинг"},
            expected={},  # any rule-layer effect = PASS
        )
        st = rt.run(intent)
        self.assertEqual(st, State.CONFIRMED,
                         "rule-layer match → effect recorded → CONFIRMED")

    def test_runtime_with_llm_local_adapter_free_speech_unknown(self):
        """Free speech + no model → NotExecuted → no failover (only one adapter)
        → kernel reports WAITING_FOR_HUMAN or UNKNOWN. MUST NOT be CONFIRMED."""
        ad = default_adapter()
        caps = self._make_caps()
        rt = Runtime(caps, [ad], Policy({"execute_command", "answer_question", "generate_response", "check_status"}))
        intent = Intent(
            intent_id="rt-free-1",
            description="free speech: расскажи про эмерджентность",
            operation="answer_question",
            payload={"phrase": "расскажи про эмерджентность"},
            expected={},
        )
        st = rt.run(intent)
        self.assertIn(st, {State.WAITING_FOR_HUMAN, State.UNKNOWN, State.FAILED},
                      f"free-speech without model MUST NOT be CONFIRMED — got {st}")

    def test_runtime_with_llm_local_adapter_idempotency(self):
        """Idempotency at adapter level: same idempotency_key called twice
        via direct adapter.execute() → only ONE real execute (cache hit on 2nd).
        (Runtime doesn't allow re-run with same intent_id; that's a separate
        invariant — kernel-level idempotency. This test is adapter-level.)"""
        ad = default_adapter()
        intent = Intent(
            intent_id="rt-idem-1",
            description="voice command: пинг",
            operation="execute_command",
            payload={"phrase": "пинг"},
            expected={},
        )
        # First call — real execute, caches response
        result1 = ad.execute(intent, "key-1")
        self.assertEqual(result1, "понг")
        self.assertEqual(ad.calls(), 1)
        # Second call with same idempotency_key — cache hit, no real execute
        result2 = ad.execute(intent, "key-1")
        self.assertEqual(result2, "понг")
        self.assertEqual(ad.calls(), 1, "cache hit MUST NOT increment _calls")
        # Verify cached state
        obs = ad.read_state(intent, "key-1")
        self.assertEqual(obs.status, PRESENT)


if __name__ == "__main__":
    unittest.main()
