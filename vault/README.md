# Vault — Layer 3 (Second Brain)

> Markdown-first, git-synced, AI-augmented personal knowledge base.
> Приватный по умолчанию. Публикуется только явное `publish: true` — см. [ADR-0009](../docs/adr/0009-default-deny-vault-publish.md).

## Структура (PARA + Zettelkasten + MOC)

```
vault/
├── 00-daily/         # journal + fleeting capture (приватно)
├── 10-projects/      # PARA: Projects (active, deadline)
├── 20-areas/         # PARA: Areas (responsibility, no end)
├── 30-resources/     # PARA: Resources (topics of interest, MOCs)
├── 40-archive/       # PARA: Archive (completed)
├── 50-literature/    # literature notes по источникам (приватно)
├── 60-permanent/     # atomic permanent notes — единственный кандидат на публикацию
├── 90-meta/
│   ├── templates/    # permanent / daily / literature / moc
│   ├── attachments/  # images, pdf (gitignored если тяжёлые)
│   └── canary-secret.md  # отрицательный тест CI
└── .obsidian/        # safe-to-commit config (workspace* gitignored)
```

## Открыть в Obsidian

1. File → Open vault → выбрать `vault/` директорию.
2. Settings → Community plugins → отключить "Restricted mode" (только если хочешь obsidian-git, smart-connections, copilot).
3. Settings → Templates → template folder location = `90-meta/templates`.

## Sync (obsidian-git)

- Поставь плагин **obsidian-git** (Vinzent03/obsidian-git).
- Settings → auto-backup every 10 min → commit + push в `polymath-os` (private repo).
- Mobile: Working Copy (iOS) или Termux+git (Android).

## Publish — digital garden (Quartz v4)

**Важно: публикация идёт через CI, не через push в public-репо.**

1. Напиши permanent note в `60-permanent/`.
2. Поставь в YAML frontmatter `publish: true` — это **явное** разрешение.
3. Push в `main`.
4. CI workflow [`../.github/workflows/publish-garden.yml`](../.github/workflows/publish-garden.yml):
   - фильтрует `vault/60-permanent/` → оставляет только `publish: true`;
   - gitleaks + regex-чек на emails/phones;
   - копирует filtered subset → `apps/garden/content/`;
   - собирает Quartz v4;
   - деплоит в GitHub Pages.
5. Canary-тест: заметка `90-meta/canary-secret.md` без `publish: true` **не должна**
   появиться в собранном сайте. CI падает, если она там оказалась.

## Default-deny (ADR-0009)

- Каждый шаблон заметки имеет `publish: false` по умолчанию.
- Заметка без явного `publish: true` — приватная.
- Даже если фильтр сломается — отдельный public-репо изолирует утечку до
  notes с `publish: true` (но git-история private-репо всё равно навсегда
  сохранит утекшую заметку — см. RUNBOOK §5 для ротации).

## Что не коммитим

`.gitignore` в репо-рут исключает:
- `vault/.obsidian/workspace*` — mutable per-session state.
- `vault/.obsidian/cache` — плагин-кэш.
- `vault/.trash/` — Obsidian recycle bin.
- `vault/.smart-env/` — Smart Connections embeddings cache.

`community-plugins.json` пустой — плагины ставятся через Obsidian UI, не коммитятся.
`hotkeys.json` пустой — дефолтные горячие клавиши.

## Ссылки

- ADR-0009: `../docs/adr/0009-default-deny-vault-publish.md`
- Layer 3 doc: `../docs/04-second-brain.md`
- RUNBOOK §5 (если утекло): `../docs/runbook/RUNBOOK.md`
