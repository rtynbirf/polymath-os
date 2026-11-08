"""runtime/tests/test_agent_card.py — Tests for Agent Card Protocol (ADR-0023)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_card import (
    AgentCard, AgentCardError, AgentEndpoint,
    SINGULYAR_EIR_CARD, POLYMATH_OS_BROWSER_CARD, CELL65_LLM_CARD,
    ALL_DEFAULT_CARDS,
)


class AgentCardValidationTests(unittest.TestCase):
    def test_valid_card_construction(self):
        c = AgentCard(
            id="test-agent.local",
            name="Test Agent",
            description="Test description",
            version="v0.1",
            capabilities=["test.op"],
        )
        self.assertEqual(c.id, "test-agent.local")
        self.assertEqual(c.decree_scope, "all")  # default
        self.assertEqual(c.license, "MIT")  # default

    def test_invalid_id_rejected(self):
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="UPPER-CASE",  # uppercase not allowed
                name="x", description="x", version="v0.1",
                capabilities=["x.op"]
            )
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="space in id",  # spaces not allowed
                name="x", description="x", version="v0.1",
                capabilities=["x.op"]
            )
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="",  # empty not allowed
                name="x", description="x", version="v0.1",
                capabilities=["x.op"]
            )

    def test_missing_required_field_rejected(self):
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="x.local",
                name="",  # empty name
                description="x", version="v0.1", capabilities=["x.op"]
            )
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="x.local",
                name="x", description="x", version="v0.1",
                capabilities=[]  # empty capabilities
            )

    def test_invalid_endpoint_type_rejected(self):
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="x.local",
                name="x", description="x", version="v0.1",
                capabilities=["x.op"],
                endpoints=[AgentEndpoint(type="carrier-pigeon", url="...")],
            )

    def test_decree_scope_default_all(self):
        c = AgentCard(
            id="x.local", name="x", description="x",
            version="v0.1", capabilities=["x.op"],
        )
        self.assertEqual(c.decree_scope, "all")

    def test_decree_scope_custom(self):
        c = AgentCard(
            id="x.local", name="x", description="x",
            version="v0.1", capabilities=["x.op"],
            decree_scope="singulyar",
        )
        self.assertEqual(c.decree_scope, "singulyar")

    def test_empty_decree_scope_rejected(self):
        with self.assertRaises(AgentCardError):
            AgentCard(
                id="x.local", name="x", description="x",
                version="v0.1", capabilities=["x.op"],
                decree_scope="",
            )


class AgentCardSerializationTests(unittest.TestCase):
    def test_to_json_and_back(self):
        original = SINGULYAR_EIR_CARD
        json_str = original.to_json()
        restored = AgentCard.from_json(json_str)
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.capabilities, original.capabilities)
        self.assertEqual(restored.decree_scope, original.decree_scope)

    def test_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            SINGULYAR_EIR_CARD.save_to_file(path)
            restored = AgentCard.from_file(path)
            self.assertEqual(restored.id, SINGULYAR_EIR_CARD.id)

    def test_invalid_json_rejected(self):
        with self.assertRaises(AgentCardError):
            AgentCard.from_json("{not valid json")
        with self.assertRaises(AgentCardError):
            AgentCard.from_json("[]")  # not a dict

    def test_missing_required_field_in_dict(self):
        with self.assertRaises(AgentCardError):
            AgentCard.from_dict({
                "id": "x.local",
                # missing name, description, version, capabilities
            })

    def test_extra_unknown_fields_ignored(self):
        """Forward-compatible — unknown fields don't fail validation."""
        data = SINGULYAR_EIR_CARD.to_dict()
        data["future_extension_field"] = "should not break"
        card = AgentCard.from_dict(data)
        self.assertEqual(card.id, SINGULYAR_EIR_CARD.id)


class DefaultAgentCardsTests(unittest.TestCase):
    def test_singulyar_eir_card_valid(self):
        self.assertEqual(SINGULYAR_EIR_CARD.id, "singulyar-eir.local")
        self.assertEqual(SINGULYAR_EIR_CARD.decree_scope, "all")
        self.assertIn("intent.execute", SINGULYAR_EIR_CARD.capabilities)

    def test_polymath_os_browser_card_valid(self):
        self.assertEqual(POLYMATH_OS_BROWSER_CARD.id, "polymath-os.browser")
        self.assertEqual(POLYMATH_OS_BROWSER_CARD.decree_scope, "polymath-os")

    def test_cell65_llm_card_valid(self):
        self.assertEqual(CELL65_LLM_CARD.id, "cell65-host.llm")
        self.assertEqual(CELL65_LLM_CARD.decree_scope, "singulyar")

    def test_all_default_cards_distinct_ids(self):
        ids = [c.id for c in ALL_DEFAULT_CARDS]
        self.assertEqual(len(ids), len(set(ids)), "default cards must have distinct ids")

    def test_all_default_cards_serializable(self):
        for card in ALL_DEFAULT_CARDS:
            json_str = card.to_json()
            restored = AgentCard.from_json(json_str)
            self.assertEqual(restored.id, card.id)


if __name__ == "__main__":
    unittest.main()
