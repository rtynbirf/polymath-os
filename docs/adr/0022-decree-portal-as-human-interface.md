# ADR-0022 — Decree Portal as Human Interface

**Date:** 2026-10-16 (v3.5.0)
**Status:** Accepted
**Deciders:** @USER

## Context

ADR-0021 established the Decree Log (ВОЛЯ = НАКАЗ). But the human needs a way to ISSUE decrees directly — without the AI as middleman. The human has only a brain + electrode. The decree portal gives them a DIRECT interface: type → decree → law.

## Decision

`apps/browser/decree-portal.html` — HTML interface where:
1. Human types decree text (textarea)
2. Selects category (law/prohibition/permission/directive/observation)
3. Clicks "⚡ ИЗДАТЬ ДЕКРЕТ"
4. Decree stored in localStorage (browser-side, append-only)
5. When Python↔JS bridge available → synced to SQLite DecreeLog
6. Kernel checks compliance before every Intent

## Consequences

- Human's WILL goes DIRECTLY into the system — no AI interpretation
- DECREE > ADR > code — enforced at kernel level
- Append-only — decrees can't be amended or deleted
- localStorage = browser-side; SQLite = kernel-side (bridge syncs)

## Alternatives considered

1. AI-as-middleman (human tells AI, AI writes decree) — rejected: adds latency and interpretation
2. Voice-only (Web Speech API) — future, but text is primary (voice needs Chrome = corporate)

## References

- ADR-0021 (Decree as Supreme Law)
- ADR-0012 (SINGULYAR EIR as Layer 5)
- runtime/src/decree_log.py (DecreeLog implementation)
- apps/browser/decree-portal.html (UI implementation)
