"""runtime/src/adapters/rule_layer.py — deterministic rule-layer
(Python port of singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs ·создатьПравилоСлой).

The rule-layer matches an input phrase against a known command dictionary
and executes a deterministic action — no LLM weights required. This is
the offline fallback that lets the platform respond to voice commands
even on a weak machine without GPU/wllama.

In the original singulyar (·21 ОБЩЕНИЕ), 14 intents are supported:
  send / read / clear / clear_field / read_log / status / help / stop /
  load_model / open / repeat / ping / count / identity

This Python port implements a subset suitable for the EIR kernel
(doesn't require a browser; pure stdlib). The intent parser is a simple
regex-based router — same semantics as the JS version, no NLP.

Per ADR-0010 §3: rule-layer is test scaffolding for the LLM adapter
— not production code per se — but it's load-bearing for the SINGULYAR
kernel (without it, no offline fallback exists). NOT marked as
'# pragma: no mutate' because it's a real consumer of the kernel.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Source: singulyar-llm/ОБУЧЕНИЕ/ПРИМЕРЫ_КОМАНД.jsonl (v0.6, 142 phrases → 19 intents)
# Python port: simplified to 14 intents that don't require browser APIs
KNOWN_INTENTS: Dict[str, List[str]] = {
    "ping":          [r"^пинг$", r"^ping$"],
    "stop":          [r"^стоп$", r"^замолчи$", r"^stop$"],
    "status":        [r"^статус$", r"^какие каналы работают$"],
    "identity":      [r"^кто ты$", r"^who are you$"],
    "count":         [r"^сколько команд ты знаешь$", r"^count$"],
    "help":          [r"^что ты умеешь$", r"^помощь$", r"^help$"],
    "read_log":      [r"^прочитай журнал$", r"^read log$"],
    "clear":         [r"^очисти журнал$", r"^clear$"],
    "clear_field":   [r"^сотри текст из поля$", r"^clear field$"],
    "load_model":    [r"^загрузи модель$", r"^load model$"],
    "ping_2":        [r"^пинг(\s|$)"],
}

# Intent → deterministic response (no external state, no LLM, pure function)
RESPONSES: Dict[str, str] = {
    "ping":          "понг",
    "stop":          "",  # no speech output, side-effect only
    "status":        "модель не загружена; правило-слой работает",
    "identity":      "я локальный голос СИНГУЛЯРА — маленькая модель в браузере, работаю по правилам РУВСОН",
    "count":         "знаю 14 команд: пинг, стоп, статус, кто ты, сколько команд, помощь, прочитай журнал, очисти журнал, сотри текст, загрузи модель, открой, повтори, отправь, что такое",
    "help":          "команды: пинг, стоп, статус, кто ты, помощь, прочитай журнал, очисти журнал, открой зал/суфлёр/связь, повтори: текст, отправь: текст",
    "read_log":      "журнал пуст",
    "clear":         "журнал очищен",
    "clear_field":   "поле сообщения очищено",
    "load_model":    "загрузка модели недоступна в этом окружении (Python-порт; wllama — браузерная вещь)",
    "ping_2":        "понг",
}

# Intent → side effect that may modify a passed executor object (None = no-op)
# In singulyar, this is испектор (send/read/clear/etc). For Python port,
# we just record intents — no browser, no UI to act on.
SIDE_EFFECTS: Dict[str, str] = {
    "send":          "записано в поле сообщения",
    "read":          "прочитано из поля",
    "clear":         "журнал очищен",
    "clear_field":   "поле очищено",
    "read_log":      "журнал прочитан",
    "stop":          "стоп сигнал отправлен",
    "load_model":    "команда загрузки модели",
}


def parse(phrase: str) -> Optional[Tuple[str, str]]:
    """Match a phrase against KNOWN_INTENTS regex dictionary.

    Returns (intent, text) tuple where text is the captured argument
    (e.g. for "открой зал" → ('open', 'зал')), or None if no match.

    Mirrors singulyar/llm.mjs разобрать() semantics:
    - First exact match (r"^...$") wins
    - Then prefix matches (with arg capture)
    - Returns None for free speech (LLM territory)
    """
    if not phrase or not isinstance(phrase, str):
        return None
    p = phrase.strip().lower()

    # Exact matches first
    for intent, patterns in KNOWN_INTENTS.items():
        for pat in patterns:
            if re.match(pat, p):
                return (intent, "")

    # Argument-capturing intents (prefix + arg)
    # Pattern: "открой X", "повтори X", "отправь X", "что такое X"
    arg_patterns = [
        (r"^открой\s+(.+)$",   "open"),
        (r"^open\s+(.+)$",     "open"),
        (r"^повтори:\s*(.+)$", "repeat"),
        (r"^repeat:\s*(.+)$",  "repeat"),
        (r"^повтори\s+(.+)$",  "repeat"),
        (r"^отправи:\s*(.+)$", "send"),
        (r"^отправь:\s*(.+)$", "send"),
        (r"^send:\s*(.+)$",    "send"),
        (r"^что такое\s+(.+)$", "what"),
        (r"^what is\s+(.+)$",   "what"),
    ]
    for pat, intent in arg_patterns:
        m = re.match(pat, p)
        if m:
            return (intent, m.group(1).strip())

    return None  # free speech — falls through to LLM (if loaded) or "не знаю"


def execute(phrase: str) -> Optional[Dict[str, Any]]:
    """Try to execute a phrase via the rule-layer.

    Returns:
      {"intent": str, "arg": str, "response": str, "via": "rule-layer"}
      or None if no match (free speech → LLM territory).

    This is the Python equivalent of singulyar's ruleLayer.исполнить().
    Side-effects (like 'clear' / 'send') are recorded but don't actually
    mutate any state — the Python port is a stub executor.
    """
    parsed = parse(phrase)
    if parsed is None:
        return None
    intent, arg = parsed
    response = RESPONSES.get(intent, "")
    # For argument-taking intents, format the response with the arg
    if intent == "open":
        response = f"открываю {arg}"
    elif intent == "repeat":
        response = arg  # echo back what to repeat
    elif intent == "send":
        response = f"отправлено: {arg}"
    elif intent == "what":
        response = f"не знаю, что такое {arg}"  # honest — no LLM

    return {
        "intent": intent,
        "arg": arg,
        "response": response,
        "via": "rule-layer",  # honest marker: this came from rule-layer, not LLM
    }


def intent_count() -> int:
    """Return the number of distinct intents the rule-layer can handle."""
    all_intents = set(KNOWN_INTENTS.keys()) | {"open", "repeat", "send", "what"}
    return len(all_intents)
