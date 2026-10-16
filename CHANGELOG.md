# CHANGELOG — Polymath OS

Все значимые изменения в этом проекте документируются в этом файле.

Формат основан на [Keep a Changelog v1.1.0](https://keepachangelog.com/ru/1.1.0/),
проект следует [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Каждый PR должен обновлять секцию `[Unreleased]`. При release — секция
переименовывается в `[X.Y.Z] — YYYY-MM-DD`, и `release.yml` извлекает её
тело в GitHub Release notes.

## [Unreleased]

### Added — GitHub meta-files (best practices 2024-2026)

- **`.github/CODEOWNERS`** — соло-владение `@USER` на весь репо, с
  закомментированными секциями для команды по 5 слоям + cross-cutting.
- **`.github/PULL_REQUEST_TEMPLATE.md`** — Summary / Type (feat/fix/docs/refactor/perf/test/chore/build/ci) /
  Breaking changes / Verification (`make verify`) / Checklist (Conventional Commits, DCO signed-off,
  ADR if arch change, gitleaks, CHANGELOG updated).
- **`.github/ISSUE_TEMPLATE/bug_report.yml`** — GitHub Issue Form (не .md):
  description, steps to reproduce, expected, actual, `make verify` output, env (OS/Python/Node/commit).
- **`.github/ISSUE_TEMPLATE/feature_request.yml`** — GitHub Issue Form:
  problem statement, proposed solution, alternatives, target layer, ADR-needed checkbox.
- **`.github/ISSUE_TEMPLATE/config.yml`** — `blank_issues_enabled: false` + 5 contact_links
  (PUSH.md, AUDIT_RESPONSE.md, RUNBOOK, Discussions, Security advisory).
- **`.github/dependabot.yml`** — npm (weekly Monday 06:00 UTC, grouped minor+patch) +
  GitHub Actions (weekly, grouped). gomod/docker/pip omitted — соответствующих файлов в репо нет.
- **`.github/FUNDING.yml`** — placeholder (нет настроенных платформ, закомментированы примеры).
- **`.github/renovate.json`** — alternative to dependabot: schedule weekly,
  auto-merge minor devDeps after CI green, group eslint + typescript + github-actions,
  pinned packages (pnpm, turbo, typescript, biome) excluded from major auto-bump.
- **`.github/labels.yml`** — triage catalog: `type/*` (9), `priority/*` (4),
  `status/*` (4), `layer/*` (6 — mirror ARCHITECTURE.md), `adr/*` (4), meta (5).
- **`.github/labeler.yml`** — path → label rules for `actions/labeler@v5` (path-based auto-labeling).
- **`.github/workflows/release.yml`** — on tag `v*.*.*`: `make verify` → build →
  CycloneDX SBOM → cosign keyless sign (Sigstore) → extract notes from CHANGELOG.md →
  GitHub Release with SBOM + signature artifacts.
- **`.github/workflows/codeql.yml`** — CodeQL SAST (бесплатно для OSS) на PR/push + еженедельно
  (Monday 06:00 UTC), languages: javascript-typescript + python.
- **`.github/workflows/labels.yml`** — auto-apply `layer/*` и `type/*` labels на PR
  по path-паттернам + sync `.github/labels.yml` catalog → GitHub на push.
- **`CODE_OF_CONDUCT.md`** — Contributor Covenant v2.1 (русский перевод, оригинал приоритет).
- **`.gitattributes`** — `* text=auto eol=lf`, binary markers, linguist overrides
  (runtime → Python, generated files excluded), `export-ignore` для `.github/` и editor configs.
- **`.pre-commit-config.yaml`** — gitleaks + standard hooks (trailing-whitespace,
  end-of-file-fixer, check-yaml/json/toml/merge-conflict, detect-private-key,
  check-added-large-files, mixed-line-ending) + commitizen (conventional commits) +
  markdownlint-cli2 + ruff + prettier (YAML only).
- **`.markdownlint.yaml`** — MD013 disabled (long lines), MD024 siblings-only,
  MD041 enforced (first-line top-level heading), MD040 enforced (code block lang).
- **`.all-contributorsrc`** — initialization spec for All Contributors bot (empty list).

### Changed

- _Nothing in this release._

### Deprecated

- _Nothing in this release._

### Removed

- _Nothing in this release._

### Fixed

- _Nothing in this release._

### Security

- CodeQL SAST теперь работает на каждом PR (раньше — только Semgrep + Trivy + gitleaks в CI).
- cosign keyless (OIDC) подпись SBOM на каждом release (раньше — только Makefile target `make sign`).

## [1.0.0] — 2025-10-16

Первый публичный выпуск. Репозиторий переведён из «отчёта» в `make verify`-контракт:
каждое утверждение в `README.md` воспроизводится одной командой.

### Added

- **Layer 5 — SINGULYAR EIR v0.3**: execution kernel, который сохраняет намерение
  человека при смене исполнителя и не объявляет успех без подтверждённого состояния.
  Лестница абляции B0→B3→EIR — каждое звено несущее (тест `test_each_ablation_link_is_load_bearing`).
- **12 ADRs (0001-0012)** — каждое архитектурное решение зафиксировано по шаблону
  Context / Decision / Consequences. Список и mapping в `docs/AUDIT_RESPONSE.md`.
- **Sovereignty Registry** (ADR-0002) — двухъярусный реестр зависимостей:
  суверенное ядро (git, markdown, SQLite, age, Nix) + арендуемые сервисы (заменяемы по контракту).
- **Hardened RUNBOOK** — шаблон процедуры
  `ПРЕДУСЛОВИЯ → ПРЕДПРОСМОТР → ДЕЙСТВИЕ ⛔ → ПРОВЕРКА → ЕСЛИ УПАЛО → СЛЕД`.
- **`make verify`** — open-source контракт: 12 проверок, exit 0 — все
  утверждения держатся на машине, где запущено.
- **CI** (`.github/workflows/ci.yml`) — pnpm + turborepo + gitleaks + Semgrep +
  Trivy (HIGH/CRITICAL) + CycloneDX SBOM.
- **MIT License** + `SECURITY.md` (private disclosure, ≤72 ч ack, ≤7 дней triage).

[Unreleased]: https://github.com/USER/polymath-os/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/USER/polymath-os/releases/tag/v1.0.0
