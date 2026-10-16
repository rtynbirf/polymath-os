# ADR-0009: Default-deny публикация vault — из экспорта, не из самого репо

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A9 (Self-publish из одного репо с приватной базой знаний)

## Context

Polymath OS отчёт заявлял: «Vault коммитится каждые 10 минут в репозиторий, Quartz v4 публикует подмножество second brain как public digital garden». Но:

- **Механизм выбора подмножества не описан.**
- Ошибка в фильтре = публикация приватных заметок.
- Git-история сохраняет всё навсегда — даже после удаления из последнего коммита приватная заметка остаётся в истории.

Это **severe** risk: случайно опубликованная заметка с секретом/персональными данными — необратима.

## Decision

### 1. Default-deny: публикуется только явное `publish: true`

Quartz фильтрует заметки по YAML frontmatter:

```yaml
---
type: permanent
publish: true   # ЯВНО. Без этого — приватно.
---
# Atomic Notes Compound
...
```

Заметка без `publish: true` — **не попадает** в сборку сайта.

### 2. CI-проверка перед публикацией

В `.github/workflows/publish-garden.yml`:

1. **Секрет-сканер**: `gitleaks` / `trufflehog` над всеми заметками с `publish: true`. Если найден секрет — CI fail, публикация отменена.
2. **Персональные данные**: regex-чек на email, телефоны, адреса. Если найдено — warning + manual review (через PR).
3. **Внешние ссылки на приватное**: detect `[[note]]` ссылки на заметки без `publish: true` — strip или block.
4. **Отрицательный тест**: заметка без пометки с «ловушкой-строкой» (например `__CANARY__secret__`) **не должна** появиться в собранном сайте.

### 3. Публичный сайт — из **экспорта**, не из самого vault

Структура:

```
polymath-os/          # приватный репо, весь vault
└── apps/garden/      # Quartz v4 (исходники генератора)

polymath-os-garden/   # PUBLIC репо, только экспорт
├── content/          # только заметки с publish: true
└── quartz.config.ts
```

CI workflow:
1. Checkout `polymath-os` (private).
2. Filter `vault/60-permanent/` → оставить только `publish: true`.
3. Run security checks на отфильтрованном subset.
4. Copy filtered subset → `polymath-os-garden/content/`.
5. Build Quartz → deploy to GitHub Pages / Cloudflare Pages.

`polymath-os-garden` — public, но содержит **только фильтрованный экспорт**. Приватный репозиторий не пушится в public.

### 4. ⛔ Если приватная заметка всё же утекла

Считать публикацию **необратимой** (см. `docs/runbook/RUNBOOK.md` §5):
1. Убрать с сайта и из кэшей CDN.
2. Ротировать всё упомянутое в заметке (секреты, токены, имена, адреса).
3. Оценить обязанность уведомления (GDPR, regulation, contract).
4. Переписывать историю git **только как дополнение**, не замену ротации.

## Consequences

- **Positive:**
  - Default-deny: без явной пометки — приватно. Безопасно по умолчанию.
  - CI-gate: ошибка в фильтре ловится до публикации.
  - Отдельный public репо: даже если фильтр сломается, утечка ограничена заметками с `publish: true`.
  - Negative test: regression-защита.
- **Negative:**
  - overhead: каждый publish требует CI-прогон (минуты, не секунды).
  - Publishing friction: автор должен явно пометить `publish: true` + запушить через PR в garden.
  - Cache invalidation: после удаления `publish: true` заметка может остаться в CDN cache.
- **Neutral:**
  - `apps/garden/` в `polymath-os/` — Quartz v4 как **генератор**, не как контейнер контента.
  - `polymath-os-garden/` — отдельный public репо, deploy-target.

## Alternatives Considered

### Single repo, default-allow (publish everything unless `publish: false`)
Отвергнуто: анти-паттерн, default небезопасный.

### Single repo, default-deny (publish only `publish: true`)
Лучше чем default-allow, но отвергнуто: история приватного репо навсегда содержит утекшую заметку, даже после удаления из HEAD. Отдельный public репо изолирует.

### Manual review for each publish
Отвергнуто: не масштабируется. CI-gate + canary-test — автоматический эквивалент.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A9
- Quartz v4: https://github.com/jackyzha0/quartz
- gitleaks: https://github.com/gitleaks/gitleaks
- RUNBOOK §5: `docs/runbook/RUNBOOK.md`
