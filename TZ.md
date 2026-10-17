# TZ — Техническое задание

> **Polymath OS: LFS-style rebuild личной операционной системы.**
> Цель: rebuild с нуля, без предсобранных бинарников, по лучшим мировым практикам 2024-2026.
>
> **Текущая версия: v3.8.0** (commit `3f279c0`, 2026-10-17). Полная консолидированная спецификация — в [`ТЗ_Polymath_OS_v3.7.0.md`](./ТЗ_Polymath_OS_v3.7.0.md) (47.9 KB, 16 разделов). Этот файл — историческая спецификация Layers 1-4, написанная до того, как Layer 5 (SINGULYAR EIR) и Decree Log были добавлены. Актуальная архитектура — в [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 1. Цели и задачи

### 1.1. Цель
Создать **единый self-bootstrapping репозиторий**, который объединяет:
- структуру монорепо (Layer 1)
- AI-рабочие процессы (Layer 2)
- личную базу знаний / second brain (Layer 3)
- devex / CI / IaC / dotfiles / observability (Layer 4)
- **execution kernel SINGULYAR EIR v0.6 (Layer 5, добавлен в v3.6.0+)** — runtime, который сохраняет намерение человека при смене исполнителя
- **Decree Log (supreme law layer, v3.6.0+)** — SQLite, hash-chained, append-only; воля человека = закон, выше ADR и кода (ADR-0021)
- cross-cutting: security, OTel, git, token hygiene (вертикальный слой)

Репозиторий должен быть **самодостаточным**: `git clone` + одна команда `make bootstrap` → готовое рабочее окружение на новой машине за ≤30 минут. После bootstrap: `make verify` → 23/23 PASS — открытый контракт с пользователем.

### 1.2. Задачи
1. Зафиксировать архитектурные принципы (**5+1 слоёв + Decree Log**) в ADR. На v3.8.0 — 22 ADRs (0001-0022).
2. Внедрить trunk-based development с merge queue + CODEOWNERS + branch protection.
3. Настроить CI: lint, typecheck, test, security scan, SBOM, cosign signing, SLSA provenance. На v3.8.0 — 5 CI check-runs (lint+typecheck+test+build+security, make verify, CodeQL JS, CodeQL Python, Build+SBOM+cosign+Release).
4. Внедрить Changesets для управления версиями в монорепо.
5. Настроить MCP-нативный AI-стек: Claude Code + Aider + Cursor + локальный fallback на Ollama. На v3.8.0 — 4 MCP adapters (filesystem, git, postgres, web_search).
6. Развернуть Obsidian vault с git-sync, Smart Connections, Copilot+Ollama.
7. ~~Инициализировать Quartz v4 для публикации digital garden.~~ **(done in v1.0.0)** — `apps/garden/`, default-deny filter (ADR-0009) + canary test.
8. Настроить chezmoi + age + 1Password CLI для dotfiles.
9. Развернуть self-host observability stack (Grafana LGTM + Sentry/Glitchtip).
10. Настроить OpenTofu для personal-cloud инфраструктуры.
11. **(v3.6.0+) Implement DecreeLog + Decree Portal + Runtime.set_decree_log()** — supreme law layer. 7 foundational decrees recorded. ✅ done.
12. **(v3.7.0+) Electron desktop wrapper** for Decree Portal. ✅ done.
13. **(v3.8.0) v0.6 word-boundary regex matching** + scope filter + token hygiene automation. ✅ done.
14. Внедрить feature flags (Unleash self-hosted) для trunk-based dev.

## 2. Технические требования

### 2.1. Repository structure

| Требование | Реализация |
|---|---|
| Single source of truth | git, всё в репо (код, конфиг, docs, infra) |
| Monorepo structure | `apps/`, `packages/`, `tooling/`, `docs/` (см. README.md) |
| Package manager | pnpm + workspaces (`pnpm-workspace.yaml`) |
| Build system | Turborepo (`turbo.json` с content-aware hashing + remote cache) |
| Versioning | Changesets, independent versioning, conventional commits |
| Branching | Trunk-based, `main` — единственная долгоживущая ветка |
| Merging | Squash-merge + linear history + GitHub Merge Queue |
| Code ownership | `.github/CODEOWNERS` — каждый path имеет explicit owner |
| Branch protection | Require PR, ≥1 approval, CODEOWNERS, status checks, no bypasses |
| Templates | GitHub Template Repo (для верхнеуровневого репо) + Copier для подшаблонов |

### 2.2. AI workflows

| Требование | Реализация |
|---|---|
| Tool interface | MCP (Model Context Protocol) — все инструменты как MCP-серверы |
| Agent orchestration | Single-agent baseline (Anthropic pattern). Multi-agent — только при обоснованной необходимости |
| Coding agent primary | Claude Code (terminal-native, repo-aware) |
| Coding agent IDE | Cursor (Composer multi-file) |
| Coding agent git-native | Aider (transparent diffs) |
| Local LLM fallback | Ollama + Qwen 2.5 / Llama 3.3 / gpt-oss (privacy-tasks) |
| Embeddings | `nomic-embed-text` через Ollama (локально, без облака) |
| Eval in CI | promptfoo (golden dataset regression) + Langfuse (production traces) |
| Prompt caching | Anthropic explicit `cache_control` + OpenAI automatic — проектировать под cache-hit |
| Context engineering | Явные 4 подсистемы: working / reference (RAG over MCP) / episodic / compression |
| Interop | A2A protocol (Google) — если несколько агентов разных вендоров |
| Anti-patterns | Prompt spaghetti, unmanaged context, tool sprawl, multi-agent без причины |

### 2.3. Second brain / PKM

| Требование | Реализация |
|---|---|
| Source format | Plain markdown (читается `cat`-ом через 10 лет) |
| Sync | git (obsidian-git plugin, auto-backup 10 min) |
| Editor | Obsidian (primary GUI) + Foam (VSCode alt) |
| Note types | Fleeting (≤48ч) → Literature (своими словами) → Permanent (atomic) |
| Org pattern | PARA (folders) + MOC (Maps of Content, Nick Milo) |
| Capture | Apple Notes / Drafts / AudioPen → `00-daily/## Inbox` |
| Retrieval | Dataview (SQL-like) + Smart Connections (semantic, local) |
| RAG | Copilot for Obsidian + Ollama VaultQA mode (полностью офлайн) |
| Publish | Quartz v4 → GitHub Pages (фильтр по `publish: true` в frontmatter) |
| Rituals | Daily (10+10 min) + Weekly (30 min) + Monthly (2ч) + Quarterly (полдня) |
| Anti-fragility | Раз в полгода: открыть vault без Obsidian → должно работать |

### 2.4. DevEx / CI / IaC

| Требование | Реализация |
|---|---|
| CI platform | GitHub Actions (reusable workflows + composite actions в `.github-templates`) |
| Local CI | `act -W .github/workflows/ci.yml` — то же, что в CI |
| Secrets | SOPS + age (git-ops) + Doppler (CI injection); OIDC trust (no long-lived PATs) |
| Static analysis | Semgrep (code) + Trivy (images/fs) + gitleaks (secrets in git) + Ruff/Biome (lint/format) |
| Supply chain | CycloneDX SBOM + cosign keyless signing + SLSA Level 2+ provenance |
| IaC | OpenTofu (Terraform fork, drop-in) + Pulumi (если нужен real-language) |
| Dev shell | Nix Flakes + direnv (одинаковая среда на macOS/Linux/WSL2) |
| Dotfiles | chezmoi + age + 1Password CLI (`chezmoi init --apply` на новой машине) |
| Dev env | devcontainer.json (Codespaces/DevPod/Cursor/VS Code — один spec) |
| Local K8s | Tilt + kind/k3s/minikube + Testcontainers |
| Observability | OpenTelemetry SDK в каждом сервисе → Grafana LGTM (self-host) + Sentry/Glitchtip |
| Feature flags | Unleash (self-hosted) для trunk-based dev |
| Deployment | GitOps (ArgoCD/FluxCD) или `helm upgrade --install` из CI на merge в main |

## 3. Структура репозитория (каркас)

```
polymath-os/
├── apps/
│   ├── web/                # Next.js 15
│   ├── api/                # Hono/Express
│   └── garden/             # Quartz v4 (digital garden)
├── packages/
│   ├── ui/                 # shadcn-based design system
│   ├── config-eslint/
│   ├── config-tsconfig/
│   ├── db/                 # Drizzle schema + client
│   └── utils/
├── tooling/
│   ├── generators/         # plop-based scaffolding
│   └── codemods/
├── docs/
│   ├── 01-principles.md
│   ├── 02-repo-structure.md
│   ├── 03-ai-workflows.md
│   ├── 04-second-brain.md
│   ├── 05-devex-ci.md
│   ├── adr/
│   │   ├── 0001-record-architecture-decisions.md
│   │   ├── 0002-monorepo-turborepo.md
│   │   └── ...
│   └── runbook/
│       └── RUNBOOK.md
├── vault/                  # Obsidian second brain (git-synced)
│   ├── 00-daily/
│   ├── 10-projects/
│   ├── 20-areas/
│   ├── 30-resources/
│   ├── 40-archive/
│   ├── 50-literature/
│   ├── 60-permanent/
│   └── 90-meta/
├── infra/                  # OpenTofu + Nix flake
│   ├── tofu/
│   │   ├── modules/
│   │   └── environments/
│   ├── flake.nix
│   └── compose.observability.yaml
├── .changeset/
├── .devcontainer/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── release.yml
│   │   └── publish-garden.yml
│   ├── CODEOWNERS
│   └── PULL_REQUEST_TEMPLATE.md
├── .vscode/
├── ARCHITECTURE.md
├── TZ.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── SECURITY.md
├── Makefile
├── turbo.json
├── pnpm-workspace.yaml
├── package.json
├── tsconfig.base.json
├── .editorconfig
├── .gitignore
└── README.md
```

## 4. Критерии приёмки

| Критерий | Метрика |
|---|---|
| Bootstrap time | ≤30 минут от `git clone` до готового dev-shell на новой машине |
| CI runtime | ≤5 минут для PR (lint+typecheck+test на cached) |
| Local CI parity | `act -W` воспроизводит 100% шагов CI |
| Coverage | ≥80% line coverage на packages/* |
| Supply chain | 100% releases имеют SBOM + cosign signature + SLSA Level 2+ |
| Secret hygiene | 0 secrets in git (gitleaks в CI — blocking) |
| Vault sync | Auto-commit каждые 10 min, push на GitHub private repo |
| Vault anti-fragility | Vault открывается без Obsidian (в VSCode+Foam или `less`) — каждые 6 мес |
| Eval coverage | ≥1 golden dataset на каждый production agent |
| Observability | 100% сервисов инструментированы OTel SDK |
| Reversibility | `make destroy` откатывает IaC ≤5 минут |
| Documentation | ADR на каждое значимое решение (≥7 initial ADRs) |

## 5. Non-goals (что не делаем)

- **Не** строим kernel-space OS. Это пользовательский layer.
- **Не** поддерживаем Windows native (только WSL2). Цель — Unix-подобные среды.
- **Не** делаем «plug-and-play installer». LFS-style = требует понимания.
- **Не** поддерживаем legacy-стек (yarn classic, npm <9, Node <20).
- **Не** делаем фреймворк для других. Fork-ни, но не как npm-пакет.
- **Не** ставим Docker Desktop (используем colima / podman / Linux native).

## 6. Риски и митигация

| Риск | Митигация |
|---|---|
| Nix learning curve | Документация в `docs/05-devex-ci.md` + flake.nix с комментариями |
| Obsidian plugin sprawl | Белый список 7 essential плагинов (Dataview, Templater, obsidian-git, Smart Connections, Copilot, Web Clipper, Excalidraw) |
| MCP-сервер разрыв | При разрыве — fallback на ad-hoc function definitions (задокументировано в ADR) |
| Cosign keyless outage | Backup: cosign с keypair (ключи в 1Password, не в git) |
| GitHub Actions outage | Woodpecker CI self-hosted как backup (Forgejo-runner совместимый с GHA-синтаксисом) |
| Quartz v4 breaking change | Pin Quartz v4.x, миграция на v5 — отдельным ADR |

## 7. Сроки

См. `ROADMAP.md` — 4 фазы по 22-23 дня, итого 90 дней до production-ready.

## 8. Ссылки

- Исходные исследования: `/home/z/my-project/research/` (4 отчёта по 2500-3500 слов каждый)
- Worklog: `/home/z/my-project/worklog.md`
- ADR folder: `docs/adr/`
- Runbook: `docs/runbook/RUNBOOK.md`
