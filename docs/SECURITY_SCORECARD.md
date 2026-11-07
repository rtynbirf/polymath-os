# OpenSSF Scorecard — baseline и план

> Замер 1: 2026-11-07, коммит `2ba3257` — **5.7/10** (первый publish, SARIF в Code Scanning).
> Замер 2 (волна 7): 2026-11-07, коммит `5e368d2` — **6.3/10**: Pinned-Dependencies
> 0 → 10 (12 находок в shell-скриптах закрыты: без `curl | sh`, Docker — официальный
> apt-репозиторий, npm ci, Nix — предустановленный с sha256-пином, см. `docs/INSTALL_NIX.md`).
> Подпись коммитов включена (`docs/COMMIT_SIGNING.md`): два SSH Signing Key,
> пульсовые коммиты подписаны в CI, `required_signatures` = true.
> Воркфлоу: `.github/workflows/scorecard.yml` (action v2.5.0, пин по SHA, ритм вт 05:33 UTC).
> Публичный реестр: <https://scorecard.dev/viewer/?uri=github.com/rtynbirf/polymath-os>.
>
> Волна 7.2: CII-автоанкета `.bestpractices.json` (50 критериев: 44 Met / 2 Unmet /
> 4 N/A — Chief бейдж-приложения авто-заполнит), чистка плейсхолдеров (SECURITY.md:
> реальный URL advisories вместо USER; dependabot: USER → rtynbirf) и Branch-Protection
> Tier 2/3: required reviews (≥1 approval) + required status checks (CI), bypass
> allowance владельца — канон прямых волн сохранён.
>
> Замер 3: коммит `56a056a` — **6.5/10**: Token-Permissions / Dangerous-Workflow /
> Branch-Protection — N/A.
>
> Замер 4: коммит `985f6ee` — **7.0/10**. Корень N/A-троицы найден: `.github/
> export-ignore` в `.gitattributes` вырезал воркфлоу из source-тарбола, а
> Scorecard читает файлы именно из архива (`tarball.listFiles`) — «no workflows
> found». После снятия export-ignore: Token-Permissions N/A→10 (job-level
> нормализация волны 7.3), Dangerous-Workflow N/A→10. Обратная сторона прозрения:
> Pinned-Dependencies 10→8 (видны unpinned pip-команды) — закрыто hash-pinned
> requirements (`scripts/requirements/*.txt`, волна 7.5). `administration: read`
> в GITHUB_TOKEN невалиден (скоуп App/PAT) — чтение защиты ветки переведено на
> repository ruleset `main-scorecard-protection` (6 правил, bypass владельца,
> волна 7.5): rulesets читаются Scorecard'ом без админ-токена.

## На 10/10 уже сейчас

Binary-Artifacts, Security-Policy, License, Vulnerabilities, Dependency-Update-Tool,
CI-Tests, SAST, Dangerous-Workflow, Token-Permissions — плюс закрытые в волне 4:
Pinned-Dependencies (42 SHA-пина actions, 0 непинненных команд в shell-скриптах,
pip — hash-pinned requirements, волна 7.5),
Branch-Protection (linear history + conversation resolution + required_signatures
+ ruleset `main-scorecard-protection`).

## Чеки ниже максимума — разбор

| Чек | Очки (замер 4) | Природа | Что делать |
| --- | --- | --- | --- |
| Signed-Releases | 8/10 | 5/5 релизов подписаны cosign, счётчик не максимален | растёт автоматически с каждым подписанным релизом |
| Maintained | 0/10 | репо моложе 90 дней (создано 2026-10-16) | время; автоматически 10 после 2027-01-14 |
| Code-Review | 0/10 | 0/29 approved changesets — канон прямых коммитов владельца | решение зафиксировано (волна 7.2): PR-флоу обязателен для внешних контрибьюторов — branch protection требует ≥1 approval + CI-чеки; владелец — bypass allowance (прямые волны, ПУЛЬС PID1 не ломается). Соло-владелец сам себе approved не выдаёт — осознанный 0 до второго ревьюера; рост через комьюнити |
| CII-Best-Practices | 0/10 | нет регистрации на bestpractices.dev | подготовка закрыта (волна 7.2): автоанкета `.bestpractices.json` в корне — Chief бейдж-приложения предложит ответы при регистрации; остался единственный ручной шаг: OAuth-вход владельца на <https://www.bestpractices.dev> → New project → Save (in_progress = 2 балла сразу, passing = 5 после анкеты); после — badge в README |
| Fuzzing | 0/10 | чек закрывается только OSS-Fuzz-интеграцией | сделан внутренний mutation-fuzzing `runtime/tests/test_fuzz_parsers.py` (stdlib, детерминированный) — нашёл и закрыл дыру в `schema_validate`; OSS-Fuzz — отдельная заявка |
| Contributors | 0/10 | 0 компаний-контрибьюторов | комьюнити и время |
| Packaging | N/A | нет публикации в реестры пакетов | кандидат: npm-публикация пакетов из `packages/` при появлении NPM_TOKEN |

## Принцип

Оценка — инструмент, не самоцель: чеки, требующие ломки канона репо
(прямые коммиты ПУЛЬСа, журнал-из-фактов), не торгуются — см. `docs/COMMIT_SIGNING.md`
про `required_signatures`. Остальное — доводим.
