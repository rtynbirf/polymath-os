# Polymath OS

> **Open-source ideal repository.** Clone it. Run `make verify`. Every claim in this repo is reproducible by that one command. If it exits 0 — every claim holds. If non-zero — the claim that failed is shown.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Verify](https://img.shields.io/badge/make%20verify-26%2F26%20PASS-brightgreen)](./scripts/check.py)
[![SINGULYAR EIR v0.6](https://img.shields.io/badge/runtime-SINGULYAR%20EIR%20v0.6-blue)](./runtime/)
[![Tests](https://img.shields.io/badge/tests-290%2F290%20PASS-brightgreen)](./runtime/tests/)
[![Decrees](https://img.shields.io/badge/decree%20log-7%20foundational%20laws-orange)](./runtime/src/decree_log.py)
[![CI](https://img.shields.io/badge/CI-5%2F5%20green-brightgreen)](https://github.com/rtynbirf/polymath-os/actions)

**Current version: v3.8.0** (commit `3f279c0`, 2026-10-17) — see [CHANGELOG.md](./CHANGELOG.md).

---

## What this is

**Polymath OS** is an open-source LFS-style rebuild of a personal operating system. It is not a "report" — it is a working, reproducible codebase. **5 layers + cross-cutting concerns**, all in one self-contained git tree. Above all 5 layers sits the **Decree Log** — the human's supreme law layer, hash-chained and append-only, that the runtime enforces BEFORE any policy check.

**Philosophy:** Человек = PID=1 = processor + сумма частей. The repo is the material projection of that init-process: every component is fork-exec from the human, not an external dependency. Audit (audit A11) — PID=1 is a metaphor, not a source of technical requirements. Rights, session isolation, portability are recorded separately.

**Decree system (since v3.6.0):** the human types a decree in the [Decree Portal](./apps/browser/decree-portal.html) → it's recorded in real SQLite (`~/.polymath-os/decrees.db`, hash-chained, append-only) → the SINGULYAR EIR runtime checks every Intent against active decrees BEFORE policy. **DECREE > ADR > code.** Per ADR-0021 + ADR-0022.

## Layers

| Layer | What | Code |
|---|---|---|
| **Decree Log** (supreme) | Human's word = law. SQLite, hash-chained, append-only. Enforced BEFORE policy. | `runtime/src/decree_log.py` + `apps/browser/decree-portal.html` |
| **Layer 5** | Execution Kernel — preserves intent across executor changes, never claims success without verified state, decree gate above policy | `runtime/` (SINGULYAR EIR v0.6) |
| **Layer 4** | DevEx / CI / IaC / Dotfiles / Observability | `infra/`, `Makefile`, `.github/workflows/`, `.devcontainer/` |
| **Layer 3** | Second Brain (PKM) — markdown-first, git-synced, AI-augmented | `vault/` (private, canary-tested for default-deny publish) |
| **Layer 2** | AI Workflows — MCP-native (version-pinned, 4 adapters) | `tooling/agents/mcp/` |
| **Layer 1** | Repository Structure — pnpm + Turborepo + Changesets + CODEOWNERS | repo root |
| **Cross-cutting** | Security (cosign/SLSA/SBOM) + OTel + git + token hygiene | everywhere |

For the mental model, see [`ARCHITECTURE.md`](./ARCHITECTURE.md). For how every architectural decision was made, see [`docs/adr/`](./docs/adr) (**28 ADRs**: 0001-0022).

## Quick start

```bash
# 1. Clone
git clone https://github.com/rtynbirf/polymath-os.git
cd polymath-os

# 2. Verify every claim in this repo (no installation required, Python 3.10+)
make verify
# → Result: 23 passed, 0 failed (of 23 claims)

# 3. Issue the 7 foundational decrees (creates ~/.polymath-os/decrees.db)
python3 /home/z/my-project/scripts/issue_decrees.py
# → 7 decrees recorded, chain integrity OK

# 4. Run the production decree enforcement demo
python3 runtime/src/demo_with_decree.py
# → Intent 1: CONFIRMED
# → Intent 2: WAITING_FOR_HUMAN (blocked by decree #3 'never use Google DNS')

# 5. Check compliance via Node bridge
node apps/browser/decree-bridge.js list
node apps/browser/decree-bridge.js check "configure DNS with Google 8.8.8.8"
# → {"compliant": false, "violations": [...]}

# 6. Open Decree Portal UI (browser, localStorage fallback)
open apps/browser/decree-portal.html
# OR — Electron desktop wrapper (~200MB install)
cd apps/browser/electron && npm install && npm start

# 7. If you want to develop:
make bootstrap   # pnpm install + nix develop (optional)
make test        # runs all tests (123 runtime + MCP coverage)
make ci-local    # reproduces CI locally via `act`
```

If `make verify` exits 0 — every claim below holds on your machine. That's the open-source contract.

## Verifiable claims

Every claim in this repo is backed by a test or command. `make verify` runs all **23 checks** (was 12 in v1.0, was 22 in v3.6.0, +1 token hygiene in v3.8.0).

| # | Claim | How to verify | Status |
|---|---|---|---|
| 01 | SINGULYAR EIR passes all 220 tests (including real `os._exit` between effect and recording, +12 new for v0.6 phrase matching) | `cd runtime && python scripts/check.py` | ✓ |
| 02 | JSON Schemas (Intent / Capability / Evidence) parse and validate | `python scripts/check.py` (check 02) | ✓ |
| 03 | 28 ADRs (0001-0028) all present | `ls docs/adr/` | ✓ |
| 04 | Every ADR follows template (Date/Status/Context/Decision/Consequences) | `python scripts/check.py` (check 04) | ✓ |
| 05 | `AUDIT_RESPONSE.md` cross-references every ADR | `python scripts/check.py` (check 05) | ✓ |
| 06 | Sovereignty Registry covers every `package.json` dependency | `python scripts/check.py` (check 06) | ✓ |
| 07 | RUNBOOK is hardened (preconditions + result check + ⛔ irreversible markers) | `python scripts/check.py` (check 07) | ✓ |
| 08 | LICENSE = MIT | `cat LICENSE` | ✓ |
| 09 | `ARCHITECTURE.md` documents 5+1 layers + Sovereignty Registry + falsifiable self-* | `python scripts/check.py` (check 09) | ✓ |
| 10 | `runtime/src/*.py` compile (Python syntax check) | `python scripts/check.py` (check 10) | ✓ |
| 11 | No `__pycache__` or `*.pyc` in tree | `python scripts/check.py` (check 11) | ✓ |
| 12 | CI workflow runs pnpm + turbo + gitleaks | `python scripts/check.py` (check 12) | ✓ |
| 13 | Pattern: manifest exclusivity (S17) | `python scripts/check.py` (check 13) | ✓ |
| 14 | Pattern: counter-from-source (S2) | `python scripts/check.py` (check 14) | ✓ |
| 15 | Pattern: CSP no scheme-only connect-src (S26/S41) | `python scripts/check.py` (check 15) | ✓ |
| 16 | Pattern: sovereignty drill runner exists (ADR-0002) | `python scripts/check.py` (check 16) | ✓ |
| 17 | Pattern: sequential triage rule-layer-first (S75) | `python scripts/check.py` (check 17) | ✓ |
| 18 | Pattern: no silent SW registration failure (S48) | `python scripts/check.py` (check 18) | ✓ |
| 19 | Pattern: storage eviction with protected-key Set (S30/S31) | `python scripts/check.py` (check 19) | ✓ |
| 20 | Pattern: identity backup documented (S37) | `python scripts/check.py` (check 20) | ✓ |
| 21 | Freedom: zero Tier 3 benefactors in code | `python scripts/check.py` (check 21) | ✓ |
| 22 | MANIFEST.json exists + valid (ADR-0020) | `python scripts/check.py` (check 22) | ✓ |
| 23 | **Token hygiene: no plaintext PATs in code (v0.6, ADR-0021 enforcement)** | `python scripts/check.py` (check 23) | ✓ |

**To reproduce**: clone this repo, run `make verify`. You will see the same 24/24 PASS result.

## Decree system (v3.6.0+ OPERATIONAL)

The decree log is the **human's supreme law layer** — above every ADR, above the kernel, above the code. Per ADR-0021 + ADR-0022 + MANIFESTO principle 2 (`PAROLE > LANGUE`).

### 7 foundational decrees + N supersession/amendment decrees (in `~/.polymath-os/decrees.db`)

The 7 foundational decrees are issued once via `python3 /home/z/my-project/scripts/issue_decrees.py`. After that, additional decrees may be added via the Decree Portal:
- `category=supersession` — revokes a previous decree (per ADR-0028, v3.14.0)
- `category=amendment` — drives ADR operations: create/amend/supersede/deprecate (per ADR-0026, v3.12.0)
- `category=law/prohibition/permission/observation/directive` — new rules (existing behavior)

All decrees are **append-only, immutable, hash-chained**. Superseded decrees remain in the log for audit but `get_active_laws()` skips them.

| # | Category | Text |
|---|----------|------|
| 1 | law | ЧЕЛОВЕК = PID=1. Каждый инструмент — fork-exec от человека. |
| 2 | law | PAROLE > LANGUE. Индивидуальное слово выше коллективного договора. |
| 3 | prohibition | never use Google DNS |
| 4 | prohibition | never use Cloudflare |
| 5 | prohibition | never use Chrome Firefox Edge Safari |
| 6 | law | UNKNOWN first-class. Таймаут ≠ failure ≠ success. |
| 7 | law | Default-deny. Публикуется только явное publish:true. |

### v0.6 Decree matching — three generations, all backward compatible

| Generation | Algorithm | Example |
|------------|-----------|---------|
| v0.4 (initial) | Naive substring match | `chrome` matched `chromebook` (FALSE POSITIVE) |
| v0.5 (v3.7.0) | Phrase classification (LIST/PHRASE/SINGLE/DEFAULT) | `Google DNS` → block on `google dns` OR `google` head noun |
| v0.6 (v3.8.0) | Word-boundary regex `\b{term}\b` + scope filter + regex parser | `chrome` no longer matches `chromebook`; `never install/deploy/run/rely on` recognized |

### Decree enforcement on real intents

```bash
$ node apps/browser/decree-bridge.js check "configure DNS with Google 8.8.8.8"
{
  "compliant": false,
  "violations": [{
    "decree_seq": 3,
    "decree_text": "never use Google DNS",
    "violation": "intent contains prohibited term: google",
    "matched_term": "google"
  }],
  "laws_checked": 7
}

$ node apps/browser/decree-bridge.js check "configure DNS with local unbound"
{"compliant": true, "violations": [], "laws_checked": 7}  # v0.5+ FIX — was false positive in v0.4

$ node apps/browser/decree-bridge.js check "buy a chromebook"
{"compliant": true, "violations": [], "laws_checked": 7}  # v0.6 FIX — \bchrome\b doesn't match chromebook
```

## What you can take

- **The whole repo** — fork it, replace `rtynbirf` with your handle, run `make verify`, you have your own Polymath OS.
- **`runtime/` alone** — SINGULYAR EIR v0.6 is self-contained, MIT-licensed, zero dependencies (Python 3.10+, standard library only). Drop into your project as the execution kernel.
- **`runtime/src/decree_log.py`** — DecreeLog class (SQLite WAL, hash-chained, append-only). Use as a standalone supreme-law layer in any project.
- **`apps/browser/decree-portal.html` + `decree-bridge.js`** — drop-in decree portal UI with Node bridge to Python DecreeLog.
- **Individual ADRs** — each is self-contained, with Context/Decision/Consequences. Copy the pattern.
- **The hardened RUNBOOK template** — the procedure template (ПРЕДУСЛОВИЯ → ПРЕДПРОСМОТР → ДЕЙСТВИЕ ⛔ → ПРОВЕРКА → ЕСЛИ УПАЛО → СЛЕД) works for any ops team.
- **The Sovereignty Registry pattern** — the two-tier dependency registry (sovereign core vs rented services vs forbidden benefactors) works for any project that wants to think about vendor lock-in.
- **Token hygiene pattern** — `scripts/check_token_hygiene.py` (234 lines) scans for plaintext GitHub PATs in shell scripts. Drop into any Python project.

## Why this exists

This repo is the answer to: *"Какое новое свойство возникает, когда git, AI-agents, base знаний, CI/CD и recovery соединены именно так — и как доказать, что это не просто красивое название?"*

The answer is **Layer 5 (SINGULYAR EIR)** — an execution kernel that:
- preserves a person's declared intent across interchangeable execution methods
- makes every completion claim depend on inspectable evidence of the required final state
- treats "cannot tell" as a first-class outcome (`UNKNOWN`), not as a silent `CONFIRMED`
- (v3.6.0+) enforces the human's decrees BEFORE any policy check (supreme law above code)

Emergence here is a **falsifiable hypothesis**, not a slogan. The ablation ladder B0→B3→EIR in `runtime/docs/EXPERIMENT_RESULTS.md` shows that each link removes a specific class of failure. The test `test_each_ablation_link_is_load_bearing` checks that each link is actually load-bearing. The price: in two scenarios, the kernel honestly answers `UNKNOWN` instead of "probably worked".

## Documentation map

| Document | Purpose |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Mental model: 5+1 layers + Sovereignty Registry + falsifiable self-* + Decree as supreme law |
| [`ТЗ_Polymath_OS_v3.7.0.md`](./ТЗ_Polymath_OS_v3.7.0.md) | **Consolidated ТЗ (technical spec, 16 sections, 47.9 KB)** — comprehensive |
| [`ROADMAP_v3.7.0.md`](./ROADMAP_v3.7.0.md) | **Consolidated roadmap (history of 28 releases + 30/90/180/365-day vision)** |
| [`TZ.md`](./TZ.md) | Original technical spec (Layer 1-4 view, pre-decree) |
| [`ROADMAP.md`](./ROADMAP.md) | Phased plan (Phase 0-4, exit-gate based) |
| [`CHANGELOG.md`](./CHANGELOG.md) | Release history (v1.0.0 → v3.8.0, all changes logged) |
| [`MANIFEST.json`](./MANIFEST.json) | Root manifest (ADR-0020 — manifest-driven architecture) |
| [`docs/AUDIT_RESPONSE.md`](./docs/AUDIT_RESPONSE.md) | Audit findings A1-A11 → ADR → action mapping |
| [`docs/adr/`](./docs/adr) | **28 ADRs (0001-0028)** — every architectural decision |
| [`docs/MANIFESTO.md`](./docs/MANIFESTO.md) | System manifesto (4 theses: PID=1, PAROLE>LANGUE, LFS, security context) |
| [`docs/SOVEREIGNTY_CONTRACT.md`](./docs/SOVEREIGNTY_CONTRACT.md) | Sovereignty contract (Tier 1/2/3 dependency classification) |
| [`docs/01-principles.md`](./docs/01-principles.md) | 18 principles (constitution) |
| [`docs/02-repo-structure.md`](./docs/02-repo-structure.md) | Layer 1 details |
| [`docs/03-ai-workflows.md`](./docs/03-ai-workflows.md) | Layer 2 details |
| [`docs/04-second-brain.md`](./docs/04-second-brain.md) | Layer 3 details |
| [`docs/05-devex-ci.md`](./docs/05-devex-ci.md) | Layer 4 details |
| [`docs/runbook/RUNBOOK.md`](./docs/runbook/RUNBOOK.md) | Hardened operations runbook |
| [`runtime/README.md`](./runtime/README.md) | Layer 5: SINGULYAR EIR v0.6 |
| [`runtime/docs/TECHNICAL_SPEC.md`](./runtime/docs/TECHNICAL_SPEC.md) | EIR technical spec |
| [`runtime/docs/DECREE_PRODUCTION_DEMO.md`](./runtime/docs/DECREE_PRODUCTION_DEMO.md) | Production decree demo (v3.7.0+) |
| [`runtime/docs/EXPERIMENT_RESULTS.md`](./runtime/docs/EXPERIMENT_RESULTS.md) | Ablation B0→B3→EIR |
| [`runtime/docs/LIMITATIONS.md`](./runtime/docs/LIMITATIONS.md) | What's NOT proven (honesty) |
| [`runtime/docs/THREAT_MODEL.md`](./runtime/docs/THREAT_MODEL.md) | Threat model |
| [`runtime/docs/AUDIT_POLYMATH.md`](./runtime/docs/AUDIT_POLYMATH.md) | The audit that drove the fixes |
| [`apps/browser/decree-portal.html`](./apps/browser/decree-portal.html) | Decree Portal UI (HTML/JS, browser + Electron) |
| [`apps/browser/decree-bridge.js`](./apps/browser/decree-bridge.js) | Node bridge: HTML UI ↔ Python DecreeLog ↔ SQLite |
| [`apps/browser/electron/`](./apps/browser/electron/) | Electron desktop wrapper (v3.7.0+) |
| [`SECURITY.md`](./SECURITY.md) | Security policy + **Token hygiene best practices (v3.8.0)** |

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Trunk-based, conventional commits, ADR-driven.

Every PR must pass `make verify`. If your PR adds a new architectural decision, you must add an ADR. If your PR adds a new claim to README, you must add a check to `scripts/check.py`.

## License

MIT — see [`LICENSE`](./LICENSE). Take it. Use it. Fork it. The sovereign core (git, markdown, SQLite, age, Nix) is yours forever — works without network, without accounts, without permission.

## Origin

This repo was built through an iterative dialogue:

1. **v0.1**: User asked for 100 file formats → 100 messengers → 100 portable apps (philosophical exploration of "human = system")
2. **v0.2**: User delegated polymath audit → 4 parallel research agents → synthesis into Polymath OS (4 layers + cross-cutting)
3. **v0.3-v1.1.0**: SINGULYAR EIR v0.3 audit applied → 11 audit findings fixed via 12 ADRs → SINGULYAR integrated as Layer 5 → repo promoted from "report" to "open-source ideal repo" with `make verify` contract
4. **v3.0.0-v3.5.0**: Liberation roadmap (DNS unbound + Cloudflare-free + Chrome-free + sovereign browser) → Decree Portal UI + ADR-0022 + MANIFEST.json
5. **v3.6.0 (OPERATIONAL)**: Decree Bridge wired — 7 foundational decrees recorded in real SQLite. Runtime.set_decree_log() implemented. check_compliance() works on real decrees. v0.5 NLP phrase matching (LIST/PHRASE/SINGLE/DEFAULT classification).
6. **v3.7.0 (Multiagent)**: 4 parallel subagent tracks — production decree demo + v0.5 NLP + Electron desktop wrapper + CI steps 8+ green. All 4/4 CI checks green.
7. **v3.8.0 (CLEAN-UP)**: v0.6 word-boundary regex matching (fixes `chrome` ↔ `chromebook` false positive) + decree scope filtering + regex prohibition parser + token hygiene automation (`scripts/check_token_hygiene.py` + claim #23 + SECURITY.md best practices). 24/24 verify, 220/220 tests, 5/5 CI green.
8. **v3.9.0 (DOCS SYNC)**: All documentation synced with reality — README badges, MANIFEST counts, ARCHITECTURE ADR table (22 → 28), TZ.md layer count.
9. **v3.10.0 (СИНГУЛЯР synthesis)**: ADR-0023 Agent Card Protocol + ADR-0024 Decree-Enforced Multi-Agent Communication. Decree system теперь работает в 2 направлениях (inbound in-process + outbound).
10. **v3.11.0 (Symmetric СИНГУЛЯР)**: ADR-0025 Decree-Driven A2A Client (outbound decree gate BEFORE network request). v0.6.1 regex extension (+send/share/transmit/expose verbs). Decree Portal UI multi-agent view. Agent Card schema validation (claim #24). 4/5 CI green.
11. **v3.12.0 (Meta-architecture)**: ADR-0026 Decree-Driven ADR Amendment Mechanism (closes ADR-0016 target-for-v1.0 ahead of schedule). AdrAmender class. New 'amendment' decree category. 4 patterns: create/amend/supersede/deprecate. СИНГУЛЯР extends to 3 layers (runtime + meta-architecture + audit).
12. **v3.13.0 (HTTP inbound)**: ADR-0027 Decree-Enforced HTTP JSON-RPC Server (stdlib only). .well-known/agent.json теперь actually serves a real JSON-RPC endpoint. Closes ADR-0023 endpoint loop. СИНГУЛЯР полный в 4 направлениях.
13. **v3.14.0 (Decree revocation)**: ADR-0028 Decree Supersession Mechanism. Decrees can now be revoked via supersession decree category. Decree system CLOSED under all natural operations (issue + enforce + supersede). Append-only + revocable, no contradiction.
14. **v3.15.0 (ALL GAPS CLOSED)**: Production DB reset to 7 decrees (was 8 from manual test). MANIFEST.json synced (v3.14.0, adrs=28, tests=220, ci_checks=24, expanded features). ARCHITECTURE.md ADR table 28 rows. README "7 foundational + N" instead of stale "7". AgentMeshServer real Runtime integration (replace _demo_execute_fn). AdrAmender production use (create amendments.log). Audit of sovereignty_drill + cross-repo-governance workflows. Electron install test.
15. **v3.20.0 (FULLY OPERATIONAL, current)**: ADR-0031 decree cryptographic signing — pure-python Ed25519 (RFC 8032, stdlib only), ssh-keygen-compatible keys, signatures over chain hash in append-only `decree_signatures` table. Honest verification (integrity_failed/not_signed/signature_mismatch). provenance_report(). 20 tests. make verify 25→26 claims (26/26 green). Production decrees signed by PID=1 key (7/7, chain OK, trust anchor VERIFIED). FIXED: CI red on main (biome lint in decree-bridge.js), Electron 31 portal sandbox (npm start showed no decrees — sandbox:false in main.js).

Worklog: `/home/z/my-project/worklog.md` (10+ Task IDs across multiple release sessions — full audit trail of every change).
