---
type: permanent
created: 2026-10-16
tags: [meta, adr, security, publish-policy]
aliases: [adr-0009, default-deny]
source: docs/adr/0009-default-deny-vault-publish.md
publish: true  # ADR-0009 — public explanation of the policy itself.
---

# Default-deny publish (ADR-0009)

> Заметка, объясняющая почему публикация из second brain идёт через явный opt-in,
> а не opt-out. Соответствует ADR-0009.

## Claim

В Polymath OS заметка публикуется в digital garden **только** если в её YAML
frontmatter стоит `publish: true`. Без этого флага — приватно. Это structural,
не configurable: фильтр стоит upstream от Quartz, сам Quartz видит только
opted-in subset.

## Context

Альтернативы (рассмотрены в ADR-0009 и отвергнуты):

- **Default-allow** (`publish: false` чтобы скрыть): небезопасно по умолчанию.
  Один забытый флаг = утечка приватной заметки навсегда (git-история хранит).
- **Single repo, default-deny**: лучше, но история приватного репо навсегда
  сохраняет утёкшую заметку, даже после удаления из HEAD.
- **Manual review per note**: не масштабируется. CI-gate + canary —
  автоматический эквивалент.

Решение: **отдельный public-репо изолирован от приватного**, наполнение
идёт через CI-фильтр на `publish: true`, перед сборкой Quartz.

## Evidence

Pipeline в [`publish-garden.yml`](https://github.com/USER/polymath-os/blob/main/.github/workflows/publish-garden.yml):

1. CI фильтрует `vault/60-permanent/` → оставляет только `publish: true`.
2. **gitleaks** + regex на emails/phones на filtered subset.
3. **Negative test**: canary-marker (см. `vault/90-meta/canary-secret.md`)
   должен отсутствовать в `apps/garden/content/`. Если есть — deploy блокируется.
4. Quartz собирается. Видит только opted-in subset.
5. Deploy в GitHub Pages.

Canary-note живёт в `vault/90-meta/canary-secret.md` без `publish: true` flag.
Если когда-нибудь filter сломается и canary попадёт в garden — CI падает до
deploy. Сам маркер в документации не приводится, чтобы не получить
ложное срабатывание negative test'а — см. исходник canary-note.

## Consequences

- **Positive**: default безопасный. Ошибка в фильтре ловится до публикации.
  Отдельный public-репо: даже при сломанном фильтре утечка ограничена
  заметками с `publish: true`.
- **Negative**: publishing friction. Автор должен явно пометить `publish: true`
  + запушить через PR в garden. Cache invalidation: после удаления
  `publish: true` заметка может остаться в CDN cache.
- **Neutral**: `apps/garden/` в `polymath-os/` — Quartz v4 как **генератор**,
  не контейнер контента. Контент приезжает из vault'а через CI.

## Connections

- [[0001-welcome]] — entry point в garden.

## References

- ADR-0009: `docs/adr/0009-default-deny-vault-publish.md`
- Workflow: `.github/workflows/publish-garden.yml`
- Filter script: `apps/garden/scripts/filter_vault.py`
- RUNBOOK §5 (если утекло): `docs/runbook/RUNBOOK.md`
- Quartz v4: https://quartz.jzhao.xyz/
- gitleaks: https://github.com/gitleaks/gitleaks
