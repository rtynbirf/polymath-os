# ROADMAP — Polymath OS

> **4 фазы × ~22 дня = 90 дней до production-ready.**
> LFS-style: каждая фаза — слой бутстрапа, без которого следующая невозможна.

---

## Фаза 0 — Foundation (Дни 1-7)

**Цель:** чистый git-каркас, ничего лишнего.

### Day 1-2: Repo init
- [ ] `git init -b main` + структура каталогов (apps/packages/tooling/docs/vault/infra)
- [ ] `README.md` (landing page, по Preston-Werner pattern)
- [ ] `LICENSE` (MIT)
- [ ] `.editorconfig`, `.gitignore` (github/gitignore boilerplate)
- [ ] `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- [ ] GitHub repo created, branch protection на `main` (require PR + linear history)
- [ ] `.github/CODEOWNERS` (даже если solo — это self-governance)

### Day 3-4: Package manager + monorepo
- [ ] `corepack enable`, `pnpm init`
- [ ] `pnpm-workspace.yaml` (apps/*, packages/*, tooling/*)
- [ ] `turbo.json` (build/lint/test/typecheck/dev pipelines с `dependsOn`)
- [ ] `tsconfig.base.json` (strict TS)
- [ ] `packages/config-tsconfig/` (base + nextjs)
- [ ] `packages/config-eslint/` (flat config, shared rules)
- [ ] `.changeset/config.json` (independent versioning)

### Day 5-7: CI baseline + Hooks
- [ ] `.github/workflows/ci.yml`: checkout + pnpm install (frozen-lockfile) + lint + typecheck + test + build
- [ ] `commitlint` + `commitizen` + `lefthook.yml` (pre-commit: lint-staged; commit-msg: commitlint)
- [ ] `action-semantic-pull-request` для PR title
- [ ] Conventional Commits enforced
- [ ] `act -W .github/workflows/ci.yml` — локально работает

**Результат фазы 0:** пустой монорепо с зелёным CI на main.

---

## Фаза 1 — Bootstrap (Дни 8-21)

**Цель:** dev environment, который ставится одной командой.

### Day 8-10: Dev shell (Nix)
- [ ] `infra/flake.nix` (go, tilt, k3s, cosign, trivy, semgrep, sops, age, 1password-cli)
- [ ] `direnv` + `nix-direnv` setup, `.envrc` с `use flake`
- [ ] Документация в `docs/05-devex-ci.md` (как добавить пакет в flake)

### Day 11-13: Dotfiles (chezmoi)
- [ ] Отдельный репо `github.com/USER/dotfiles` (chezmoi source)
- [ ] `.chezmoi.toml.tmpl`, `.chezmoiscripts/run_once-install-packages.sh.tmpl`
- [ ] `dot_zshrc.tmpl`, `dot_config/nvim/`, `dot_config/tmux/`, `dot_gitconfig.tmpl`
- [ ] `private_dot_secrets/` (SOPS+age encrypted)
- [ ] CI в dotfiles-repo: `act -W` проверяет что `chezmoi apply` проходит на чистом образе

### Day 14-16: devcontainer + DevPod
- [ ] `.devcontainer/devcontainer.json` (image, features, postCreateCommand, forwardPorts)
- [ ] Tested in: VS Code, Cursor, DevPod (`devpod up .`), GitHub Codespaces
- [ ] Один `devcontainer.json` работает везде — это и есть идемпотентный dev env

### Day 17-19: Local dev loop (Tilt)
- [ ] `Tiltfile` (docker_build + live_update + k8s_yaml + port_forwards)
- [ ] `docker-compose.yaml` для non-K8s сервисов (Postgres, Redis)
- [ ] `Makefile` (bootstrap, dev, test, ci-local, sign)
- [ ] Tilt UI открывает hot-reload в kind/k3s

### Day 20-21: Secrets (SOPS + age)
- [ ] `age-keygen` (private key НЕ коммитится, хранится в 1Password)
- [ ] `.sops.yaml` (creation_rules: `secrets/.*\.yaml$`)
- [ ] `infra/environments/personal/secrets.sops.yaml` (пример с dummy values)
- [ ] Pre-commit hook: `gitleaks detect` (blocking)

**Результат фазы 1:** `git clone && chezmoi init --apply <dotfiles> && make bootstrap` → готовая среда.

---

## Фаза 2 — Integration (Дни 22-60)

**Цель:** 4 слоя системы начинают работать вместе.

### Day 22-28: Layer 1 — Repository structure full
- [ ] Apps scaffolded: `apps/web` (Next.js 15 via create-next-app), `apps/api` (Hono), `apps/garden` (Quartz v4)
- [ ] Packages: `packages/ui` (shadcn/ui based), `packages/db` (Drizzle + schema), `packages/utils`
- [ ] `tooling/generators` (plop templates: new-app, new-package)
- [ ] Changesets: `pnpm changeset` workflow, `.github/workflows/release.yml` (changesets/action)
- [ ] Branch protection: require status checks, merge queue, no bypass
- [ ] Dependabot config + Renovate alt (review)

### Day 29-35: Layer 2 — AI workflows
- [ ] MCP servers configured: filesystem, git, postgres, web-search (Ollama or local)
- [ ] Claude Code installed + configured (`CLAUDE.md` в корне репо)
- [ ] Aider config (`.aider.conf.yml`)
- [ ] Cursor workspace settings (`.cursorrules` + `.cursor/`)
- [ ] Ollama running locally: `ollama pull nomic-embed-text + qwen2.5:32b`
- [ ] Langfuse self-hosted (docker-compose) для трейсов
- [ ] promptfoo в CI: golden dataset regression на каждый agent prompt

### Day 36-42: Layer 3 — Second brain
- [ ] `vault/` structure (00-daily, 10-projects, ..., 60-permanent, 90-meta)
- [ ] `vault/90-meta/templates/` (permanent.md, daily.md, literature.md)
- [ ] Obsidian vault opens `vault/` as folder
- [ ] Plugins: Dataview, Templater, obsidian-git (auto-backup 10 min), Smart Connections, Copilot, Web Clipper, Excalidraw
- [ ] `.obsidian/` config: commit only `app.json`, `appearance.json`, `community-plugins.json`, `core-plugins.json`, `hotkeys.json` (NOT `workspace.json`)
- [ ] Copilot for Obsidian: provider=Ollama (local), VaultQA mode on
- [ ] Quartz v4 in `apps/garden`: symlink `content/` → `vault/60-permanent/` with filter on `publish: true`
- [ ] `.github/workflows/publish-garden.yml` → GitHub Pages on push to main

### Day 43-50: Layer 4 — DevEx/CI/IaC
- [ ] `.github-templates` repo (reusable workflows + composite actions)
- [ ] OIDC trust: GitHub Actions → AWS/GCP (no long-lived keys)
- [ ] `infra/tofu/` (modules: cloudflare-dns, hetzner-server, vault-cluster, unleash)
- [ ] `infra/compose.observability.yaml` (Grafana LGTM + Sentry/Glitchtip on personal VPS)
- [ ] OpenTelemetry SDK в apps/web + apps/api (traces→Tempo, logs→Loki, metrics→Mimir)
- [ ] Feature flags: Unleash self-hosted (docker-compose), `apps/web` использует Unleash SDK
- [ ] Testcontainers: integration tests поднимают Postgres/Redis в CI

### Day 51-60: Security hardening
- [ ] `trivy fs .` + `trivy image` в CI (blocking on HIGH/CRITICAL)
- [ ] `semgrep --config auto` (CI, non-blocking → blocking после grace period)
- [ ] CodeQL analysis (GitHub Advanced Security free для OSS)
- [ ] SBOM generation: `@cyclonedx/cyclonedx-npm` → `sbom.json`
- [ ] Cosign keyless signing (OIDC) для container images
- [ ] SLSA provenance: `slsa-framework/slsa-github-generator`
- [ ] Cosign attest SBOM (`cosign attest --predicate sbom.json --type cyclonedx`)
- [ ] Verify pipeline: `cosign verify` + `cosign verify-attestation` в deploy job

**Результат фазы 2:** все 4 слоя работают, но без production-нагрузки.

---

## Фаза 3 — Production (Дни 61-90)

**Цель:** real traffic, real feedback, real metrics.

### Day 61-70: Deploy + Observability
- [ ] `infra/tofu/environments/personal/main.tf` — production-stack
- [ ] ArgoCD или FluxCD (GitOps) деплой в k3s-кластер
- [ ] OTel collector → Tempo/Loki/Mimir
- [ ] Grafana dashboards: service overview, error rate, p95 latency, business KPIs
- [ ] Sentry alerts: error rate > 1%, new errors, regression
- [ ] Uptime monitoring: BetterStack (free tier)

### Day 71-80: AI workflows production
- [ ] Langfuse → production traces (online evals)
- [ ] promptfoo scheduled regression (daily, weekly)
- [ ] Braintrust (или Langfuse evals) → CI gating на changes в prompts
- [ ] MCP servers: codified, documented, registry-registered (если публичные)
- [ ] A2A-ready: если есть ≥2 агента — реализовать interop через A2A
- [ ] Prompt caching metrics: cache-hit-ratio per agent, $/1M tokens, p95 latency

### Day 81-85: Second brain → publish
- [ ] Quartz v4 site live на `garden.your-domain.com`
- [ ] Public subset: only `publish: true` notes
- [ ] Search: Quartz full-text + Smart Connections public version
- [ ] RSS/Atom feed для новых permanent notes
- [ ] Cross-link: ADR → vault/60-permanent note (bi-directional)

### Day 86-90: Documentation + Audit
- [ ] `docs/runbook/RUNBOOK.md` — incident response, rollback, on-call
- [ ] All ADRs (≥7) committed
- [ ] `docs/adr/template.md` обновлён
- [ ] Anti-fragility тест: clone на чистую VM, `chezmoi init --apply && make bootstrap && make dev` → работает
- [ ] Audit checklist (см. TZ.md §4) — все метрики зелёные
- [ ] v1.0.0 tag + GitHub Release с SBOM + cosign signature

**Результат фазы 3:** production-ready v1.0.0, эмерджентная система работает end-to-end.

---

## Критерии перехода между фазами

| Фаза → Фаза | Gate |
|---|---|
| 0 → 1 | `git clone` + `pnpm install` + `pnpm turbo run build` проходят на чистой машине без ошибок |
| 1 → 2 | `chezmoi init --apply && make bootstrap && make dev` открывает Tilt с hot-reload |
| 2 → 3 | Все 4 слоя документированы, ADR ≥7, `make ci-local` проходит, observability collect-ает метрики |
| 3 → Done | v1.0.0 tag + release с SBOM+cosign, audit checklist 100% зелёный |

## Мониторинг прогресса

- **Worklog:** `/home/z/my-project/worklog.md` (append-only, multi-agent shared)
- **Project board:** GitHub Projects v2 с колонками: To Do / In Progress / In Review / Done
- **Daily:** commit в `vault/00-daily/YYYY-MM-DD.md` (15-min review)
- **Weekly:** `vault/00-daily/week-YYYY-Www.md` (MOC update + retro)

## Что после v1.0.0

- Quarterly audit (см. ARCHITECTURE.md §7: self-audit)
- Migrate Quartz v4 → v5 (separate ADR when ready)
- Explore A2A protocol adoption wider
- Local-first experiments: Anytype или Loro CRDT для vault multi-device
- Bazel для тяжёлых полирепо-сценариев (если вырастет)
