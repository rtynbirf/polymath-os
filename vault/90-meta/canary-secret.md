---
type: canary
created: 2026-10-16
tags: [meta, test, canary]
description: "Negative-test canary. Must NEVER appear in apps/garden/content/. Used by publish-garden.yml."
---

# Canary — do not publish

> ⛠ **Test fixture**, не настоящая заметка. Используется CI workflow'ом
> `publish-garden.yml` как отрицательный тест default-deny (ADR-0009).
>
> У этой заметки **нет** поля `publish:` в frontmatter. Это значит — приватная.
> Она никогда не должна появиться в `apps/garden/content/` и никогда не
> должна быть видна на сайте garden.

## Negative test

CI-фильтр (`apps/garden/scripts/filter_vault.py`) перед deploy проверяет,
что маркер `__CANARY_p1m0s_8f3a2e91_dnp_v1__` отсутствует в собранном контенте:

```bash
grep -r "__CANARY_p1m0s_8f3a2e91_dnp_v1__" apps/garden/content/ \
  && echo "CANARY LEAKED — default-deny broken" && exit 1 \
  || echo "canary absent — default-deny holds"
```

Если ты видишь на готовом сайте строку `__CANARY_p1m0s_8f3a2e91_dnp_v1__` —
default-deny сломан. Открой issue: github.com/USER/polymath-os/issues.

__CANARY_p1m0s_8f3a2e91_dnp_v1__
