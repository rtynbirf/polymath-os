# Agent Execution System — polymath-os overlay

## Purpose

Create a repeatable way for one or more AI agents to investigate, design, modify, test, criticize, and document changes while preserving human control and auditable evidence.

## Maturity labels

- **CURRENTLY OBSERVED:** directly inspected in the repository and supported by a path/commit/log.
- **PROPOSED:** design to implement; not yet running.
- **UNKNOWN:** not inspected or not reproducible.
- **DEPRECATED:** retained for history, not to be used for new work.

At package creation, all runtime architecture in this folder is **PROPOSED** until verified against the actual repository and implemented.

## Reading paths

- Coding agent: root `AGENTS.md` → `01` → `02` → relevant domain docs → `05` → `06` → `08`.
- Research agent: `02` → `06` → `12`; return claim/evidence pairs, not loose summaries.
- Reviewer: `02` → `06` → `08`; review the diff and evidence independently.
- Security reviewer: `07` plus all relevant workflow/tool/credential paths.
- Integrator: `05` → `08` → `09`; do not merge without gates.

## First milestone

Do not implement a large agent framework immediately. First inspect the repo, establish baseline commands, adopt the task/evidence format, and make one end-to-end pilot task reproducible. Runtime choice is an ADR after the baseline, not a foregone conclusion.
