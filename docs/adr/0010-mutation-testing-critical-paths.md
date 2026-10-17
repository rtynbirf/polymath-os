# ADR-0010: Мутационный контроль для критичных путей

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A10 (Метрики приёмки как суррогаты)

## Context

Отчёт Polymath OS использовал метрики приёмки как суррогаты качества:
- «Coverage ≥80%» — не говорит, проверены ли **критические** ветки.
- «100% сервисов с OTel» — не говорит, что трассы **полезны**.
- «make destroy ≤5 мин» — не определяет окружение.

Реальный пример из SINGULYAR v0.2 → v0.3: после **35 зелёных тестов** подмена `INCONCLUSIVE → CONFIRMED` (т.е. подмена «не могу проверить» на «всё ок») **не провалила ни один тест**. Тест добавили только после мутационной проверки (`runtime/docs/AUDIT_POLYMATH.md` §A10, V11). Это значит: coverage 100% не гарантирует, что тесты реально проверяют инварианты.

## Decision

### 1. Метрики привязаны к риску и способу измерения

| Метрика | Что реально проверяет | Способ измерения |
|---|---|---|
| Coverage 80% | что 80% строк выполнены во время тестов | `c8` / `coverage.py` |
| Mutation score ≥80% на критичных путях | что 80% мутаций убиваются тестами | `mutmut` (Python), `stryker` (JS/TS) |
| Critical path coverage 100% | все ветки в auth/secrets/recovery покрыты | `c8 --branches` + manual review |
| Deploy rollback ≤60 сек | время rollback-команды | quarterly drill, запись времени |
| OTel traces useful | trace содержит span с intent_id, capability_id, evidence_verdict | schema-assertion в CI |

### 2. Мутационный контроль на критичных путях

Mutation testing — **только** для критичных модулей, не для всего кода:

- `runtime/src/singulyar_runtime.py` — ядро EIR (state transitions, failover, recovery)
- `runtime/src/sqlite_ledger.py` — hash-linked journal (integrity)
- `packages/db/` — schema migrations
- `apps/api/` — auth, secrets handling
- `tooling/agents/` — production agent prompts (через promptfoo mutation)

Не мутационно:
- UI components (тестируются visual regression)
- Documentation
- Config files

### 3. Mutation CI-gate

В CI:
```yaml
- name: Mutation testing (critical paths)
  run: |
    mutmut run --paths-to-mutate=runtime/src/singulyar_runtime.py
    mutmut results --qualitative  # должен быть ≥80% killed
    if [ $? -ne 0 ]; then exit 1; fi
```

Mutation **не на каждый PR** (медленно). На nightly schedule + на PR, затрагивающий критичные файлы.

### 4. Что делать, если мутация выжила

«Выжившая мутация» = тест, который **не ловит** изменение поведения. Это:
1. Добавить regression-тест, который ловит эту мутацию.
2. Если мутация семантически нейтральна (например, изменение `+0` на `+1` в комментарии) — пометить как `# pragma: no mutate` с обоснованием.

## Consequences

- **Positive:**
  - Coverage перестаёт быть surrogate. Mutation score — более сильная метрика.
  - Реальные пробелы в тестах ловятся **до production**.
  - Критичные модули — наиболее защищённые.
- **Negative:**
  - Mutation testing медленный (10-100× unit tests). Nightly, не per-PR.
  - False positives: некоторые мутации семантически нейтральны, требуют `# pragma: no mutate`.
  - Engineering cost: каждый surviving mutation → новый тест.
- **Neutral:**
  - Coverage остаётся как quick metric, но не как acceptance gate.

## Alternatives Considered

### Coverage 80% as acceptance (как в оригинальном TZ)
Отвергнуто: A10 прямо показал — coverage не ловит пробелы.

### Mutation testing на каждый PR
Отвергнуто: слишком дорого. Nightly + critical-paths только.

### Property-based testing (Hypothesis, fast-check)
Дополнительно, но не замена mutation. Property-based — для инвариантов, mutation — для проверки, что тесты их реально проверяют.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A10, V11
- SINGULYAR self-audit V11: `runtime/docs/AUDIT_POLYMATH.md` §C
- mutmut: https://github.com/boxed/mutmut
- Stryker: https://stryker-mutator.io/
- promptfoo: https://www.promptfoo.dev (mutation for prompts)
