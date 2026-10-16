# docs/ECOSYSTEM.md — The rtynbirf Ecosystem Map

**Date**: 2026-10-16 (v2.1.0)
**Status**: Living document
**Purpose**: Map all 4 repos of the rtynbirf sovereign media platform + their
roles + their current versions + their Sovereignty Tier per ADR-0002.

Per singulyar AGENTS.md закон 7: "Один факт — одно место." This document
is the **single source of truth** for which repo does what.

## The 4 repos

```
                    ┌─────────────────────────────────┐
                    │         rtynbirf (human)          │
                    │           PID = 1                 │
                    └──────┬──────────┬──────────┬─────┘
                           │          │          │
              ┌────────────┘    ┌─────┘    ┌─────┘
              ▼                 ▼          ▼
     ┌────────────────┐ ┌──────────┐ ┌─────────────────┐
     │   singulyar    │ │ singulyar │ │  cell65-host    │
     │   (product)    │ │   -llm   │ │ (infrastructure) │
     │   2.3 GB       │ │  466 MB  │ │     66 KB       │
     │   17 modules   │ │ Qwen2.5  │ │  sovereign-node  │
     │   44 doors     │ │  -0.5B   │ │  3 transports    │
     │   такт v11.50  │ │  GGUF    │ │  VLESS+Reality   │
     │   «НАПОЛНЕНИЕ» │ │  v0.6    │ │  +Hysteria2      │
     └───────┬────────┘ └────┬─────┘ └────────┬────────┘
             │               │                │
             └───────────────┼────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   polymath-os    │
                    │   (OS / intent)   │
                    │    532 KB        │
                    │   16 ADRs        │
                    │   3 adapters     │
                    │   9 patterns     │
                    │   v2.0.0         │
                    └──────────────────┘
```

## Repo roles

| Repo | Role | Sovereignty Tier | What it IS |
|---|---|---|---|
| **singulyar** | Product | Tier 1 (offline core) + Tier 2 (Nostr/STUN/mempool) | Offline karaoke universe PWA — 64 songs, 200 languages, 17 modules, 44 doors. One HTML = entire platform (offline). Air-gapped WebRTC, ECDSA identity, local LLM. |
| **singulyar-llm** | Model | Tier 1 (weights Apache-2.0) + Tier 2 (HuggingFace CDN for first download) | Qwen2.5-0.5B-Instruct GGUF q4_k_m, 6 parts ≤100MB, instruction layer (ПРАВИЛА_СИНГУЛЯРА.txt, 17 rules v0.6). Weights run in browser via wllama (WASM). |
| **cell65-host** | Infrastructure | Tier 1 (sing-box binary) + Tier 2 (VPS, Cloudflare, DDNS) | Personal anti-censorship kit: 3 transports (VLESS+Reality, VLESS+WS+CF, Hysteria2) with auto-rotation, RU/non-RU split. |
| **polymath-os** | OS / Intent | Tier 1 (Python stdlib, SQLite, git, markdown) + Tier 2 (GitHub Actions, cosign, Pages) | Sovereign media-OS umbrella: SINGULYAR EIR v0.3 (intent-preserving kernel), 3 real adapters (LLMLocal, HTTP, WebRTC), 16 ADRs, 9 machine-checked patterns, 4 audit documents (3 levels), weekly sovereignty drill. |

## Current versions

| Repo | Version | Last push | Status |
|---|---|---|---|
| singulyar | такт v11.50 «НАПОЛНЕНИЕ», s15-orkestrator-v200 | 2026-10-16T09:35:32Z | live, 2.3 GB |
| singulyar-llm | v0.6 (106 voice commands, 17 rules) | 2026-10-15T03:50:22Z | live, 466 MB |
| cell65-host | (no version tag, sovereign-node/ README) | 2026-10-11T08:02:22Z | live, 66 KB |
| polymath-os | v2.0.0 (16 ADRs, 3 adapters, 20 CI checks) | 2026-10-16T16:57:01Z | live, 532 KB |

## Dependencies between repos

```
singulyar ──────depends on──────► singulyar-llm (апстрим мозгов Малыша)
singulyar ──────depends on──────► cell65-host (sovereign-node for network access)
polymath-os ────audits──────────► singulyar (AUDIT_SINGULYAR.md, 90 findings)
polymath-os ────ports from──────► singulyar (llm.mjs → llm_local_adapter.py, ·17 ЗАЛ → webrtc_adapter.py)
polymath-os ────governs─────────► (all repos, via cross-repo CI — future)
```

## Issues filed from polymath-os audit → singulyar

Per Gate-5 (third-level recursive audit), 5 critical findings filed as issues:

| Issue | Finding | Severity | singulyar issue |
|---|---|---|---|
| S1 | тэглайн «без интернета» vs реальная структура | [док] | [#6](https://github.com/rtynbirf/singulyar/issues/6) |
| S18 | S15_MAX=140 < S15_CORE.length=168 — ядро вытесняется | [док] | [#7](https://github.com/rtynbirf/singulyar/issues/7) |
| S26 | ·17 ЗАЛ CSP blocks wss: Nostr — КРУГ dead | [док] | [#8](https://github.com/rtynbirf/singulyar/issues/8) |
| S27 | ·17 ЗАЛ innerHTML XSS via peer name | [док] | [#9](https://github.com/rtynbirf/singulyar/issues/9) |
| S37 | ·19 ЧЕЛОВЕК ECDSA identity lost on browser clearing | [док] | [#10](https://github.com/rtynbirf/singulyar/issues/10) |

## The bridge (future — Python↔JS)

polymath-os has Python ports of singulyar's JS adapters:
- `runtime/src/adapters/llm_local_adapter.py` ← port of `singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs` (·21 ОБЩЕНИЕ)
- `runtime/src/adapters/webrtc_adapter.py` ← port of `singulyar/СИНГУЛЯР_17_ЗАЛ.html` (·17 ЗАЛ)

Future: singulyar calls polymath-os kernel (via Pyodide/WASM in browser, or via subprocess on server). The kernel routes Intent → Capability → Adapter → Observation → Evidence across the language boundary.

This proves the SINGULYAR EIR thesis at ecosystem level: **preserve intent across changes in execution method** (JS → Python → JS).

## The governance layer (future — cross-repo CI)

polymath-os as governance layer:
- Weekly check: singulyar AGENTS.md 7 «Незыблемое» laws still hold
- Weekly check: singulyar такт ritual (8 stages) was followed
- Weekly check: singulyar "одна правда" block matches `data/versions.json`
- Weekly check: singulyar cache generation (`s15-orkestrator-vNN`) is current

This makes polymath-os the "judicial branch" of the ecosystem — it doesn't command singulyar, but verifies singulyar follows its own rules.

## The human's path through the ecosystem

```
Human says "исправить S18"
  ↓
polymath-os SINGULYAR EIR kernel
  ↓
Intent: fix S18 in singulyar
  ↓
Capability: git.create_branch (singulyar repo)
  ↓
Adapter: GitAdapter (tooling/agents/mcp/git_adapter.py)
  ↓
Branch created: fix/s18-cache-eviction
  ↓
Capability: code.fix (sw15.js, S15_MAX → 200)
  ↓
Adapter: FilesystemAdapter
  ↓
File modified
  ↓
Capability: git.commit + git.push
  ↓
Adapter: GitAdapter
  ↓
PR created: github.com/rtynbirf/singulyar/pull/N
  ↓
Verification: make verify (singulyar tests) + sovereignty drill
  ↓
Evidence: PASS → kernel confirms CONFIRMED
  ↓
Human reviews + merges
```

This is the full "управляемая эмерджентная непрерывность" thesis proven at ecosystem level: **the human's intent (fix S18) is preserved across changes in execution method (from human voice to Python kernel to JS file to git commit to PR).**

## References

- ADR-0002 (Sovereignty Registry) — defines Tier 1/2/3 for all repos
- ADR-0012 (SINGULYAR EIR as Layer 5) — the kernel that preserves intent
- ADR-0016 (Self-rewriting ADR mechanism) — how this document can be amended
- AUDIT_SINGULYAR.md — the 90 findings that connect polymath-os to singulyar
- SOVEREIGNTY_CONTRACT.md — the 7 contracts that govern the ecosystem
- singulyar AGENTS.md — the 7 «Незыблемое» laws for the product repo
- singulyar `data/versions.json` — single source of truth for singulyar numbers


## Cross-repo execution — FIRST REAL PR (v2.3.0) ✨

polymath-os's SINGULYAR EIR kernel drove a real code fix in singulyar:

| Step | What | Where |
|---|---|---|
| Audit | Found S18 (S15_MAX=140 < S15_CORE.length=168) | polymath-os/docs/AUDIT_SINGULYAR.md |
| Issue | Filed as #7 in singulyar | https://github.com/rtynbirf/singulyar/issues/7 |
| Branch | Created fix/s18-cache-eviction | singulyar repo |
| Commit | S15_MAX 140→200 | sw15.js, commit ccfe3dcafe |
| PR | Pull request #11 | https://github.com/rtynbirf/singulyar/pull/11 |

The full circuit: **audit → issue → kernel → GitAdapter → branch → commit → PR**.

This proves the «управляемая эмерджентная непрерывность» thesis at execution level:
the human's intent (expressed through polymath-os's audit) reached singulyar (the product)
through a real code fix, across repo boundaries, across language boundaries
(Python audit → JS fix), across concept boundaries (audit → issue → code → PR).

## Ecosystem integration path — COMPLETE

| Step | What | Status |
|---|---|---|
| 1 | Audit → singulyar issues (5 critical filed) | ✅ v2.1.0 |
| 2 | ECOSYSTEM.md (map of 4 repos) | ✅ v2.1.0 |
| 3 | Python↔JS bridge (subprocess JSON protocol) | ✅ v2.2.0 |
| 4 | Cross-repo CI (governance workflow) | ✅ v2.3.0 |
| 5 | Human intent → cross-repo execution (PR #11) | ✅ v2.3.0 |

All 5 steps complete. The ecosystem is integrated.

## ALL 5 CRITICAL FINDINGS MERGED (v2.5.0) ✨

| Finding | Issue | PR | Status |
|---|---|---|---|
| S18: S15_MAX fix | #7 | PR #11 | ✅ MERGED |
| S1: honest tagline | #6 | PR #13 | ✅ MERGED |
| S26: CSP Nostr allowlist | #8 | PR #14 | ✅ MERGED |
| S27: innerHTML→textContent | #9 | PR #15 | ✅ MERGED |
| S37: data-clearing warning | #10 | PR #16 | ✅ MERGED |

All 5 critical findings from AUDIT_SINGULYAR.md are FIXED and LIVE in singulyar main.
