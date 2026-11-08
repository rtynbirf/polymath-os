"""runtime/tests/test_llm_local_adapter_integration.py — Real LLM weights
integration test (Gate-6, LIMITATIONS.md item 8 closure).

This test SKIPS unless the env var LLM_MODEL_PATH is set to a real GGUF
file path. If set, loads Qwen2.5-0.5B-Instruct via llama-cpp-python
and verifies that LLMLocalAdapter reaches READY state and produces a
real LLM response (not rule-layer cached).

Per ADR-0002 Tier 2: llama-cpp-python is optional (replaceable by
ctransformers or transformers). Per LIMITATIONS.md item 8: "ИИ-моделей нет"
— this test closes that gap when explicitly enabled.
"""

import os, sys, unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_SRC_ADAPTERS = _SRC / "adapters"
if str(_SRC_ADAPTERS) not in sys.path:
    sys.path.insert(0, str(_SRC_ADAPTERS))

from singulyar_runtime import Intent, Capability, State
from adapters.llm_local_adapter import LLMLocalAdapter, CAPABILITIES
from adapters.llm_local_adapter import _HAS_LLAMA_CPP

MODEL_PATH = os.environ.get("LLM_MODEL_PATH", "")
RUN_INTEGRATION = bool(MODEL_PATH) and _HAS_LLAMA_CPP


@unittest.skipUnless(RUN_INTEGRATION, "LLM_MODEL_PATH env var not set or llama-cpp-python not installed")
class RealLLMIntegrationTests(unittest.TestCase):
    """Run only when LLM_MODEL_PATH env var points to a real GGUF file.

    To run locally:
        export LLM_MODEL_PATH=/path/to/qwen2.5-0.5b-instruct-q4_k_m.gguf
        pip install llama-cpp-python
        cd runtime && python3 -m unittest tests.test_llm_local_adapter_integration -v
    """

    @classmethod
    def setUpClass(cls):
        cls.adapter = LLMLocalAdapter(model_path=MODEL_PATH)
        cls.adapter.load_model(MODEL_PATH)

    def test_load_model_reaches_ready_state(self):
        st = self.adapter.status()
        self.assertEqual(st["state"], "READY")
        self.assertNotIn("не загружены", st.get("reason", ""))

    def test_free_speech_gets_llm_response_not_not_executed(self):
        """Per ADR-0007: free speech + LLM loaded → real response (not NotExecuted).

        With rule-layer-only (no weights), free speech raises NotExecuted.
        With real weights loaded, the LLM produces a response and stores it
        in the cache (read_state returns PRESENT)."""
        intent = Intent(
            intent_id="real-llm-1",
            description="free speech: расскажи коротко про СИНГУЛЯР",
            operation="answer_question",
            payload={"phrase": "расскажи коротко про СИНГУЛЯР"},
            expected={},
        )
        result = self.adapter.execute(intent, "real-llm-key-1")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0, "LLM must produce non-empty response")
        # Verify cached
        obs = self.adapter.read_state(intent, "real-llm-key-1")
        self.assertEqual(obs.status, "PRESENT")
        self.assertEqual(obs.value["via"], "llm.local",
                         "via marker must show llm.local (not rule-layer) for free speech")

    def test_rule_layer_command_still_works_alongside_llm(self):
        """Rule-layer commands (ping) still work — they short-circuit before LLM."""
        intent = Intent(
            intent_id="rule-ping-1",
            description="voice command: пинг",
            operation="execute_command",
            payload={"phrase": "пинг"},
            expected={},
        )
        result = self.adapter.execute(intent, "rule-ping-key-1")
        self.assertEqual(result, "понг")
        obs = self.adapter.read_state(intent, "rule-ping-key-1")
        self.assertEqual(obs.value["via"], "rule-layer",
                         "rule-layer match must NOT invoke LLM")


if __name__ == "__main__":
    unittest.main()
