<!--
PR template — Polymath OS.
Заполни все секции. PR без Summary / Type / Checklist не проходит triage.
Trunk-based: таргет = `main`, squash-merge, lifetime ≤24 ч.
См. CONTRIBUTING.md.
-->

## Summary

<!-- 1–3 предложения: что делает PR и зачем. Если закрывает issue — `Closes #N`. -->

Closes #

## Type

<!-- Отметь один. Соответствует Conventional Commit scope. -->

- [ ] `feat` — новая возможность (minor bump по semver)
- [ ] `fix` — исправление бага (patch bump)
- [ ] `docs` — только документация
- [ ] `refactor` — без изменения поведения
- [ ] `perf` — улучшение производительности
- [ ] `test` — добавление/правка тестов
- [ ] `chore` — deps, ci, meta-files (не влияет на runtime)
- [ ] `build` — сборка, зависимости
- [ ] `ci` — только CI-конфигурация

## Breaking changes

<!-- Если breaking — опиши что ломается, что мигрировать, и поставь `!` в commit (feat!: ...). -->
<!-- Если нет — оставь "None". -->

None

## Verification

<!-- Запусти локально и приложи вывод. PR без зелёного `make verify` не мёрджится. -->

```bash
make verify
```

- [ ] `make verify` exit 0 (12/12 checks pass)
- [ ] Если PR добавляет новый claim в `README.md` — добавлен соответствующий check в `scripts/check.py`
- [ ] Если PR меняет архитектуру — создан/обновлён ADR в `docs/adr/` (см. `docs/adr/template.md`)

## Checklist

- [ ] Commit message следует [Conventional Commits](https://www.conventionalcommits.org) (`feat(web): ...`)
- [ ] PR title = commit message (verified by `amannn/action-semantic-pull-request`)
- [ ] `Signed-off-by` в коммите (DCO, `git commit -s`) — подтверждение авторства под MIT
- [ ] Нет секретов в diff (pre-commit hook `gitleaks` включён; если случайно закоммитил секрет — отозвать и открыть private advisory по `SECURITY.md`)
- [ ] `CHANGELOG.md` обновлён в секции `[Unreleased]` (Keep a Changelog)
- [ ] Если добавлен новый workflow / action — добавлен в `CODEOWNERS` и Dependabot grouping
- [ ] Self-review пройден; комментарии в коде на русском/английском как в окружающем файле
