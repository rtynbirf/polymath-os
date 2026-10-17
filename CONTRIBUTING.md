# CONTRIBUTING — Polymath OS

Спасибо за интерес! Trunk-based, conventional commits, ADR-driven.

## Перед PR

1. **Обсуждение:** для не-trivial изменений — открой issue или Discussion с предложением.
2. **ADR:** если изменяется архитектура — создай/обнови ADR в `docs/adr/`.
3. **Локальная проверка:**
   ```bash
   make bootstrap && make lint && make typecheck && make test && make ci-local
   ```

## Branch & Commit

- **Ветка:** `feat/<short-scope>-<kebab-topic>` (например, `feat/web-add-auth`)
- **Время жизни:** ≤24 ч; если дольше — разбей на stacked PRs (Graphite)
- **Commit message:** [Conventional Commits](https://www.conventionalcommits.org):
  ```
  feat(web): add OAuth login with Google
  fix(api): handle 404 on user-not-found
  docs(adr): add ADR-0009 on local-first second brain
  chore(deps): bump turbo to 2.1.0
  ```
- **PR title:** такой же формат, как commit message (verified by `action-semantic-pull-request`)

## PR

- Таргет: `main`
- Затронутые пути в `CODEOWNERS` → requisite approval
- Status checks: lint, typecheck, test, build, security — все зелёные
- Squash-merge → один атомарный коммит в `main`
- Linear history preserved (force-rebase включён)

## Release

- `pnpm changeset` в PR рядом с кодом → `changesets/action` создаёт Version PR
- Merge Version PR → триггерит `pnpm publish -r` с SLSA provenance
- Для контейнеров: `cosign sign` (keyless OIDC) + `cosign attest` SBOM

## Architecture changes

Если PR меняет архитектуру:
1. Создай ADR `docs/adr/NNNN-<slug>.md` (используй `docs/adr/template.md`)
2. ADR должен быть Approved до merge
3. После merge — обнови `ARCHITECTURE.md` если нужно

## Security

- **Секреты в коде = блок.** Pre-commit hook на `gitleaks`.
- Если нашёл vulnerability — см. `SECURITY.md` (private disclosure).
- SBOM (CycloneDX) генерируется в каждом release.

## Code style

- TS/JS: Biome (drop-in для ESLint+Prettier)
- Python: Ruff
- Go: golangci-lint с default config
- Markdown: Prettier с `proseWrap: preserve`

## Tests

- Unit: обязательны для `packages/*`
- Integration: Testcontainers для `apps/*` (Postgres/Redis в CI)
- Eval: promptfoo golden datasets для AI-агентов
