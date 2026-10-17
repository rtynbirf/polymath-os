# ADR-0021 — Decree as Supreme Law (ВОЛЯ ЧЕЛОВЕКОИЗЪЯВЛЕНИЯ = НАКАЗ)

**Date:** 2026-10-16 (v3.2.0)
**Status:** Accepted
**Deciders:** @USER
**Supersedes:** None (above all ADRs — DECREE > ADR > code)

## Context

Per MANIFESTO principle 1: "Человек — PID=1."
Per MANIFESTO principle 2: "PAROLE > LANGUE."
Per SOVEREIGNTY_CONTRACT.md §11: "The human says X and polymath-os's
kernel treats it as law."

But there was NO mechanism for the human's raw expression (PAROLE) to
become binding law in the system. ADRs are written by the AI. Code is
written by the AI. The human's WILL was expressed through the AI
session, but not RECORDED as law.

This ADR introduces the **Decree Log** — the supreme law layer.

## Decision

### 1. Decree Log — `runtime/src/decree_log.py`

A SQLite-based append-only hash-chained journal that records the
human's raw expressions as binding decrees. Each decree:
- Has a sequence number (monotonic)
- Has a timestamp (ISO 8601 UTC)
- Has the raw text (what the human said — PAROLE)
- Has a category: 'law' | 'prohibition' | 'permission' | 'observation' | 'directive'
- Has a scope: 'all' | 'singulyar' | 'polymath-os' | 'cell65-host' | etc.
- Is hash-chained (SHA-256 of prev_hash + timestamp + text)
- Is append-only (immutable once recorded)
- Chain verified on open (fail-closed per ADR-0006)

### 2. DECREE > ADR > code

The hierarchy:
1. **DECREE** (human's raw will — PAROLE) — supreme, cannot be overridden
2. **ADR** (architectural decision — LANGUE) — can be superseded by new ADR (per ADR-0016)
3. **code** (implementation) — follows ADRs

A decree can create, amend, or supersede an ADR. An ADR CANNOT
override a decree. Code CANNOT override an ADR.

### 3. Decree compliance check — `check_compliance(intent_text)`

The kernel calls `check_compliance()` before executing any Intent.
If a prohibition decree says "never use Google" → any intent containing
"google" is DENIED. Not by policy rule — by DECREE.

### 4. Decree categories

| Category | What it means | Enforcement |
|---|---|---|
| law | Binding rule | Kernel enforces via check_compliance() |
| prohibition | "never do X" | check_compliance() blocks matching intents |
| permission | "explicitly allow X" | overrides default-deny for specific action |
| observation | Record without binding | Journal entry, no enforcement |
| directive | Specific action command | Kernel routes to appropriate adapter |

### 5. Decree enforcement

Simple implementation (v1): keyword matching. If a prohibition decree
contains "never use X" → the kernel checks if the intent contains X.

Future (v0.5): NLP-based semantic matching (deterministic, no LLM).

## Consequences

- **+**: The human's will is RECORDED as law, not just interpreted
- **+**: Append-only + hash-chained = tamper-evident (can't forge decrees)
- **+**: check_compliance() makes decrees ENFORCED, not just documented
- **+**: DECREE > ADR — the human's word supersedes AI decisions
- **-**: Simple keyword matching may have false positives/negatives
- **-**: No way to REVOKE a decree (append-only — can issue a new decree that supersedes)

## Verification

- 8 tests in tests/test_decree_log.py — all pass
- test_append_only_cannot_amend — chain breaks on tamper
- test_hash_chain_verification_on_open — tamper detected on reopen
- test_check_compliance_prohibition_blocks — decrees enforced
- test_decrees_survive_restart — SQLite WAL durability
- make verify — 21/21 PASS

## References

- MANIFESTO principle 1: "Человек — PID=1"
- MANIFESTO principle 2: "PAROLE > LANGUE"
- ADR-0006 (Falsifiable self-*) — chain verification fail-closed
- ADR-0009 (Default-deny) — no decree = no permission
- ADR-0016 (Self-rewriting ADR) — decrees can supersede ADRs
- SOVEREIGNTY_CONTRACT.md §11 — 7 contracts (decree is the 8th)
