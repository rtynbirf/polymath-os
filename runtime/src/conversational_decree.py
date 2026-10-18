"""runtime/src/conversational_decree.py — Conversational Decree Interface (ADR-0032).

A thin preprocessing layer that sits in front of `DecreeLog.issue()` and
accepts natural language. The human types raw speech ("I don't want to use
Google anymore") → the interface translates it to a formal decree
(`text="never use Google"`, `category="prohibition"`, `scope="all"`) →
issues it through the existing DecreeLog API → returns the decree record.

Per ADR-0032:
- The translator is a pure preprocessing layer — `DecreeLog` does not
  know that a decree came from natural language vs. from a hand-typed
  formal decree. The append-only hash-chained invariant (ADR-0021),
  supersession (ADR-0028), N-of-M multi-sig (ADR-0029 §6), time-limited
  decrees (v3.19.0), and NSA compartmentalization (ADR-0029 §7) all
  apply unchanged.
- Translation has two paths: (1) LLM path (preferred when an
  `llm_adapter` is supplied — duck-typed as a callable `(prompt) -> str`),
  and (2) rule-based path (always available — keyword detection with
  priority `prohibition > law > permission`, default `directive`).
- Per ADR-0006 (falsifiable properties): a broken LLM does not silently
  pass through — the translator degrades to the deterministic fallback
  rather than issuing a malformed decree.

Per MANIFESTO §2: PAROLE > LANGUE — the human's raw speech IS the law.
This interface re-casts the same meaning into the formal decree
vocabulary the kernel's `check_compliance` matcher expects, without
asking the human to learn that vocabulary first.

Canonical example (the one used by the ADR-0032 acceptance test):

    cdi = ConversationalDecreeInterface(decree_log=dl, llm_adapter=None)
    record = cdi.issue_from_nl("I don't want to use Google anymore")
    # → dl.issue(text="never use Google", category="prohibition", scope="all")
    # → record = {"seq": N, "category": "prohibition",
    #             "decree_text": "never use Google", ...}
    # Then: dl.check_compliance("configure DNS with Google 8.8.8.8")
    # → {"compliant": False, ...}  (the prohibition decree blocks it)
"""

import json
import re
from typing import Any, Callable, Dict, Optional


# ───────────────────────────────────────────────────────────────
# Rule-based keyword detection tables (ADR-0032 §Translation strategy).
#
# Priority order: prohibition > law > permission. A false-positive
# prohibition is SAFER than a false-negative — the system errs toward
# respecting the human's No (per ADR-0009 default-deny philosophy).
#
# Triggers are matched as case-insensitive substrings (not word-boundary
# regexes) because the human's speech is messy: "Idon't want to..." with
# a missing apostrophe, "STOPUSING" all-caps, mixed-language "запретить
# use of Google" — substring match is more forgiving than \b...\b.
#
# Multi-word triggers include both English and Russian so the interface
# works regardless of which language the human is thinking in on a
# given day (per ПРАВИЛА_СИНГУЛЯРА rule 1: 'Отвечай на том языке, на
# котором задан вопрос').
# ───────────────────────────────────────────────────────────────

_PROHIBITION_TRIGGERS: tuple = (
    "don't want",        # "I don't want to use Google anymore"
    "do not want",       # formal contraction expansion
    "never",             # "never use AWS"
    "stop using",        # "stop using Cloudflare"
    "no more",           # "no more Chrome"
    "ban ",              # "ban Google" (trailing space avoids 'bank' false hit)
    "запретить",         # "запретить Google"
    "запрет",            # "запрет AWS"
)

_LAW_TRIGGERS: tuple = (
    "always",            # "always use local unbound"
    "обязательно",       # Russian 'must / obligatorily'
    "всегда",            # Russian 'always'
    "must ",             # "must pin MCP version" (trailing space avoids 'mustache')
)

_PERMISSION_TRIGGERS: tuple = (
    "allow ",            # "allow local unbound" (trailing space avoids 'allowance')
    "разрешить",         # Russian 'allow'
    "permission to",     # "permission to use WebRTC for P2P"
    "you may",           # "you may use llama-cpp"
)

# Default category when no trigger matches. Per ADR-0032 §Translation
# strategy: directive is the catch-all — the original text is echoed
# unchanged, and the kernel's check_compliance matcher treats directives
# as informational (no enforcement).
_DEFAULT_CATEGORY = "directive"

# Default scope in the rule-based path. Rule-based detection does not
# infer scope from natural language; scope refinement is left to the LLM
# path or to the human editing the formal decree directly. "all" is the
# safe default — a decree scoped to "all" applies at every scope in the
# v3.19.0 hierarchy (_SCOPE_HIERARCHY in decree_log.py).
_DEFAULT_SCOPE = "all"


# Regex that extracts the prohibited entity from a "use X" / "using X" /
# "install X" / ... phrase. Captures everything after the verb to the end
# of the input. Trailing filler words and punctuation are stripped in
# code (see _formalize_prohibition) — keeping the regex simple and the
# cleanup explicit makes the rule easier to mutation-test (ADR-0010).
#
# Case-insensitive (re.IGNORECASE) so "Use Google" and "use google" both
# work. The capture group preserves the ORIGINAL case of the entity —
# the formal decree "never use Google" keeps the capital G the human
# typed.
#
# Verb set mirrors _PROHIBITION_REGEX in decree_log.py L66-69 (the
# v0.6.1 set: use/using/adopt/deploy/install/run/rely on/send/share/
# transmit/expose) so the conversational translator and the kernel's
# own prohibition matcher agree on what counts as a 'prohibition verb'.
_PROHIBITION_VERB_RE = re.compile(
    r"\b(?:use|using|adopt|deploy|install|run|rely\s+on|send|share|transmit|expose)\s+(.+)$",
    re.IGNORECASE,
)

# Russian prohibition: "запретить <entity>" or "запретить использовать
# <entity>". The optional inner verb mirrors the English pattern.
_PROHIBITION_RU_RE = re.compile(
    r"\bзапретить(?:\s+(?:использовать|применять|ставить))?\s+(.+)$",
    re.IGNORECASE,
)

# Trailing filler words that humans append to prohibitions but that the
# formal decree does not need ("never use Google anymore" → "never use
# Google"). Word-boundary anchored at end-of-string ($).
_PROHIBITION_FILLER_RE = re.compile(
    r"\s+(?:anymore|any\s+more|again|ever|no\s+more|please|now|too|either)$",
    re.IGNORECASE,
)

# Punctuation to strip from the end of the extracted entity (so "use
# Google." → "Google"). Used after filler removal, twice, to handle
# "use Google anymore." → strip ".an" → no, actually the filler regex
# runs first and strips "anymore" (including the trailing period since
# `[.,;:!?]*$` is appended). Re-run punctuation strip AFTER filler strip
# in case the filler is followed by punctuation ("use Google, anymore!").
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!?]+$")


class ConversationalDecreeInterface:
    """Conversational front-end for `DecreeLog.issue()` (ADR-0032).

    The human types natural language → the interface translates it to a
    formal decree specification `{text, category, scope}` → issues it via
    the existing `DecreeLog.issue()` API → returns the decree record.

    The translator is stateless: it does not cache, does not persist,
    does not modify the decree log beyond what `DecreeLog.issue()` already
    does. The same translator instance can be reused across many NL
    inputs and across many DecreeLog instances (just construct a new
    interface per DecreeLog — `__init__` is cheap).

    Args:
        decree_log: a `DecreeLog` instance (any object exposing
            `issue(text, category, scope, ...) -> dict` — duck-typed so
            test fakes work without inheriting from DecreeLog).
        llm_adapter: optional callable `(prompt: str) -> str`. When
            supplied, `translate()` first asks the LLM to produce a
            JSON `{text, category, scope}` for the input. If the LLM
            raises or returns unparseable output, the translator
            transparently falls back to the rule-based path (per ADR-0006
            — falsifiable properties; a broken LLM does not silently pass
            through a malformed decree). When None (default), the
            rule-based path is used directly.

    Example:
        >>> from decree_log import DecreeLog
        >>> from conversational_decree import ConversationalDecreeInterface
        >>> dl = DecreeLog("/tmp/decrees.db")
        >>> cdi = ConversationalDecreeInterface(decree_log=dl, llm_adapter=None)
        >>> record = cdi.issue_from_nl("I don't want to use Google anymore")
        >>> record["category"]
        'prohibition'
        >>> record["decree_text"]
        'never use Google'
    """

    def __init__(
        self,
        decree_log: Any,
        llm_adapter: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.decree_log = decree_log
        self.llm_adapter = llm_adapter

    # ─── Public API ───────────────────────────────────────────────

    def translate(self, natural_language_text: str) -> Dict[str, Any]:
        """Translate natural language to a formal decree specification.

        Returns a dict with keys:
            text:     the formal decree text (e.g. "never use Google")
            category: one of {prohibition, law, permission, directive,
                       observation} — matches DecreeLog.issue()'s category
                       vocabulary
            scope:    the decree scope (default "all" in the rule-based path)

        Two paths (per ADR-0032 §Translation strategy):
            1. LLM path (preferred when llm_adapter is set): build the
               fixed-format prompt, call the adapter, parse the JSON
               response. On any failure → fall back to path 2.
            2. Rule-based path (always available): keyword detection over
               the lowercased input, with priority prohibition > law >
               permission > directive. Then formalize the text for the
               prohibition case ("use X anymore" → "never use X").

        The LLM path is wrapped in a broad try/except so that ANY adapter
        failure (network error, malformed JSON, timeout, exception)
        degrades to the deterministic rule-based path. Per ADR-0006:
        falsifiable — the rule-based path is the contract, the LLM is the
        upgrade.
        """
        # LLM path — preferred when an adapter is supplied.
        if self.llm_adapter is not None:
            try:
                prompt = (
                    "Translate this user intent to a decree. "
                    "Format: {text, category, scope}. "
                    f"User said: '{natural_language_text}'"
                )
                raw = self.llm_adapter(prompt)
                return self._parse_llm_response(raw, fallback_text=natural_language_text)
            except Exception:
                # LLM failed — degrade to rule-based (per ADR-0006).
                # Do NOT re-raise: a broken LLM must not prevent the human's
                # decree from being recorded.
                pass
        # Rule-based path.
        return self._rule_based_translate(natural_language_text)

    def issue_from_nl(self, natural_language_text: str) -> Dict[str, Any]:
        """Translate natural language → issue decree → return decree record.

        Calls `translate()` to get the formal decree specification, then
        calls `self.decree_log.issue(text=..., category=..., scope=...)`
        and returns whatever `issue()` returns (the decree record dict
        with `seq`, `timestamp`, `decree_text`, `category`, `scope`,
        `decree_hash`, etc.).

        The decree is durably recorded in the DecreeLog — append-only,
        hash-chained — before this method returns. A subsequent call to
        `decree_log.get_all()` will include it.

        Raises whatever `DecreeLog.issue()` raises (e.g. ValueError on
        invalid `required_signatures`; we don't pass that kwarg here so
        the default of 1 applies — single-sig, active immediately).
        """
        decree = self.translate(natural_language_text)
        return self.decree_log.issue(
            text=decree["text"],
            category=decree["category"],
            scope=decree.get("scope", _DEFAULT_SCOPE),
        )

    # ─── Internal: LLM response parsing ───────────────────────────

    @staticmethod
    def _parse_llm_response(raw: str, fallback_text: str) -> Dict[str, Any]:
        """Parse the LLM's string response into a decree specification.

        Expects a JSON object `{text, category, scope}`. The object may
        be embedded in surrounding prose, so we search for the first
        `{...}` block (non-greedy, single-level — no nested objects
        expected in this schema). If no `{...}` is found, attempt to
        parse the whole string as JSON.

        Normalizes:
            text:     stripped; falls back to `fallback_text` (the
                      original NL input) if missing or empty
            category: stripped, lowercased; falls back to "directive"
            scope:    stripped, lowercased; falls back to "all"

        Raises on any JSON parse failure — the caller (`translate`)
        catches and falls back to rule-based.
        """
        if raw is None:
            raise ValueError("LLM adapter returned None")

        # Find the first {...} block (single-level — our schema has no
        # nested objects). re.DOTALL so newlines inside the JSON are OK.
        match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        json_str = match.group(0) if match else raw
        obj = json.loads(json_str)
        if not isinstance(obj, dict):
            raise ValueError(f"LLM response is not a JSON object: {obj!r}")

        text = str(obj.get("text", fallback_text) or fallback_text).strip()
        if not text:
            text = fallback_text
        category = str(obj.get("category", _DEFAULT_CATEGORY)).strip().lower() or _DEFAULT_CATEGORY
        scope = str(obj.get("scope", _DEFAULT_SCOPE)).strip().lower() or _DEFAULT_SCOPE
        return {"text": text, "category": category, "scope": scope}

    # ─── Internal: rule-based translation ─────────────────────────

    @classmethod
    def _rule_based_translate(cls, text: str) -> Dict[str, Any]:
        """Keyword-detection translation (always available, no LLM).

        Priority: prohibition > law > permission > directive. A
        false-positive prohibition is safer than a false-negative (per
        ADR-0009 default-deny philosophy — respect the human's No).
        """
        lowered = text.lower()
        if any(t in lowered for t in _PROHIBITION_TRIGGERS):
            category = "prohibition"
        elif any(t in lowered for t in _LAW_TRIGGERS):
            category = "law"
        elif any(t in lowered for t in _PERMISSION_TRIGGERS):
            category = "permission"
        else:
            category = _DEFAULT_CATEGORY

        formal_text = cls._formalize(text, category)
        return {"text": formal_text, "category": category, "scope": _DEFAULT_SCOPE}

    @staticmethod
    def _formalize(text: str, category: str) -> str:
        """Re-cast the NL text into formal decree vocabulary.

        Only the `prohibition` category is re-cast — for everything else
        (law / permission / directive), the original text is echoed
        unchanged (the kernel's check_compliance matcher already handles
        raw text; only prohibitions benefit from the
        `never <verb> <entity>` shape that _PROHIBITION_REGEX in
        decree_log.py expects).
        """
        if category != "prohibition":
            return text.strip()

        # Try the English verb-first pattern: "use X" / "using X" / ...
        # Operate on the ORIGINAL text (preserve the entity's case — the
        # human typed "Google" with a capital G, keep it).
        m = _PROHIBITION_VERB_RE.search(text)
        if m:
            entity = m.group(1).strip()
            # Strip trailing filler words ("anymore", "any more", "again",
            # ...) and trailing punctuation, in that order, repeated
            # until stable (handles "Google, anymore!" → "Google").
            for _ in range(3):  # 3 passes is enough for any realistic input
                entity = _TRAILING_PUNCT_RE.sub("", entity).strip()
                new_entity = _PROHIBITION_FILLER_RE.sub("", entity).strip()
                new_entity = _TRAILING_PUNCT_RE.sub("", new_entity).strip()
                if new_entity == entity:
                    break
                entity = new_entity
            if entity:
                return f"never use {entity}"

        # Russian: "запретить X" or "запретить использовать X"
        m2 = _PROHIBITION_RU_RE.search(text)
        if m2:
            entity = m2.group(1).strip()
            entity = _TRAILING_PUNCT_RE.sub("", entity).strip()
            if entity:
                return f"never use {entity}"

        # No entity extractable — echo the original text. The kernel's
        # check_compliance matcher will still try to match the raw
        # text; if it can't, the decree is recorded but inert (the human
        # can supersede it via ADR-0028 and rephrase). Do NOT invent an
        # entity — that would put words in the human's mouth, violating
        # PAROLE > LANGUE (MANIFESTO §2).
        return text.strip()


__all__ = ["ConversationalDecreeInterface"]
