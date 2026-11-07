"""runtime/tests/test_fuzz_parsers.py — mutation fuzzing of parser entry points (stdlib-only).

Falsifiable property (канон ADR-0006): security-sensitive парсеры не должны
падать неуправляемыми исключениями на произвольном входе. Контролируемые исходы:
SchemaError / AgentCardError / ValueError / TypeError / документированный
возврат значения. Запрещённые: RecursionError, AssertionError, MemoryError,
PermissionError, sqlite3.Error из глубины стека.

Поверхности:
  1. schema_validate.validate(value, schema)     — произвольные value+schema;
  2. AgentCard.from_dict(data)                   — произвольный dict (внешний JSON);
  3. ConversationalDecreeInterface.translate     — произвольный текст + сломанный
     LLM-адаптер (канон ADR-0006: сломанный LLM не роняет интерфейс).

Детерминизм: фиксированный seed → одна и та же серия мутаций на каждом прогоне
(канон verify 33/33 — тесты не флейкуют). Stdlib-only: канон «нулевые внешние
зависимости» runtime/.
"""
import json
import random
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import schema_validate
from agent_card import AgentCard, AgentCardError
from conversational_decree import ConversationalDecreeInterface
from decree_log import DecreeLog

SEED = 20261107  # дата кристаллизации фазз-волны — детерминизм прогона
ITERATIONS = 400
FORBIDDEN = (RecursionError, AssertionError, MemoryError, PermissionError, sqlite3.Error)

_ALPHABET = (
    "abcXYZ019 ,.:;()[]{}<>\"'`\\/*+-=~!@#$%^&|?_"
    "\n\r\t\x00\x0b\x1b\u00e9\u044f\u4e2d\u2028\ud83d\ude00"
    "%s%n%d{}"  # форматные инъекции
    "{'a':1}\"key\""  # обрывки JSON/Python-литералов
)

_DECREE_WORDS = (
    "never use Google anymore", "always", "prohibit", "allow", "", " ",
    "I don't want to", "запретить", "!!!!", "law of gravity", "permission to",
    "decree #123", "\x00\x01", "a" * 300, "CREATE TABLE x (v)",
)


def _mut_string(rng: random.Random, base: str = "") -> str:
    """Мутатор строк: вставки/удаления/дубли/инъекции из алфавита-помоек."""
    s = list(base or "")
    for _ in range(rng.randint(1, 5)):
        op = rng.randint(0, 3)
        pos = rng.randint(0, max(0, len(s)))
        if op == 0:
            s.insert(pos, rng.choice(_ALPHABET))
        elif op == 1 and s:
            del s[rng.randint(0, len(s) - 1)]
        elif op == 2:
            chunk = "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 12)))
            s[pos:pos] = list(chunk)
        else:
            s = s[:pos]
    return "".join(s)


def _json_value(rng: random.Random, depth: int = 0):
    """Генератор произвольных JSON-совместимых структур (мусорных по смыслу)."""
    r = rng.random()
    if depth > 5 or r < 0.35:
        return rng.choice([None, True, False, rng.randint(-10**12, 10**12),
                           rng.uniform(-1e9, 1e9), _mut_string(rng),
                           "", rng.choice(_DECREE_WORDS)])
    if r < 0.7:
        return {(_mut_string(rng) or f"k{rng.randint(0, 50)}"): _json_value(rng, depth + 1)
                for _ in range(rng.randint(0, 6))}
    return [_json_value(rng, depth + 1) for _ in range(rng.randint(0, 6))]


class SchemaValidateFuzzTests(unittest.TestCase):
    """validate(value, schema) на произвольных входах: только SchemaError/список."""

    def test_validate_never_uncontrolled_crash(self):
        rng = random.Random(SEED)
        for _ in range(ITERATIONS):
            schema = _json_value(rng)
            value = _json_value(rng)
            try:
                errors = schema_validate.validate(value, schema)
            except schema_validate.SchemaError:
                continue  # контролируемый исход: unsupported keyword / неверный тип схемы
            except FORBIDDEN as e:
                self.fail(f"uncontrolled crash: {type(e).__name__}: {e} "
                          f"on schema={schema!r:.200} value={value!r:.200}")
            except (ValueError, TypeError, KeyError):
                continue  # контрактные ошибки типа аргументов
            self.assertIsInstance(errors, list, f"not a list for schema={schema!r:.200}")

    def test_deeply_nested_value_no_recursion(self):
        rng = random.Random(SEED + 1)
        deep: dict = {}
        node = deep
        for _ in range(2000):
            node["k"] = {}
            node = node["k"]
        schema = {"type": "object"}
        try:
            schema_validate.validate(deep, schema)  # рекурсия по СХЕМЕ, не по значению
        except FORBIDDEN as e:
            self.fail(f"deep value caused {type(e).__name__}")


class AgentCardFuzzTests(unittest.TestCase):
    """AgentCard.from_dict на произвольных dict: только AgentCardError/возврат карты."""

    def test_from_dict_never_uncontrolled_crash(self):
        rng = random.Random(SEED + 2)
        base = {"id": "a1", "name": "agent", "version": "1.0.0", "capabilities": ["c1"]}
        for _ in range(ITERATIONS):
            data = _json_value(rng)
            if rng.random() < 0.4 and isinstance(data, dict):
                data = {**data, **base}  # полумусор: почти-валидная карта с сюрпризами
            try:
                AgentCard.from_dict(data)
            except (AgentCardError, ValueError, KeyError, TypeError):
                continue  # контролируемые исходы
            except FORBIDDEN as e:
                self.fail(f"uncontrolled crash: {type(e).__name__}: {e} on data={data!r:.200}")


class ConversationalDecreeFuzzTests(unittest.TestCase):
    """translate на мусорном тексте со сломанным LLM: fallback обязан спасать (ADR-0006)."""

    def _fresh_interface(self, tmpdir: str, adapter):
        return ConversationalDecreeInterface(
            decree_log=DecreeLog(str(Path(tmpdir) / "fuzz_decrees.db")),
            llm_adapter=adapter,
        )

    def test_translate_broken_llm_never_uncontrolled_crash(self):
        rng = random.Random(SEED + 3)

        def broken_llm(_prompt: str) -> str:
            r = rng.random()
            if r < 0.3:
                raise RuntimeError("LLM exploded")  # адаптер падает — fallback спасает
            if r < 0.6:
                return _mut_string(rng)  # мусор вместо JSON
            return rng.choice(["null", "[]", '{"text": 1}', '["not","an","object"]',
                               '{"text": "ok", "category": 123}', ""])

        with tempfile.TemporaryDirectory() as tmp:
            it = self._fresh_interface(tmp, broken_llm)
            for _ in range(200):
                text = _mut_string(rng, rng.choice(_DECREE_WORDS))
                try:
                    it.issue_from_nl(text)
                except (ValueError, TypeError, KeyError):
                    continue  # контрактные ошибки интерфейса
                except FORBIDDEN as e:
                    self.fail(f"uncontrolled crash: {type(e).__name__}: {e} on text={text!r:.120}")

    def test_translate_rule_based_only_never_uncontrolled_crash(self):
        rng = random.Random(SEED + 4)
        with tempfile.TemporaryDirectory() as tmp:
            it = self._fresh_interface(tmp, None)
            for _ in range(200):
                text = _mut_string(rng, rng.choice(_DECREE_WORDS))
                try:
                    it.issue_from_nl(text)
                except (ValueError, TypeError, KeyError):
                    continue
                except FORBIDDEN as e:
                    self.fail(f"uncontrolled crash: {type(e).__name__}: {e} on text={text!r:.120}")


if __name__ == "__main__":
    unittest.main()
