# Polymath OS

> **Open-source ideal repository.** Clone it. Run `make verify`. Every claim in this repo is reproducible by that one command. If it exits 0 — every claim holds. If non-zero — the claim that failed is shown.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Verify](https://img.shields.io/badge/make%20verify-passing-brightgreen)](./scripts/check.py)
[![SINGULYAR EIR v0.3](https://img.shields.io/badge/runtime-SINGULYAR%20EIR%20v0.3-blue)](./runtime/)

---

## What this is

**Polymath OS** is an open-source LFS-style rebuild of a personal operating system. It is not a "report" — it is a working, reproducible codebase. 5 layers + cross-cutting concerns, all in one self-contained git tree.

**Philosophy:** Человек = PID=1 = processor + сумма частей. The repo is the material projection of that init-process: every component is fork-exec from the human, not an external dependency. Audit (audit A11) — PID=1 is a metaphor, not a source of technical requirements. Rights, session isolation, portability are recorded separately.

## Layers

| Layer | What | Code |
|---|---|---|
| **Layer 5** | Execution Kernel — preserves intent across executor changes, never claims success without verified state | `runtime/` (SINGULYAR EIR v0.3) |
| **Layer 4** | DevEx / CI / IaC / Dotfiles / Observability | `infra/`, `Makefile`, `.github/workflows/`, `.devcontainer/` |
| **Layer 3** | Second Brain (PKM) — markdown-first, git-synced, AI-augmented | `vault/` (gitignored, private) |
| **Layer 2** | AI Workflows — MCP-native (version-pinned), Claude Code + Aider + Cursor | `tooling/agents/` (to be created) |
| **Layer 1** | Repository Structure — pnpm + Turborepo + Changesets + CODEOWNERS | repo root |
| **Cross-cutting** | Security (cosign/SLSA/SBOM) + OTel + git | everywhere |

For the mental model, see [`ARCHITECTURE.md`](./ARCHITECTURE.md). For how every architectural decision was made, see [`docs/adr/`](./docs/adr) (12 ADRs).

## Quick start

```bash
# 1. Clone
git clone git@github.com:USER/polymath-os.git
cd polymath-os

# 2. Verify every claim in this repo (no installation required, Python 3.10+)
make verify

# 3. If you want to develop:
make bootstrap   # pnpm install + nix develop (optional)
make test        # runs all tests (runtime + packages)
make ci-local    # reproduces CI locally via `act`
```

If `make verify` exits 0 — every claim below holds on your machine. That's the open-source contract.

## Verifiable claims

Every claim in this repo is backed by a test or command. `make verify` runs all 12 checks.

| # | Claim | How to verify | Status |
|---|---|---|---|
| 01 | SINGULYAR EIR passes all 40 tests (including real `os._exit` between effect and recording) | `cd runtime && python scripts/check.py` | ✓ |
| 02 | JSON Schemas (Intent / Capability / Evidence) parse and validate | `python scripts/check.py` (check 02) | ✓ |
| 03 | 12 ADRs (0001-0012) all present | `ls docs/adr/` | ✓ |
| 04 | Every ADR follows template (Date/Status/Context/Decision/Consequences) | `python scripts/check.py` (check 04) | ✓ |
| 05 | `AUDIT_RESPONSE.md` cross-references every ADR | `python scripts/check.py` (check 05) | ✓ |
| 06 | Sovereignty Registry covers every `package.json` dependency | `python scripts/check.py` (check 06) | ✓ |
| 07 | RUNBOOK is hardened (preconditions + result check + ⛔ irreversible markers) | `python scripts/check.py` (check 07) | ✓ |
| 08 | LICENSE = MIT | `cat LICENSE` | ✓ |
| 09 | `ARCHITECTURE.md` documents 5 layers + Sovereignty Registry + falsifiable self-* | `python scripts/check.py` (check 09) | ✓ |
| 10 | `runtime/src/*.py` compile (Python syntax check) | `python scripts/check.py` (check 10) | ✓ |
| 11 | No `__pycache__` or `*.pyc` in tree | `python scripts/check.py` (check 11) | ✓ |
| 12 | CI workflow runs pnpm + turbo + gitleaks | `python scripts/check.py` (check 12) | ✓ |

**To reproduce**: clone this repo, run `make verify`. You will see the same result.

## What you can take

- **The whole repo** — fork it, replace `USER` with your handle, run `make verify`, you have your own Polymath OS.
- **`runtime/` alone** — SINGULYAR EIR is self-contained, MIT-licensed, zero dependencies (Python 3.10+, standard library only). Drop into your project as the execution kernel.
- **Individual ADRs** — each is self-contained, with Context/Decision/Consequences. Copy the pattern.
- **The hardened RUNBOOK template** — the procedure template (ПРЕДУСЛОВИЯ → ПРЕДПРОСМОТР → ДЕЙСТВИЕ ⛔ → ПРОВЕРКА → ЕСЛИ УПАЛО → СЛЕД) works for any ops team.
- **The Sovereignty Registry pattern** — the two-tier dependency registry (sovereign core vs rented services) works for any project that wants to think about vendor lock-in.

## Why this exists

This repo is the answer to: *"Какое новое свойство возникает, когда git, AI-agents, base знаний, CI/CD и recovery соединены именно так — и как доказать, что это не просто красивое название?"*

The answer is **Layer 5 (SINGULYAR EIR)** — an execution kernel that:
- preserves a person's declared intent across interchangeable execution methods
- makes every completion claim depend on inspectable evidence of the required final state
- treats "cannot tell" as a first-class outcome (`UNKNOWN`), not as a silent `CONFIRMED`

Emergence here is a **falsifiable hypothesis**, not a slogan. The ablation ladder B0→B3→EIR in `runtime/docs/EXPERIMENT_RESULTS.md` shows that each link removes a specific class of failure. The test `test_each_ablation_link_is_load_bearing` checks that each link is actually load-bearing. The price: in two scenarios, the kernel honestly answers `UNKNOWN` instead of "probably worked".

## Documentation map

| Document | Purpose |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Mental model: 5 layers + Sovereignty Registry + falsifiable self-* |
| [`TZ.md`](./TZ.md) | Technical spec: requirements + acceptance criteria |
| [`ROADMAP.md`](./ROADMAP.md) | Phased plan (exit-gate based, not calendar) |
| [`docs/AUDIT_RESPONSE.md`](./docs/AUDIT_RESPONSE.md) | Audit findings A1-A11 → ADR → action mapping |
| [`docs/adr/`](./docs/adr) | 12 ADRs (0001-0012) — every architectural decision |
| [`docs/01-principles.md`](./docs/01-principles.md) | 18 principles (constitution) |
| [`docs/02-repo-structure.md`](./docs/02-repo-structure.md) | Layer 1 details |
| [`docs/03-ai-workflows.md`](./docs/03-ai-workflows.md) | Layer 2 details |
| [`docs/04-second-brain.md`](./docs/04-second-brain.md) | Layer 3 details |
| [`docs/05-devex-ci.md`](./docs/05-devex-ci.md) | Layer 4 details |
| [`docs/runbook/RUNBOOK.md`](./docs/runbook/RUNBOOK.md) | Hardened operations runbook |
| [`runtime/README.md`](./runtime/README.md) | Layer 5: SINGULYAR EIR |
| [`runtime/docs/TECHNICAL_SPEC.md`](./runtime/docs/TECHNICAL_SPEC.md) | EIR technical spec |
| [`runtime/docs/EXPERIMENT_RESULTS.md`](./runtime/docs/EXPERIMENT_RESULTS.md) | Ablation B0→B3→EIR |
| [`runtime/docs/LIMITATIONS.md`](./runtime/docs/LIMITATIONS.md) | What's NOT proven (honesty) |
| [`runtime/docs/AUDIT_POLYMATH.md`](./runtime/docs/AUDIT_POLYMATH.md) | The audit that drove the fixes |

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Trunk-based, conventional commits, ADR-driven.

Every PR must pass `make verify`. If your PR adds a new architectural decision, you must add an ADR. If your PR adds a new claim to README, you must add a check to `scripts/check.py`.

## License

MIT — see [`LICENSE`](./LICENSE). Take it. Use it. Fork it. The sovereign core (git, markdown, SQLite, age, Nix) is yours forever — works without network, without accounts, without permission.

## Origin

This repo was built through an iterative dialogue:
1. **v0.1**: User asked for 100 file formats → 100 messengers → 100 portable apps (philosophical exploration of "human = system")
2. **v0.2**: User delegated polymath audit → 4 parallel research agents → synthesis into Polymath OS (4 layers + cross-cutting)
3. **v0.3 (current)**: SINGULYAR EIR v0.3 audit applied → 11 audit findings fixed via 12 ADRs → SINGULYAR integrated as Layer 5 → repo promoted from "report" to "open-source ideal repo" with `make verify` contract

Worklog: `/home/z/my-project/worklog.md`
