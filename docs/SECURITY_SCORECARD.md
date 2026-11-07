# OpenSSF Scorecard — baseline и план

> Замер: 2026-11-07, коммит `2ba3257` (первый publish, SARIF в Code Scanning).
> Воркфлоу: `.github/workflows/scorecard.yml` (action v2.5.0, пин по SHA, ритм вт 05:33 UTC).
> Публичный реестр: <https://scorecard.dev/viewer/?uri=github.com/rtynbirf/polymath-os> (агрегатор догоняет с задержкой — источник истины: SARIF в Code Scanning).

## На 10/10 уже сейчас

Binary-Artifacts, Security-Policy, License, Vulnerabilities, Dependency-Update-Tool, CI-Tests — плюс закрытые в волне 4: Pinned-Dependencies (42 SHA-пина, 0 тег-пинов), Token-Permissions, Branch-Protection (linear history + conversation resolution).

## Чеки ниже максимума — разбор

| Чек | Очки | Природа | Что делать |
| --- | --- | --- | --- |
| Signed-Releases | 8/10 | 5/5 релизов подписаны cosign, счётчик не максимален | растёт автоматически с каждым подписанным релизом |
| SAST | 9/10 | CodeQL не на всех типах событий | расширить триггеры, если появятся новые |
| Maintained | 0/10 | репо моложе 90 дней (создано 2026-10-16) | время; автоматически 10 после 2027-01-14 |
| Code-Review | 0/10 | 0/30 approved changesets — канон прямых коммитов владельца | стратегический выбор: переход content-волн на PR с ревью (ПУЛЬС PID1 остаётся прямым); иначе осознанный 0 |
| CII-Best-Practices | 0/10 | нет регистрации на bestpractices.dev | анкета (~10 мин) на <https://www.bestpractices.dev> — нужен аккаунт владельца; после прохождения добавить badge в README |
| Fuzzing | 0/10 | нет fuzz-инфраструктуры | кандидат волны 7: atheris для `runtime/` (pure Python 3.10+) или OSS-Fuzz |
| Contributors | 0/10 | 0 компаний-контрибьюторов | комьюнити и время |
| Packaging | N/A | нет публикации в реестры пакетов | кандидат: npm-публикация пакетов из `packages/` при появлении NPM_TOKEN |

## Принцип

Оценка — инструмент, не самоцель: чеки, требующие ломки канона репо
(прямые коммиты ПУЛЬСа, журнал-из-фактов), не торгуются — см. `docs/COMMIT_SIGNING.md`
про `required_signatures`. Остальное — доводим.
