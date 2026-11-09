# SUPPORT

Как получить поддержку по **polymath-os**.

## Баги и предложения

- **Баги:** [Issues → New issue → Bug report](https://github.com/rtynbirf/polymath-os/issues/new?template=bug_report.yml)
- **Предложения:** [Issues → New issue → Feature request](https://github.com/rtynbirf/polymath-os/issues/new?template=feature_request.yml)

GitHub Discussions отключён — issues служат единым каналом (закон роя: один
мастер-индекс, append-only отчёты волн).

## Безопасность

**Не открывайте security-проблему публичным issue.** Репозиторий включил
**Private Vulnerability Reporting** — сообщайте приватно:

> [Security → Report a vulnerability](https://github.com/rtynbirf/polymath-os/security/advisories/new)

Ответ циклится при каждой волне проекта (мультиагентный ритм, ежедневно).

## Самостоятельная диагностика

1. `make verify` — открытый контракт репо (33 клейма целостности).
2. `PULSE.md` — журнал-из-фактов самоаудита (ПУЛЬС-протокол v2, понедельник 04:17 UTC).
3. [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/rtynbirf/polymath-os) — независимая оценка цепочки поставок.
4. `security-insights.yml` — машиночитаемый отчёт о безопасности.
5. Релизы подписаны (cosign keyless) и **неизменяемы**: `gh attestation verify <файл> -R rtynbirf/polymath-os`.

## Ответственное лицо

`rtynbirf` — единственный владелец (см. [GOVERNANCE.md](./GOVERNANCE.md)).
