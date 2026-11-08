---
type: permanent
created: 2026-10-16
tags: [meta, vault, second-brain]
aliases: [welcome, intro-to-garden]
source: docs/04-second-brain.md
publish: true  # ADR-0009 — this one IS public. Example of an opted-in note.
---

# Welcome to Polymath OS Vault

> Первая permanent note в garden'е. Документирует, что это за место и как в нём
> ориентироваться.

## Claim

Polymath OS Vault — это second brain в формате markdown-first: приватный
по умолчанию, git-synced, AI-augmented, с public-export'ом atomic permanent
notes через Quartz v4 под явным флагом `publish: true`.

## Context

Полная мотивация и стек расписаны в [`docs/04-second-brain.md`](https://github.com/USER/polymath-os/blob/main/docs/04-second-brain.md) — Layer 3 всего репо.
Решение **default-deny publish** зафиксировано в
[`ADR-0009`](https://github.com/USER/polymath-os/blob/main/docs/adr/0009-default-deny-vault-publish.md).

Этот garden — public-export ветка: здесь видны только заметки с `publish: true`.
Daily, literature, project/area/resource notes — приватные, их здесь нет.

## How to navigate

- **Backlinks** в конце каждой заметки — bidirectional graph, основа навигации.
- **Graph view** вверху справа — визуальная карта заметок и их связей.
- **Search** (`Ctrl+K` / `Cmd+K`) — full-text + indexed content.
- **Tags** — не иерархия, а ad-hoc status/тип: `#meta`, `#second-brain`, `#adr`.

## Principles (TL;DR)

1. **Markdown как source of truth.** Читается `cat`-ом через 10 лет.
2. **Atomic notes.** Одна идея на заметку → переиспользование.
3. **Bidirectional linking.** `[[note]]` — главное навигационное средство.
4. **Output > collection.** Ценность = написанный текст, не число клиппингов
   (anti-pattern: collector's fallacy).
5. **Default-deny publish.** Без явного `publish: true` — приватно. Безопасно
   по умолчанию.

## Connections

- [[0002-default-deny-publish]] — почему default-deny, а не default-allow.

## References

- Layer 3 doc: `docs/04-second-brain.md`
- ADR-0009: `docs/adr/0009-default-deny-vault-publish.md`
- Quartz v4: https://quartz.jzhao.xyz/
- Obsidian: https://obsidian.md/
