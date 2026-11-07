# OpenSSF Scorecard — baseline и план

> Замер 1: 2026-11-07, коммит `2ba3257` — **5.7/10** (первый publish, SARIF в Code Scanning).
> Замер 2 (волна 7): 2026-11-07, коммит `5e368d2` — **6.3/10**: Pinned-Dependencies
> 0 → 10 (12 находок в shell-скриптах закрыты: без `curl | sh`, Docker — официальный
> apt-репозиторий, npm ci, Nix — предустановленный с sha256-пином, см. `docs/INSTALL_NIX.md`).
> Подпись коммитов включена (`docs/COMMIT_SIGNING.md`): два SSH Signing Key,
> пульсовые коммиты подписаны в CI, `required_signatures` = true.
> Воркфлоу: `.github/workflows/scorecard.yml` (action v2.5.0, пин по SHA, ритм вт 05:33 UTC).
> Публичный реестр: <https://scorecard.dev/viewer/?uri=github.com/rtynbirf/polymath-os>.

## На 10/10 уже сейчас

Binary-Artifacts, Security-Policy, License, Vulnerabilities, Dependency-Update-Tool,
CI-Tests — плюс закрытые в волне 4: Pinned-Dependencies (42 SHA-пина actions,
волна 7: 0 непинненных команд в shell-скриптах), Token-Permissions,
Branch-Protection (linear history + conversation resolution + required_signatures).

## Чеки ниже максимума — разбор

| Чек | Очки (замер 2) | Природа | Что делать |
| --- | --- | --- | --- |
| Signed-Releases | 8/10 | 5/5 релизов подписаны cosign, счётчик не максимален | растёт автоматически с каждым подписанным релизом |
| SAST | 8/10 | CodeQL не на всех исторических коммитах | самозатягивается с новыми коммитами; PR-триггер — при переходе на PR |
| Maintained | 0/10 | репо моложе 90 дней (создано 2026-10-16) | время; автоматически 10 после 2027-01-14 |
| Code-Review | 0/10 | 0/29 approved changesets — канон прямых коммитов владельца | стратегический выбор: переход content-волн на PR с ревью (ПУЛЬС PID1 остаётся прямым); иначе осознанный 0 |
| CII-Best-Practices | 0/10 | нет регистрации на bestpractices.dev | анкета (~10 мин) на <https://www.bestpractices.dev> — нужен аккаунт владельца; после прохождения добавить badge в README |
| Fuzzing | 0/10 | чек закрывается только OSS-Fuzz-интеграцией | сделан внутренний mutation-fuzzing `runtime/tests/test_fuzz_parsers.py` (stdlib, детерминированный) — нашёл и закрыл дыру в `schema_validate`; OSS-Fuzz — отдельная заявка |
| Contributors | 0/10 | 0 компаний-контрибьюторов | комьюнити и время |
| Packaging | N/A | нет публикации в реестры пакетов | кандидат: npm-публикация пакетов из `packages/` при появлении NPM_TOKEN |

## Принцип

Оценка — инструмент, не самоцель: чеки, требующие ломки канона репо
(прямые коммиты ПУЛЬСа, журнал-из-фактов), не торгуются — см. `docs/COMMIT_SIGNING.md`
про `required_signatures`. Остальное — доводим.
