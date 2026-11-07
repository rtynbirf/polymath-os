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
>
> Замер 5 (`e1b9a2e`) — Pinned-Dependencies 10 (hash-pinned requirements);
> Branch-Protection стал читаемым через ruleset — 4/10. Волны 7.6–7.7:
> CODEOWNERS `@rtynbirf` вместо плейсхолдера `@USER`, 2 approvals + code-owner
> review + last-push approval + up-to-date (ruleset + branch protection) →
> Branch-Protection **9/10**: единственный Warn — «apply to administrators»:
> сознательный bypass владельца (канон прямых волн), 10/10 потребовал бы его ломки.
>
> Замер 8 (`6cd4688`, финал волны 7) — **7.3/10**. Branch-Protection 9/10
> подтверждён публичным реестром scorecard.dev. PR-флоу отработал end-to-end:
> #28 (svet) + #30-32 (hash-pinned pip, dependabot обновляет хеши сам) + #29
> (biome 2.6.5: dependabot → формат-фикс 16 файлов → @dependabot rebase →
> CI green → rebase-merge). Траектория волны 7: 6.5 → 7.0 → 7.3.
> Остаток: CII (OAuth-вход владельца), Maintained (время), Code-Review
> (второй ревьюер), Fuzzing (OSS-Fuzz заявка), Contributors (комьюнити).
>
> Волна 8 (2026-11-08): Signed-Releases — точная формула чека снята из
> исходников scorecard v5.6.0 (probes/releasesHaveProvenance: только
> `*.intoto.jsonl`, releaseLookBack = 5; evaluation: provenance = 10 очков,
> подпись = 8, итог = floor(сумма/5)). У всех релизов уже лежал готовый
> in-toto Statement как `sbom.slsa-provenance.json` — 36 релизам тот же файл
> байт-в-байт добавлен ассетом `sbom.slsa-provenance.intoto.jsonl` (канон
> SLSA, видимость, не фабрикация: 10 релизам без provenance пост-хоц файл
> НЕ создавался — принцип «журнал-из-фактов»); release.yml с волны 8 пишет
> сразу канон. CII-разведка фактами (agent-browser): аккаунт создан
> (rtynbirf@users.noreply.github.com), но активация требует письмо —
> noreply-адрес не принимает почту; GitHub OAuth требует сессию github.com
> (пароль). Единственный оставшийся шаг — человеческий (активация/вход,
> ≤10 мин, анкета готова в `.bestpractices.json`); in_progress = 2,
> passing = 5 очков сразу после него. Code-Review: по формуле v5.6 бот-PR
> (dependabot) — inconclusive, self-approval невозможен — соло-потолок 0
> подтверждён исходником, не догадкой; решение волны 7.2 (PR-флоу + 2
> approvals для контрибьюторов) — верное.

## На 10/10 уже сейчас

Binary-Artifacts, Security-Policy, License, Vulnerabilities, Dependency-Update-Tool,
CI-Tests, SAST, Dangerous-Workflow, Token-Permissions — плюс закрытые в волне 4:
Pinned-Dependencies (42 SHA-пина actions, 0 непинненных команд в shell-скриптах,
pip — hash-pinned requirements, волна 7.5),
Branch-Protection (linear history + conversation resolution + required_signatures
+ ruleset `main-scorecard-protection`).

## Чеки ниже максимума — разбор

| Чек | Очки (замер 8) | Природа | Что делать |
| --- | --- | --- | --- |
| Signed-Releases | 8/10 → 10 | 5/5 последних релизов получили канон `*.intoto.jsonl` (волна 8, тот же provenance байт-в-байт); release.yml пишет канон сразу | фиксируется после ближайшего замера Scorecard |
| Branch-Protection | 9/10 | «apply to administrators» = false — bypass владельца (канон прямых волн) | осознанный потолок 9/10; 10/10 = ломка канона, не торгуем |
| Maintained | 0/10 | репо моложе 90 дней (создано 2026-10-16) | время; автоматически 10 после 2027-01-14 |
| Code-Review | 0/10 | 0/29 approved changesets; по исходнику v5.6: бот-PR (dependabot) — inconclusive, self-approval невозможен | соло-потолок подтверждён исходником; решение волны 7.2 неизменно: PR-флоу обязателен для внешних контрибьюторов (branch protection + ruleset: 2 approvals + code-owner, волны 7.6–7.7); владелец — bypass (прямые волны, ПУЛЬС PID1 не ломается); рост через комьюнити |
| CII-Best-Practices | 0/10 | активация аккаунта требует письмо (noreply-адрес не принимает) / OAuth требует пароль-сессию github.com | разведка волны 8 закрыла всё автоматизируемое: аккаунт создан, анкета готова (`.bestpractices.json`); человеческий шаг ≤10 мин: активировать по ссылке из письма ИЛИ войти GitHub OAuth → New project → заполнить по `.bestpractices.json` → бейдж в README; in_progress = 2, passing = 5 сразу |
| Fuzzing | 0/10 | чек закрывается только OSS-Fuzz-интеграцией | сделан внутренний mutation-fuzzing `runtime/tests/test_fuzz_parsers.py` (stdlib, детерминированный) — нашёл и закрыл дыру в `schema_validate`; OSS-Fuzz — отдельная заявка |
| Contributors | 0/10 | 0 компаний-контрибьюторов | комьюнити и время |
| Packaging | N/A | нет публикации в реестры пакетов | кандидат: npm-публикация пакетов из `packages/` при появлении NPM_TOKEN |

## Принцип

Оценка — инструмент, не самоцель: чеки, требующие ломки канона репо
(прямые коммиты ПУЛЬСа, журнал-из-фактов), не торгуются — см. `docs/COMMIT_SIGNING.md`
про `required_signatures`. Остальное — доводим.
