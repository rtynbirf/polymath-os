# ADR-0001: Записываем архитектурные решения

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER

## Context

Polymath OS — система из 4 слоёв (repo / AI / second-brain / devex) + cross-cutting (security / OTel / git). Каждое архитектурное решение в одном слое влияет на остальные. Без явной записи решений:

- Через 6 месяцев забывается, почему выбрали X вместо Y
- При onboarding нового участника (или самого себя через год) невозможно понять rationale
- Дискуссии «почему мы используем X?» повторяются
- Рефакторинги без контекста ломают то, что было сделано осознанно

## Decision

Принять ADR-паттерн (Architecture Decision Records, https://adr.github.io):
- Каждое значимое архитектурное решение → ADR в `docs/adr/`
- Имя файла: `NNNN-kebab-slug.md` (4-значный номер)
- Template — в `docs/adr/template.md`
- Status: Proposed → Accepted → (Deprecated | Superseded by)
- После Accepted ADR immutable; новые решения → superseding ADR со ссылкой
- Каждый ADR review'ится в PR как обычный код
- Минимум 7 initial ADRs (см. `docs/01-principles.md` §"Применение принципов")

## Consequences

- **Positive:**
  - История решений — в git, индексируется, ищется
  - Onboarding: новый участник читает ADR-папку → понимает почему всё так
  - Споры «почему X?» → ссылка на ADR
  - Рефакторинг с явным superseding ADR → видно эволюцию
- **Negative:**
  - Накладные расходы на написание ADR для каждого решения
  - Риск «ADR как документация ради документации»
  - Нужно поддерживать жизнеспособность (Superseded-ссылки)
- **Neutral:**
  - ADR — living document, но не wiki. После Accepted не правится.

## Alternatives Considered

### Architecture wiki в Notion/Confluence
Отвергнуто: документация вне репозитория умирает за 6 месяцев (см. `docs/02-repo-structure.md` anti-pattern).

### README-only (без отдельной ADR-папки)
Отвергнуто: README — landing page, не место для depth-decision-rationale.

### Архитектурные решения в commit messages
Отвергнуто: commit messages — atomic, не narrative. Контекст решений нужен отдельный.

## References

- https://adr.github.io
- https://github.com/architecture-decision-record/template
- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
