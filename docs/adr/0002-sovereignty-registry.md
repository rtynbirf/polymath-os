# ADR-0002: Sovereignty Registry — двухъярусный реестр зависимостей

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A1 (LFS-этика против фактического стека)

## Context

Тезис 3 Polymath OS объявляет LFS как этическую позицию: «никаких предсобранных бинарников, никакой внешней зависимости от чужих корпоративных сборок». Однако фактический стек отчёта целиком состоит из арендованного или чужого: GitHub (CI, репо, Pages), Sentry, 1Password, OpenRouter, BetterStack, Hetzner/Cloudflare, публичная инфраструктура Sigstore, Obsidian (закрытый код).

Принцип невыполним буквально, поэтому перестаёт управлять решениями: любая новая зависимость может быть оправдана как «необходимая» без проверки, нарушает ли она суверенитет.

## Decision

Ввести **Sovereignty Registry** — двухъярусный реестр всех зависимостей системы:

### Tier 1: Суверенное ядро (sovereign core)

Зависимости, которые работают **без сети и без аккаунтов**, и данные в которых хранятся в открытом формате:

| Зависимость | Формат данных | Замена |
|---|---|---|
| Git | git objects | само ядро |
| Markdown | plaintext | — |
| SQLite | SQLite db (open) | libsql / DuckDB |
| age | X25519 + ChaCha20-Poly1305 | minisign / GPG (fallback) |
| Nix | nix expressions | Guix / devbox (fallback) |
| Conventional Commits | plaintext | — |
| cosign (keyless) | Sigstore bundle (open) | minisign (offline fallback) |
| CycloneDX SBOM | JSON | SPDX |
| Python (standard library only) | source code | — |

Суверенное ядро работает на чистой машине без аккаунта в GitHub/Sentry/Cloudflare.

#### Tier 1 — OSS dev tooling (npm-зависимости, declared in `package.json`)

Все devDependencies — OSS, без proprietary lock-in. Каждая перечислена здесь для coverage-чек:

| Пакет | Назначение | Замена (Tier 1 alt) |
|---|---|---|
| `@changesets/cli` | Управление версиями в монорепо | `release-please` / `semantic-release` |
| `turbo` | Build system монорепо (Vercel) | `nx` / `bazel` |
| `typescript` | Type checker (Microsoft, Apache-2.0) | — |
| `prettier` | Code formatter (MIT) | `biome` (drop-in) |
| `@biomejs/biome` | Linter + formatter (MIT) | `eslint` + `prettier` |

Все 5 пакетов — **OSS, MIT/Apache-2.0**, нет proprietary lock-in. Можно поставить через `npm` или `pnpm` без аккаунта, без регистрации. Кэш пакетов — в `~/.pnpm-store/`, работает offline после первичной установки.

### Tier 2: Арендуемые сервисы (rented services)

Зависимости, которые можно заменить по контракту. Для каждой фиксируется:

- что берём у сервиса (capability)
- формат данных на выходе (portable)
- стоимость выхода (effort + downtime)
- replacement (конкретный инструмент/сервис)
- offline fallback (что работает без сервиса)

| Сервис | Capability | Replacement | Offline fallback |
|---|---|---|---|
| GitHub Actions | CI | Woodpecker CI / Forgejo Actions + self-hosted runner | `act` локально |
| GitHub (repo) | git hosting | Gitea / Forgejo / Codeberg | локальный bare repo |
| GitHub Pages | static hosting | Cloudflare Pages / Netlify / self-host nginx | `python -m http.server` |
| Sentry | error tracking | Glitchtip (self-host) | structured logs in Loki |
| 1Password | secrets vault | Bitwarden (self-host Vaultwarden) | age-encrypted files in git |
| OpenRouter | LLM gateway | Ollama (local) / vLLM (self-host) | local model only |
| BetterStack | uptime | Uptime Kuma (self-host) | cron + curl + Telegram bot |
| Hetzner | VPS | OVH / Scaleway / self-host on mini-PC | local bare metal |
| Cloudflare | DNS / CDN | bind9 (self-host) / Bunny CDN | `/etc/hosts` |
| Obsidian | markdown editor | Foam (VSCode) / Logseq / `less` | `cat` / `less` |
| Quartz | static site gen | MkDocs Material / Astro Starlight | plain HTML |

### Tier 3: Закрытые форматы (lock-in, миграция обязательна)

| Зависимость | Проблема | Миграция |
|---|---|---|
| Obsidian `.canvas` files | не markdown | экспорт в `.md` + Mermaid |
| Notion | нет настоящего экспорта, связи теряются | migrate → Obsidian vault |
| `.obsidian/workspace.json` | mutable state, не экспортируется | `.gitignore` |
| GitHub-specific Actions | несовместимы с другими CI | reusable workflow + abstraction |

## Consequences

- **Positive:**
  - Принцип LFS становится выполнимым: ядро реально работает без сети
  - Каждая новая зависимость получает явный тир — решение обосновано
  - Учение выхода — quarterly drill: отключить один сервис, проверить что ядро и данные работают
  - Sovereignty метрика: % функций, работающих offline
- **Negative:**
  - Накладные расходы на документирование каждой зависимости
  - Tier 2 может соблазнить «всё арендовать, не утруждаясь ядром»
  - Некоторые сервисы (OpenRouter) не имеют полного offline-replacement для enterprise-grade моделей
- **Neutral:**
  - Реестр обновляется при каждом изменении стека (ADR + PR)

## Alternatives Considered

### LFS literally (no external dependencies)
Отвергнуто: невыполнимо для production-grade системы с monitoring/observability/LLM.

### No registry, just use what works
Отвергнуто: principle drift, любая зависимость оправдана, нет управления суверенитетом.

### Vendor-managed sovereignty (vendor tells you what's theirs)
Отвергнуто: противоречит самой идее суверенитета.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A1
- Implementation: `ARCHITECTURE.md` §8
- Drill procedure: `docs/runbook/RUNBOOK.md` §9
