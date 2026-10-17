# ADR Template

```markdown
# ADR-NNNN: <краткое название решения>

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded by [ADR-XXXX](./XXXX-...)
**Deciders:** @users

## Context

<зачем нужно решение. что было раньше. какие альтернативы рассматривались.>

## Decision

<что решили.>

## Consequences

- **Positive:**
  - <плюс 1>
  - <плюс 2>
- **Negative:**
  - <минус 1>
  - <минус 2>
- **Neutral:**
  - <нейтральное следствие>

## Alternatives Considered

### <Альтернатива A>
<почему не подошла>

### <Альтернатива B>
<почему не подошла>

## References

- <link 1>
- <link 2>
```

## Numbering

- Формат: `NNNN-slug.md` (4-значный номер, kebab-case slug).
- Номера — последовательные (0001, 0002, 0003...).
- После Accepted — immutable. Изменения → новый ADR с `Superseded by`.

## Status transitions

```
Proposed → Accepted → (Deprecated | Superseded by ...)
```

`Proposed` → `Accepted` происходит при merge PR'а с ADR в `main`.
`Accepted` → `Deprecated` или `Superseded` — через новый ADR с явной ссылкой.
