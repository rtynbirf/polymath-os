# ADR-0005: Раздельные цели отката — код / миграции / данные

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A4 (Self-rollback ≤60 сек)

## Context

Метрика «Self-rollback ≤60 сек» описывает только самый простой кусок: откат кода через `helm rollback` / `argocd app rollback`. Но:

- **Миграции схемы** не откатываются вместе с кодом. Если deploy включил migration `ALTER TABLE users DROP COLUMN email`, rollback кода не вернёт колонку.
- **Внешние побочные эффекты** (отправленные emails, processed payments, push notifications) — не откатываются.
- **Данные**, модифицированные между deploy и rollback — потеряны или в несогласованном состоянии.
- RUNBOOK при этом допускал 30 минут до решения об откате для P1 — противоречие с метрикой «60 сек».

## Decision

Заменить единую метрику «rollback ≤60 сек» на **три раздельные цели**:

### Цель 1: Откат кода — ≤60 сек

`helm rollback` / `argocd app rollback`. Это rollback deployment к предыдущей ревизии Helm chart.

- Метрика: время выполнения rollback-команды
- Предел: нельзя rollback миграций

### Цель 2: Безопасные миграции — expand/contract, без отката данных

Каждая миграция схемы БД — **расширяющая или сужающая**, но никогда не ломающая совместимость:

- **Expand:** добавить колонку (nullable, с default). Old code игнорирует. New code использует.
- **Migrate:** backfill данных для новых колонок (background job).
- **Contract:** убрать использование колонки из old code (после деплоя new code, который не использует).
- **Cleanup:** дроп колонку в следующей миграции (после подтверждения, что old code больше не живёт).

**Откат кода возможен** (new code → old code), потому что old code совместим с новой схемой.

Метрика: **CI тест** — old code должен читать/писать new schema без ошибок. Без этого теста миграция не смержится.

### Цель 3: Восстановление данных — RPO/RTO с измеренным учением

- **RPO (Recovery Point Objective):** окно потери данных (target: ≤5 min через WAL/PITR).
- **RTO (Recovery Time Objective):** время восстановления (target: ≤1 час для production).
- **Метрика:** quarterly учение «восстановить БД на чистую машину», запись времени и потерянного окна как артефакт.

## Consequences

- **Positive:**
  - Метрика честная: rollback ≠ «60 сек и всё хорошо». Разделяет ответственность.
  - Expand/contract миграции — стандарт с первого дня, не retrofit потом.
  - RPO/RTO — реальные числа, проверенные drill-ом, а не обещания.
- **Negative:**
  - Expand/contract требует discipline и времени — каждая миграция теперь несколько шагов, не один.
  - RPO/RTO ≤5 min / ≤1 час — реальная инфраструктурная стоимость (WAL streaming, PITR setup).
  - Учения занимают время (quarterly полдня).
- **Neutral:**
  - RUNBOOK переписан (см. `docs/runbook/RUNBOOK.md` §2) с тремя раздельными таблицами метрик.

## Alternatives Considered

### Single metric «60 sec»
Отвергнуто: вводит в заблуждение, игнорирует миграции/данные.

### Миграции всегда forward (no rollback ever)
Отвергнуто: в production всегда может возникнуть need-to-rollback. Expand/contract даёт эту возможность безопасно.

### Долгий down-time для миграций (maintenance windows)
Отвергнуто: противоречит continuous deployment философии.

## Verification

- CI: тест «old code + new schema» — blocking
- Quarterly: restore-test на чистой машине, запись RPO/RTO как issue-артефакт
- RUNBOOK §2 — три таблицы метрик

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A4
- Expand/Contract pattern: https://martinfowler.com/bliki/ParallelChange.html
- PITR (Point-in-Time Recovery): Postgres WAL / RDS PITR
