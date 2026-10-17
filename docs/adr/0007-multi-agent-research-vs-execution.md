# ADR-0007: Multi-agent — research=parallel, execution=single+verifier

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A7 (Multi-agent: проектирование против исполнения)

## Context

Отчёт Polymath OS цитировал Cognition (Jun 2025) «Don't Build Multi-Agents» и рекомендовал «сначала один агент, потом — несколько». Методология же этого же отчёта использовала **четырёх параллельных агентов** для исследования. Это противоречие, даже если формально это разные контексты.

Без явного разделения контекстов принцип теряет управляемость: любой multi-agent сценарий может быть оправдан «это исследование» или «это исполнение».

## Decision

Явное разделение двух режимов:

### Режим 1: Исследование (research) — параллельные агенты OK

- Цель: сбор данных, обзор практик, генерация опций.
- Побочные эффекты: **только чтение** (web search, file read, DB read).
- Multi-agent — нормально: 4 параллельных исследователя собирают данные по 4 доменам.
- Сходимость: человек сводит результаты, конфликты решаются человеком.
- Пример из этого проекта: 4 research-агента (repo / AI / second-brain / devex) вернули структурированные отчёты, человек синтезировал их в Polymath OS.

### Режим 2: Исполнение (execution) с побочными эффектами — single executor + детерминированный независимый проверяющий

- Цель: выполнить задачу, изменяющую состояние мира (deploy, write, send, mutate).
- Побочные эффекты: запись (file write, DB write, network POST, deploy).
- **Single executor**: один агент выполняет действие.
- **Независимый проверяющий — НЕ второй LLM**, а:
  - формальный верификатор (JSON Schema для Intent/Capability/Evidence)
  - тест состояния (assertion в CI)
  - readback состояния (определяется через adapter.read_state, не через agent claim)
- Это паттерн SINGULYAR EIR (`runtime/docs/TECHNICAL_SPEC.md` §2-5): EXECUTING → VERIFYING с PASS/FAIL/INCONCLUSIVE.

## Почему не второй LLM как verifier

- Тот же LLM-класс → те же слепые пятна.
- Разный LLM-класс → сложно сравнивать вердикты.
- LLM-вердикт не детерминированный — нельзя regression-test.
- Формальный верификатор (schema, test, readback) — детерминированный и тестируемый.

## Consequences

- **Positive:**
  - Принцип «сначала single-agent» выполним буквально для исполнения.
  - Multi-agent в исследовании — явно разрешён, не противоречие.
  - Проверка результата — deterministic, regression-testable.
- **Negative:**
  - Single executor — bottleneck для throughput.
  - Формальный verifier — overhead (каждое действие требует schema + test).
  - Не все действия можно верифицировать readback (например, fire-and-forget emails).
- **Neutral:**
  - SINGULYAR EIR — реальная реализация этого принципа (Layer 5).

## Alternatives Considered

### Multi-agent execution с LLM-verifier
Отвергнуто: недетерминированный, не regression-testable.

### Single-agent всегда (even research)
Отвергнуто: research параллелизм реально ускоряет работу в 4× (как в этом проекте).

### Multi-agent execution с разделением ролей (planner/executor/critic)
Отвергнуто: «Don't Build Multi-Agents» (Cognition) — dispersed decision-making + context propagation = хрупкость.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A7
- Cognition: https://cognition.com/blog/dont-build-multi-agents
- SINGULYAR EIR: `runtime/docs/TECHNICAL_SPEC.md` §2-5
