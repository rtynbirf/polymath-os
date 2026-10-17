# Second Brain / PKM — Layer 3

> Best-in-class практики для personal knowledge management (2024-2026).
> LFS-rebuild: markdown-first, git-sync, AI-augmented, no vendor lock-in.

---

## Принципы

1. **Markdown как source of truth.** Заметка читается `cat`-ом через 10 лет. HTML-вёрстка, проприетарные `.canvas`/`.notion` — долг.
2. **Local-first, cloud-optional.** Данные на диске, доступны офлайн. Облако — только sync.
3. **Atomic notes.** Одна идея на заметку (Luhmann, Matuschak). Атомарность = переиспользование.
4. **Bidirectional linking.** `[[note]]` — главное навигационное средство. Папки = type, теги = status, ссылки = смысл.
5. **Output > collection.** Ценность = написанный текст, не число клиппингов (collector's fallacy).
6. **Capture frictionless, processing deliberate.** <5 сек capture, осознанный processing.
7. **AI как retriever, не как author.** Локальные embeddings + локальный LLM. Ничего в облако.

## Стек (Polymath OS defaults)

| Компонент | Tool | Зачем |
|---|---|---|
| Editor | **Obsidian** | Local-first md, plugin ecosystem, primary GUI |
| Outliner alt | Logseq | Если любишь Roam-парадигму без облака |
| VSCode-native alt | Foam | Если редактор уже VSCode |
| Sync | **obsidian-git** plugin | Auto-backup 10 min, branch-на-эксперименты |
| Daily notes | Obsidian core + Templater | Journal + fleeting capture |
| Note management | **PARA** folders + **MOC** (Nick Milo) | Findability + navigation |
| Retrieval (SQL) | **Dataview** plugin | SQL-like queries по YAML frontmatter |
| Semantic search | **Smart Connections** + Ollama embeddings | Local, offline, ничего в облако |
| RAG chat | **Copilot for Obsidian** + Ollama VaultQA | Полностью офлайн RAG над vault |
| Capture (web) | **Glasp** + Obsidian Web Clipper | Highlight + AI summary → markdown |
| Capture (voice) | **AudioPen** | AI-polished transcript → inbox |
| Publish | **Quartz v4** | Static site gen для Obsidian vault → GitHub Pages |
| Backup | git (private repo on GitHub/Gitea/Forgejo) | History + multi-device |

## Структура vault

```
vault/
├── 00-daily/         # journal, fleeting capture
├── 10-projects/      # PARA: Projects (active, deadline)
├── 20-areas/         # PARA: Areas (responsibility, no end)
├── 30-resources/     # PARA: Resources (topics of interest, MOCs)
├── 40-archive/       # PARA: Archive (completed)
├── 50-literature/    # literature notes по источникам
├── 60-permanent/     # atomic permanent notes
└── 90-meta/          # templates, scripts, attachments
```

## Паттерны

### Трёхтипные заметки (Zettelkasten Luhmann)

- **Fleeting** — мгновенный захват (≤48 ч lifetime). Дальше — upgrade или delete.
- **Literature** — резюме источников: YAML meta + буллеты ключевых тезисов **своими словами** + ссылка.
- **Permanent** — атомарные, 1 идея, ≥2 линка на другие permanent, написаны своими словами.

### Daily note как inbox + журнал

```markdown
---
type: daily
---
# 2026-10-16

## Inbox (fleeting)
- [ ] Идея: ...
- [ ] Ссылка: https://...

## Today's work
- [[project-X]] — делал Y

## Permanent notes written today
- [[2026-10-16-atomic-notes-compound]]
```

### Tags vs folders vs links

- **Folders** = type of content (daily / literature / permanent / moc / archive)
- **Tags** = ad-hoc status (`#toread`, `#draft`, `#book`)
- **Links `[[...]]`** = основные смысловые связи

Правило (Eleanor Konik): «папки для type, теги для статуса, ссылки для смысла».

### RAG-чат над vault (полностью офлайн)

```bash
ollama serve
ollama pull nomic-embed-text     # for embeddings
ollama pull qwen2.5:32b          # for chat (или gpt-oss:120b)
```

В Copilot for Obsidian: provider = `Ollama (local)`, endpoint = `http://localhost:11434/v1`, mode = `VaultQA`. Copilot retrieves top-k чанков vault → LLM отвечает с цитатами `[[note]]`.

### Git-sync (backups + history + multi-device)

- Private GitHub/Gitea/Forgejo репо
- obsidian-git: auto-backup 10 min → commit + push
- Mobile: Working Copy (iOS) или Termux+git (Android)
- Branches — для экспериментальных reorg: `git checkout -b reorg-2026-q4`

### Публикация → digital garden

Quartz v4: статический генератор специально под Obsidian vault. Читает `[[wikilinks]]`, рендерит backlinks, graph view, search. Деплой на GitHub Pages — бесплатно.

```bash
npx quartz@4 create
# symlink content/ → vault/60-permanent/ (или копировать с фильтром)
# GitHub Action: build Quartz → deploy to Pages
```

Фильтр: заметки с `publish: true` в frontmatter идут в garden; остальные — приватные.

## Anti-patterns

1. **Collector's fallacy** — сохранять = знать. Симптом: 1000 unread lit-notes, 20 permanent. Лечение: «одна lit → одна permanent в течение 7 дней».
2. **Plugin sprawl** — 50 плагинов. Лечение: белый список 7 essential.
3. **Organization without output** — 50 MOC, 0 статей. Лечение: метрика «publish-output в месяц».
4. **No daily/weekly review** — inbox переполняется. Лечение: 10+10 min daily, 30 min weekly — неудаляемые слоты.
5. **Облако как primary storage** — Notion/Roam без локальной копии. Лечение: markdown-копия локально + git.
6. **Длинные «всё-в-одном» заметки** — не переиспользуются. Лечение: split на 20 atomic + 1 MOC.
7. **AI как замена мышления** — «AI написал MOC» → чужой MOC, ты его не понимаешь.
8. **Over-tagging** — тег на каждое слово. Лечение: ≤3 тегов на заметку, тег = статус/тип.
9. **MOC как оглавление** — если можно Dataview-generate, это не MOC, это ToC.
10. **Отсутствие «delete»** — vault пухнет. Лечение: `git` даёт историю, можно удалять смело.

## LFS-рекомендации

См. `ROADMAP.md` Фаза 2, дни 36-42. Резюме:

1. Repo skeleton: 8 папок PARA+ (00-daily, 10-projects, ..., 90-meta)
2. Templates: permanent.md, daily.md, literature.md
3. Obsidian как GUI + 7 essential plugins
4. Git-sync (private repo, auto-backup 10 min)
5. AI augmentation: Ollama + Smart Connections + Copilot for Obsidian (VaultQA)
6. Publish: Quartz v4 в `apps/garden` → GitHub Pages
7. Rituals: daily (10+10) + weekly (30) + monthly (2ч) + quarterly (полдня)
8. Anti-fragility: раз в полгода открыть vault без Obsidian

## Референсы

- Zettelkasten.de: https://zettelkasten.de/introduction/
- Collector's Fallacy: https://zettelkasten.de/posts/collectors-fallacy/
- Building a Second Brain (Tiago Forte): https://www.buildingasecondbrain.com/
- PARA Method: https://fortelabs.com/blog/the-para-method/
- Linking Your Thinking (Nick Milo): https://www.linkingyourthinking.com/
- Andy Matuschak — Evergreen notes: https://notes.andymatuschak.org/Evergreen_notes
- Obsidian: https://obsidian.md/
- Foam: https://github.com/foambubble/foam
- obsidian-git: https://github.com/Vinzent03/obsidian-git
- Smart Connections: https://github.com/brianpetro/obsidian-smart-connections
- Copilot for Obsidian: https://github.com/logancyang/obsidian-copilot
- Khoj: https://github.com/khoj-ai/khoj
- Quartz v4: https://github.com/jackyzha0/quartz
- Local-First Software (Kleppmann 2019): https://www.inkandswitch.com/local-first/
