# Repo Structure — Layer 1

> Best-in-class практики для monorepo / version control / templates (2024-2026).
> Ссылки на источники в `TZ.md` §8 и в research-отчётах.

---

## Принципы

1. **Repository as a single source of truth** — всё в git: код, конфиг CI, IaC, docs, политики, рунбуки.
2. **Trunk-based development** как дефолт. GitFlow — только для boxed-release on-prem.
3. **Linear history + squash-merge** — `git log` читается как narrative.
4. **Code ownership** — каждый path имеет explicit owner в `CODEOWNERS`.
5. **Documentation-driven design** — README-first, ARCHITECTURE.md, ADR, RUNBOOK.
6. **Supply chain integrity по умолчанию** — SBOM + SLSA + cosign.
7. **Automation over discipline** — правило в коде = blocking.

## Структура

См. `TZ.md` §3 и `README.md` — каркас `apps/packages/tooling/docs/vault/infra`.

### apps/ vs packages/

- `apps/` — деплоящиеся приложения (умеют иметь `next build`, `Dockerfile`, deploy pipeline).
- `packages/` — переиспользуемые пакеты (имеют `package.json` с `"name": "@scope/ui"`, могут публиковаться или линковаться).
- `tooling/` — generators, codemods, scaffolding.

### Turborepo pipeline

```json
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**", ".next/**"] },
    "lint": {},
    "typecheck": {},
    "test": { "dependsOn": ["^build"], "outputs": ["coverage/**"] },
    "dev": { "cache": false, "persistent": true }
  }
}
```

### Changesets workflow

```bash
pnpm changeset                       # создать changeset в PR
git add .changeset/*.md              # закоммитить changeset рядом с кодом
# После merge в main → changesets/action создаёт "Version Packages" PR
# Merge Version PR → триггерит publish
pnpm publish -r --filter "@scope/*" --provenance
```

## Branch protection (один systemic блок)

```gitignore
# .github/CODEOWNERS
*                          @USER

/apps/web/                  @USER
/apps/api/                  @USER
/packages/ui/               @USER
/packages/db/               @USER
/.github/                   @USER
/infra/                     @USER
/docs/adr/                  @USER
```

Branch protection rule на `main`:
- ✅ Require PR with ≥1 approval (CODEOWNERS required для затронутых путей)
- ✅ Require status checks: lint, typecheck, test, build, security-scan
- ✅ Require conversation-resolution
- ✅ Require linear history (force-rebase)
- ✅ Require merge queue
- ✅ Do not allow bypassing (даже для admins — для security-critical)

## ADR-паттерн

```markdown
# ADR-NNNN: <название решения>

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by ADR-XXXX
**Deciders:** @users

## Context
Зачем нужно решение. Что было. Какие альтернативы рассматривались.

## Decision
Что решили.

## Consequences
- Positive: ...
- Negative: ...
- Neutral: ...
```

ADR — immutable после Accepted. Новые решения → superseding ADR со ссылкой на старый.

## Anti-patterns

- GitFlow в новом продукте (зарезервированные ветки `develop`, `release/*`)
- Long-lived feature branches (>3 дней)
- Вручную поддерживаемый `CHANGELOG.md` (забывается в 80% PR'ов)
- Документация вне репозитория (Confluence / Notion — умирает за 6 мес)
- `README.md` = installation guide на 300 строк (должен быть landing page)
- Нет `CODEOWNERS` — review у случайных людей
- Merge commits без squash — шум в `git log`
- Прямой push в `main` — даже для админов
- Lerna в новом монорепо (deprecated, замена на Turborepo + Changesets)
- `yarn.lock` + `package-lock.json` в одном репо (один PM на репо)
- `.env` закоммичен (даже с fake values) — только `.env.example`
- Нет SBOM в release pipeline — регуляторы (EU CRA, NIST SSDF) требуют
- Copied-and-pasted ESLint/tsconfig в каждом пакете — drift-баги

## LFS-рекомендации

См. `ROADMAP.md` Фаза 0 (дни 1-7) — конкретные шаги init репо.

## Референсы

- Turborepo docs: https://turbo.build/docs
- t3-oss/create-t3-turbo: https://github.com/t3-oss/create-t3-turbo
- changesets/changesets: https://github.com/changesets/changesets
- Conventional Commits: https://www.conventionalcommits.org
- SLSA: https://slsa.dev
- ADR: https://adr.github.io
- Trunk-Based Development (DORA): https://dora.dev/capabilities/trunk-based-development
