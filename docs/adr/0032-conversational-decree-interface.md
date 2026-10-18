# ADR-0032 — Conversational Decree Interface

**Date:** 2026-10-19
**Status:** Accepted
**Tags:** decree, conversational, nlp, llm, v3.20.0
**Deciders:** @USER (Командир корабля)
**Extends:** [ADR-0022 — Decree Portal as Human Interface](./0022-decree-portal-as-human-interface.md)

## Context

ADR-0021 established the Decree Log (ВОЛЯ = НАКАЗ) — the human's raw
expression (PAROLE) is recorded as a binding decree, append-only,
hash-chained. ADR-0022 gave the human a direct typing interface —
`apps/browser/decree-portal.html` — where the human types decree
**text**, picks a **category**, and clicks "⚡ ИЗДАТЬ ДЕКРЕТ".

But this still puts the burden of **formalization** on the human:
the human must already know that "I don't want to use Google anymore"
becomes `text="never use Google"`, `category="prohibition"`,
`scope="all"`. The human must think like a decree-clerk before their
will is recorded.

This violates the foundational principle **PAROLE > LANGUE**
(MANIFESTO §2): the human's raw speech is supposed to BE the law.
The decree portal currently forces the human to translate their
speech into the system's langue *before* the system will accept it.

What we want instead:

> Human types: "I don't want to use Google anymore"
> System translates → `text="never use Google"`, `category="prohibition"`, `scope="all"`
> System issues → decree #N recorded in the hash-chained log
> Kernel enforces → every subsequent Intent mentioning Google → DENIED

The translation step is **not** an interpretation that changes the
meaning — it is a **re-casting** of the same meaning into the formal
decree vocabulary the kernel already understands. The human's PAROLE
is preserved (recorded in `decree_text`); the formalized shape is
just a deterministic projection that the kernel's `check_compliance`
matcher can apply.

This ADR introduces `ConversationalDecreeInterface` — a thin layer
that sits in front of `DecreeLog.issue()` and accepts natural
language, translates it, and issues the resulting decree in one call.

## Decision

Implement `runtime/src/conversational_decree.py` with class
`ConversationalDecreeInterface`:

```python
cdi = ConversationalDecreeInterface(decree_log=dl, llm_adapter=None)
record = cdi.issue_from_nl("I don't want to use Google anymore")
# → dl.issue(text="never use Google", category="prohibition", scope="all") → record
```

### Translation strategy

`translate(natural_language_text) -> dict` returns a decree
specification `{text, category, scope}`. Two paths:

1. **LLM path (preferred when an `llm_adapter` is supplied).** The
   adapter is duck-typed as a callable `(prompt: str) -> str`. The
   prompt is fixed-format:
   ```
   Translate this user intent to a decree. Format: {text, category, scope}. User said: '<NL>'
   ```
   The LLM's response is parsed for a JSON object `{text, category,
   scope}`. If parsing fails (no JSON, wrong shape, adapter raises),
   the translator falls back to the rule-based path. This honors
   ADR-0006 (falsifiable properties): a broken LLM does not silently
   pass through — it degrades to the deterministic fallback.

2. **Rule-based path (always available, used when no LLM is supplied
   or the LLM path failed).** Keyword detection over the lowercased
   input. Priority order is `prohibition > law > permission` (because
   "never" is a stronger commitment than "always" and a false-positive
   prohibition is safer than a false-negative — the system errs
   toward respecting the human's No).

   | Trigger (case-insensitive, partial substring)  | Category     |
   |------------------------------------------------|--------------|
   | `don't want`, `do not want`, `never`, `stop using`, `no more`, `запретить`, `запрет` | `prohibition` |
   | `always`, `обязательно`, `всегда`, `must`       | `law`        |
   | `allow`, `разрешить`, `permission to`, `you may` | `permission` |
   | (none of the above)                            | `directive`  |

   After the category is detected, the text is **formalized**:
   - **Prohibition**: regex-search for a verb introducing the
     prohibited entity (`use`, `using`, `adopt`, `deploy`, `install`,
     `run`, `rely on`, `send`, `share`, `transmit`, `expose`)
     followed by `(.+)` to the end of input. Trailing filler words
     (`anymore`, `any more`, `again`, `ever`, `no more`) and
     trailing punctuation are stripped. The decree text becomes
     `never use <entity>`. Russian `запретить X` is mapped the same
     way. If no entity is extractable, the original text is echoed
     unchanged (do not invent).
   - **Law / permission / directive**: the original text is echoed
     unchanged (the kernel's `check_compliance` matcher already
     handles raw text — these categories do not need the
     `never <verb> X` shape).

   `scope` is always `"all"` in the rule-based path (rule-based
   detection does not infer scope from natural language; scope
   refinement is left to the LLM path or to the human editing the
   formal decree directly).

### Issue

`issue_from_nl(natural_language_text) -> dict` calls `translate()` to
get the formal decree specification, then calls
`self.decree_log.issue(text=..., category=..., scope=...)` and
returns the decree record (the dict that `DecreeLog.issue()` already
returns — `seq`, `timestamp`, `decree_text`, `category`, `scope`,
`decree_hash`, etc.).

### No new decree category, no schema changes

The formal decree produced by the translator uses the EXISTING
`DecreeLog.issue()` API and the EXISTING categories
(`prohibition | law | permission | directive | observation`). No
new table, no new column, no migration. The translator is a pure
preprocessing layer — `DecreeLog` does not know that a decree came
from natural language vs. from a typed formal decree.

This is critical: the append-only hash-chained invariant
(ADR-0021), the supersession mechanism (ADR-0028), the N-of-M
multi-sig (ADR-0029 §6), the time-limited decrees (v3.19.0), and the
NSA compartmentalization (ADR-0029 §7) all apply unchanged to
conversational decrees. The human's "I don't want to use Google
anymore" decree is, after formalization, byte-for-byte identical to
a hand-typed `never use Google` prohibition decree.

### Preserving PAROLE

The `decree_text` column contains the **formalized** decree
(`never use Google`), not the raw natural-language utterance. This
is intentional — `decree_text` is the binding law string that
`check_compliance` matches against, and the matcher expects the
formal shape. The raw PAROLE can be reconstructed from the audit
trail if needed (the human typed it in the portal; the portal can
log the raw input alongside the formalized decree text in a separate
audit column or vault note). This ADR does not change how
`decree_text` is stored.

## Consequences

**Positive:**
- **Lowers the formalization burden** — the human can type raw speech
  and the system re-casts it into decree vocabulary. Honors PAROLE >
  LANGUE (MANIFESTO §2): the human's speech IS the law, not a
  template the human must learn to fill in.
- **Deterministic fallback** — when no LLM is available (offline,
  air-gapped, model not loaded), the rule-based translator still
  produces correct formal decrees for the common cases (Google,
  Cloudflare, Chrome, DNS, etc.). The system never refuses a decree
  because the LLM is down.
- **No schema migration** — the translator is a pure preprocessing
  layer; the append-only hash-chained invariant is untouched. A
  conversational decree and a hand-typed formal decree are
  indistinguishable in the log.
- **Composes with ADR-0028 (supersession)** — the human can later
  say "actually I do want to use Google for one specific thing" and
  the existing supersession mechanism applies unchanged.
- **Composes with ADR-0029 (N-of-M + classification)** — a
  conversational decree can require multi-sig or be classified
  `secret` by passing the same kwargs through (the translator
  does not block this; future extension).

**Negative:**
- **Rule-based translation is shallow** — only handles the
  `never <verb> <entity>` shape. Complex prohibitions like "I
  don't ever want to see another Docker container on this machine"
  will fall through to the entity-extraction failure case and be
  echoed verbatim — `check_compliance` will not recognize "Docker
  container" as a prohibited term unless the human rephrases.
  Mitigation: the LLM path handles these; the rule-based path
  handles the common 80%.
- **Scope is hardcoded to `"all"` in rule-based path** — the
  translator does not infer that "don't use Google in cell65-host"
  should be `scope="cell65-host"`. The LLM path can fill this in,
  but offline the human must edit the formal decree directly to
  narrow scope. Acceptable — `scope="all"` is the safe default.
- **False-positive prohibition risk** — the trigger `no more` could
  match a benign phrase like "no more alerts please" and produce a
  prohibition decree. Mitigation: the priority order
  (`prohibition > law > permission`) errs toward respecting the
  human's No, which is the conservative direction per ADR-0009
  (default-deny).
- **LLM translation is not byte-deterministic** — two calls with
  the same input may produce slightly different decree texts (e.g.
  "never use Google" vs. "never use the Google"). This is acceptable
  because `check_compliance` matches on whole-word boundaries, so
  both produce the same enforcement behavior. But it means the
  decree log is not reproducible from NL inputs alone — the
  translator's output is part of the audit trail (recorded as
  `decree_text`).

**Neutral:**
- The translator is **idempotent in shape but not in seq** — calling
  `issue_from_nl("never use Google")` twice produces two decrees
  (seq N and seq N+1), both with the same text. This is correct
  (append-only) but means the human cannot "re-issue" the same
  decree to deduplicate — they should use supersession (ADR-0028)
  if they want to revoke the duplicate.

## Alternatives considered

1. **LLM-only (no rule-based fallback).** Rejected: violates
   ADR-0002 (Tier 1 — no external deps at runtime) and ADR-0006
   (falsifiable properties — an LLM-only path is non-deterministic
   and cannot be mutation-tested). The rule-based path is the
   contract; the LLM path is the upgrade.

2. **Store the raw natural-language text in `decree_text` and let
   `check_compliance` do NLP matching.** Rejected: changes the
   `decree_text` semantics (currently a formal law string), breaks
   the v0.6.1 prohibition matcher regex, and makes the hash chain
   dependent on the LLM's exact output. Keeping `decree_text`
   formal preserves every other invariant.

3. **Add a `natural_language` column to the decrees table.**
   Rejected: schema migration for marginal benefit. The raw
   utterance can be logged in the browser portal or the vault; the
   decree log itself stays formal.

4. **Voice-only interface (no text).** Rejected for the same reason
   as ADR-0022 alternative 2 — voice needs Chrome = corporate. Text
   is primary. This ADR is about the *form* of the text input, not
   the *modality*.

5. **Make the translator a separate `DecreeTranslator` service with
   its own SQLite cache of translations.** Rejected: over-engineered
   for v1. The translator is stateless; it does not need a database.
   If translation caching becomes valuable (e.g. to detect repeated
   decrees), it can be added later as a separate concern.

## Verification

- `runtime/tests/test_conversational_decree.py` — 5 tests:
  - `test_rule_based_prohibition_detection` — NL with a
    prohibition trigger → `category == "prohibition"`.
  - `test_rule_based_law_detection` — NL with a law trigger →
    `category == "law"`.
  - `test_issue_from_nl_creates_decree` — full pipeline:
    `issue_from_nl()` returns a decree record with `seq`, `category`,
    `decree_hash`, etc.; the decree is durably stored (recoverable
    via `dl.get_all()`).
  - `test_nl_with_google_becomes_prohibition` — the canonical
    example: "I don't want to use Google anymore" →
    `category == "prohibition"` and `decree_text` starts with
    `never use Google` (case-insensitive).
  - `test_nl_default_directive` — NL with no recognized trigger →
    `category == "directive"` and `decree_text` echoes the input.

- `make verify` check 01 (SINGULYAR EIR tests) — still passes
  (the new module imports cleanly and the new tests run alongside
  the existing `test_decree_log.py`).

- Manual: open a fresh DecreeLog, call
  `cdi.issue_from_nl("I don't want to use Google anymore")`,
  then call `dl.check_compliance("configure DNS with Google 8.8.8.8")`
  and verify the result is non-compliant (the prohibition decree
  blocks the matching intent).

## References

- [ADR-0021 — Decree as Supreme Law](./0021-decree-as-supreme-law.md) —
  append-only hash-chained invariant; PAROLE > LANGUE.
- [ADR-0022 — Decree Portal as Human Interface](./0022-decree-portal-as-human-interface.md) —
  the typing interface this ADR upgrades.
- [ADR-0028 — Decree Supersession Mechanism](./0028-decree-supersession-mechanism.md) —
  composes: a conversational decree can be superseded like any other.
- [ADR-0029 — СИНГУЛЯР Security Model](./0029-singulyar-security-model-corporate-synthesis.md) —
  N-of-M + classification apply unchanged to conversational decrees.
- [ADR-0006 — Falsifiable Self-Properties](./0006-falsifiable-self-properties.md) —
  the LLM path degrades to the deterministic fallback rather than
  silently passing through a broken translation.
- `runtime/src/decree_log.py` — `DecreeLog.issue()` API used by the
  translator.
- `runtime/src/adapters/llm_local_adapter.py` — example of the
  duck-typed LLM adapter shape (a callable that takes a prompt and
  returns a string).
- `runtime/src/conversational_decree.py` — implementation.
- `runtime/tests/test_conversational_decree.py` — tests.

## Self-reference

This ADR itself can be superseded by a future decree-driven amendment
(per ADR-0026). For example:
- Decree #N: "the rule-based translator must also recognize
  'ban <X>' and 'no <X>' as prohibition triggers" → ADR-0032 is
  amended via AdrAmender.
- Decree #N+1: "the LLM path is now mandatory; remove the rule-based
  fallback" → ADR-0032 is superseded by a new ADR-0033.
