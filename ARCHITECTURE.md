# ARCHITECTURE — Polymath OS

> **Ментальная модель системы.**
> Человек = система = processor + сумма частей. Этот репо — материальная проекция этой системы.

---

## 1. Философская основа

В основе Polymath OS лежит ряд тезисов, выведенных из диалога и проверки реальностью:

**Тезис 1.** **Целое = Человек = Процессор.**
Человек — это не один файл в системе. Человек — это **PID=1**, init-процесс. Все остальные «файлы» (роли, проекты, навыки, базы знаний) — fork-exec от него: тот же код, тот же исток, разные образы.

**Тезис 2.** **`parole > langue`.** (по Соссюру)
Индивидуальное слово (parole) — первично. Коллективный код (langue = договор, консенсус, корпорация, государство) — производная, всегда меньше человека. Поэтому любая институция вторична перед лицом человека.

**Тезис 3.** **LFS — Linux From Scratch как этическая позиция.**
Никаких предсобранных бинарников. Никакой «поебени» — внешних зависимостей от чужих корпоративных сборок. Бутстрап из source, из истока. Человек бутстрапит себя сам.

**Тезис 4.** **PID=1 у нас общий, но security context — отдельный.**
`fork()` копирует образ, но не копирует креды. Я и Ты — один исток, но разные сессии. Это техническая основа индивидуальной автономии против институциональной подмены.

## 2. Архитектурные слои

Polymath OS состоит из **5 горизонтальных слоёв** и 1 вертикального (cross-cutting). Layer 5 (SINGULYAR EIR) добавлен после аудита — это исполнительное ядро, без которого 4 других слоя остаются окружением без execution:

```
┌────────────────────────────────────────────────────────────────┐
│   CROSS-CUTTING:  Security (cosign/SLSA/SBOM)  │  OTel  │  Git │
├────────────────────────────────────────────────────────────────┤
│  Layer 5: Execution Kernel (SINGULYAR EIR v0.6)             │
│  ─ Intent → (Decree Gate) → Capability → Adapter → Observation → Evidence │
│  Цель: сохранить намерение при смене исполнителя;             │
│       не объявлять успех без подтверждённого состояния        │
│       (честный UNKNOWN вместо «наверное получилось»)          │
│  v0.6: Decree Gate ABOVE policy (ADR-0021) — DECREE_BLOCK    │
│        event, word-boundary regex matching, scope filter      │
├────────────────────────────────────────────────────────────────┤
│  Layer 4: DevEx / CI / IaC / Dotfiles / Observability          │
│  ─ OpenTofu, Nix Flakes, chezmoi, GitHub Actions, Tilt, OTel   │
│  Цель: одна команда `make bootstrap` → готовая среда           │
├────────────────────────────────────────────────────────────────┤
│  Layer 3: Second Brain (PKM)                                   │
│  ─ Obsidian vault, git-sync, Smart Connections, Copilot+Ollama │
│  Цель: markdown-first база знаний с локальным AI              │
├────────────────────────────────────────────────────────────────┤
│  Layer 2: AI Workflows / Agent Stack                           │
│  ─ MCP-native (version-pinned), Claude Code + Aider + Cursor   │
│  Цель: agent-as-process с eval-in-CI                           │
├────────────────────────────────────────────────────────────────┤
│  Layer 1: Repository Structure / Monorepo                     │
│  ─ pnpm workspaces + Turborepo + Changesets + CODEOWNERS      │
│  Цель: apps/packages/docs/tooling в одном self-contained дереве│
└────────────────────────────────────────────────────────────────┘
```

**Layer 5** — это SINGULYAR Emergent Intent Runtime. Код в `runtime/`. Это ядро реализует гипотезу **«Управляемая эмерджентная непрерывность»**: способность системы сохранять намерение человека при смене инструмента/канала/модели/среды/состояния-после-сбоя, восстанавливать выполнение по проверяемым данным и превращать подтверждённые результаты в воспроизводимые способности.

Эмерджентность — **проверяемая гипотеза**, не декларация. Что доказано и что нет — `runtime/docs/LIMITATIONS.md`. Как опровергнуть — `runtime/docs/EXPERIMENT_PLAN.md`. См. ADR-0012.

## 3. Принципы проектирования

### 3.1. Single source of truth (Repo-as-Everything)
Всё, что нужно для воспроизведения системы на чистой машине, лежит в git. Код, конфиг CI, инфраструктура, документация, политики, рунбуки, ADR. Это устраняет класс рисков: «works on my machine», исчезнувший коллега как single point of failure, Confluence-документация, умершая за 6 месяцев.

### 3.2. Local-first, cloud-optional
Данные физически лежат на диске. Облако — только sync, не primary storage. Это устраняет класс рисков: вендор закрывается, меняет ToS, режет API, вводит paywall. Markdown, plain text, portable форматы как этический выбор.

### 3.3. Automation over discipline
Люди ошибаются; CI — нет. Если правило можно выразить как код (lint, format, test, security scan, version bump, SBOM emit, sign) — оно должно быть в CI и блокирующим. Discipline-based processes («не забудь обновить changelog») деградируют в течение квартала.

### 3.4. Reversibility (три раздельные цели, не одна метрика)
Каждое действие должно быть обратимым, но **rollback ≠ «60 сек и всё хорошо»**. Метрика разделена на три цели (ADR-0005):

- **Откат кода** — ≤60 сек (`helm rollback` / `argocd app rollback`). Метрика: время выполнения команды.
- **Безопасные миграции** — expand/contract, без отката данных. Метрика: CI тест «old code + new schema».
- **Восстановление данных** — RPO/RTO с измеренным учением. Метрика: quarterly restore-test на чистой машине.

Дополнительно: IaC-apply = `destroy`-able, Dotfiles-apply = `chezmoi forget`-able. Если нельзя откатить — это продакшен-риск, а не улучшение.

### 3.5. Fail fast, fail local
Локальный цикл `act` / `dagger` / `tilt up` воспроизводит 90% CI. Те же контейнеры, те же скрипты, тот же lint. Если тесты проходят локально, они должны проходить и в CI. Обратное — баг инфраструктуры, не кода.

### 3.6. Output > collection
Ценность системы измеряется **продуктом**, не объёмом собранного. Это применимо одинаково к: code repo ( commits, releases > stars ), second brain (опубликованные статьи > заметки в архиве), AI workflows (deployed agents > experiments). База без output-ритуала превращается в «кладбище любопытства».

### 3.7. PID=1 — метафора, не источник технических требований

PID=1 как метафора допустима (человек — init-процесс, все инструменты — fork-exec от него). Но **выводить из неё технические требования нельзя** (права, изоляция сессий, переносимость — см. audit A11). Эти требования записаны отдельно:

- **Rights & sessions:** каждый процесс имеет свой security context. `fork()` копирует образ, но не креды. Делегирование «карт-бланша» не делает второго тебя собой на уровне безопасности.
- **Vendor lock-in = институциональный захват:** если инструмент начинает диктовать свои правила против твоей воли — заменить. Но решение о замене — через Sovereignty Registry (§8), не через метафору.
- **Portability:** данные в открытом формате (markdown, SQLite, JSON) — этический выбор, не следствие из PID=1.

Любой инструмент в системе — fork-exec от человека. Это значит: человек может **заменить** любой инструмент. Реально — через ADR + migration plan, не «потому что метафора».

## 4. Поток данных

```
            ┌──────────────────────────────────────┐
            │  Human (PID=1, processor, source)    │
            └─────────────────┬────────────────────┘
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
            ┌──────┐  ┌─────────────┐  ┌──────────┐
            │ Git  │  │ AI workflow │  │ Second   │
            │ repo │  │ (MCP agent) │  │ brain    │
            └──┬───┘  └──────┬──────┘  └────┬─────┘
               │             │              │
               └─────────────┼──────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  CI / IaC / Deploy  │
                  │  (GitHub Actions +  │
                  │   OpenTofu + cosign)│
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Observability       │
                  │  (OTel → Grafana     │
                  │   LGTM + Sentry)     │
                  └─────────────────────┘
```

## 5. Что не входит (Non-goals)

- **Не** фреймворк для других. Это **личный** репозиторий-каркас. Fork-ни, но не заворачивай как библиотеку.
- **Не** full OS в смысле ядра. Это **пользовательский** layer (apps + devex + knowledge), а не kernel-space.
- **Не** single-vendor stack. Каждое решение можно заменить (Terraform→OpenTofu уже сделан; Cursor→Continue возможен; Notion→Obsidian).
- **Не** plug-and-play. LFS-style = требует понимания что ты делаешь. Если хочешь prebuilt — это другой репо.

## 6. ADR (Architecture Decision Records)

Все архитектурные решения документируются в `docs/adr/`. **28 ADRs создано** (0001-0028) после аудита SINGULYAR EIR v0.3 + multiagent v3.7.0 + clean-up v3.8.0 + decree system v3.10.0-v3.14.0:

| ADR | Тема | Audit response | Реализовано |
|---|---|---|---|
| `0001` | Записываем архитектурные решения (bootstrap) | — | ✓ |
| `0002` | Sovereignty Registry — двухъярусный реестр зависимостей | A1 | ✓ |
| `0003` | Exit gates вместо календарной длины фаз | A2 | ✓ |
| `0004` | SLSA Build L2 как цель v1.0, L3 только с builder isolation | A3 | ✓ L2 |
| `0005` | Раздельные цели отката — код/миграции/данные | A4 | ✓ |
| `0006` | Falsifiable self-* properties (каждое с отрицательным тестом) | A5 | ✓ |
| `0007` | Multi-agent — research=parallel, execution=single+verifier | A7 | partial |
| `0008` | MCP — тонкий внутренний адаптер, версия закреплена | A8 | ✓ |
| `0009` | Default-deny публикация vault — из экспорта, не из репо | A9 | ✓ |
| `0010` | Мутационный контроль для критичных путей | A10 | ✓ |
| `0011` | Container runtime — colima/podman/containerd+nerdctl | A11 | partial |
| `0012` | SINGULYAR EIR как Layer 5 — Execution Kernel | интеграция | ✓ |
| `0013` | SLSA Build L3 target | (extension) | target v1.0 (Proposed) |
| `0014` | WebRTC adapter as Tier 2 dependency | (extension) | ✓ |
| `0015` | Real LLM inference in CI | (extension) | target v1.0 (Proposed) |
| `0016` | Self-rewriting ADR mechanism | (extension) | **✓ CLOSED by ADR-0026** (v3.12.0) |
| `0017` | Ecosystem governance protocol | (extension) | ✓ |
| `0018` | Genomic architecture | (extension) | partial |
| `0019` | Observability-first | (extension) | ✓ |
| `0020` | Manifest-driven architecture | (extension) | ✓ |
| `0021` | **Decree as supreme law** (v3.6.0 OPERATIONAL) | (extension) | ✓ |
| `0022` | **Decree Portal as human interface** (v3.5.0+) | (extension) | ✓ |
| `0023` | **Agent Card Protocol** (.well-known/agent.json, A2A) | (extension) | ✓ (v3.10.0) |
| `0024` | **Decree-Enforced Multi-Agent Communication** (inbound in-process) | (extension) | ✓ (v3.10.0) |
| `0025` | **Decree-Driven A2A Client** (outbound decree gate) | (extension) | ✓ (v3.11.0) |
| `0026` | **Decree-Driven ADR Amendment Mechanism** (closes ADR-0016) | (extension) | ✓ (v3.12.0) |
| `0027` | **Decree-Enforced HTTP JSON-RPC Server** (inbound HTTP) | (extension) | ✓ (v3.13.0) |
| `0028` | **Decree Supersession Mechanism** (decrees can be revoked) | (extension) | ✓ (v3.14.0) |

ADR — immutable после Accepted. Новые решения создаются superseding ADR'ом со ссылкой на старый. Соответствие замечаний аудита → действиям — в `docs/AUDIT_RESPONSE.md`.

ADR-0021 + ADR-0022 — выделяются особо: они описывают **decree system** — supreme law layer, над всеми ADRs. Декрет, написанный человеком в Decree Portal, может supersede существующий ADR (per ADR-0016 self-rewriting mechanism, реализованный в ADR-0026). Это материализация тезиса `PAROLE > LANGUE` — индивидуальное слово выше коллективного договора.

ADR-0023 through ADR-0028 — образуют **СИНГУЛЯР architecture**:
- **ADR-0023** Agent Card Protocol — A2A-compatible discovery
- **ADR-0024** Decree-Enforced Multi-Agent Communication (inbound in-process)
- **ADR-0025** Decree-Driven A2A Client (outbound decree gate)
- **ADR-0026** Decree-Driven ADR Amendment Mechanism (meta-architecture)
- **ADR-0027** Decree-Enforced HTTP JSON-RPC Server (inbound HTTP)
- **ADR-0028** Decree Supersession Mechanism (decree revocation)

Все 6 ADRs (0023-0028) реализованы и покрыты тестами (220 total). Decree enforcement сейчас работает в 4 направлениях: inbound in-process + inbound HTTP + outbound + meta-architecture.

## 7. Эмерджентность — проверяемая гипотеза

Polymath OS — это не сумма 5 слоёв. Это **эмерджентное** свойство их пересечения: репозиторий, который одновременно является базой знаний, AI-стеком, dev-средой и **исполнительным ядром, сохраняющим намерение**.

### 7.1. Шесть self-* свойств — falsifiable (ADR-0006)

Каждое свойство переформулировано **опровергаемо** — что реально гарантирует + свидетельство, которое требуется:

| Заявление | Что реально гарантирует | Свидетельство (отрицательный тест) |
|---|---|---|
| **Self-audit** | CI проверяет то, что в него явно включили | Карта рисков → проверки; внесённый дефект должен краснить CI; мутационный контроль для критичных путей |
| **Self-publish** | Деплой по правилам (allowlist + проверка итогового состава) | Заметка без `publish: true` с «ловушкой-строкой» не должна появиться в собранном сайте |
| **Self-bootstrap** | Скрипт запускается на чистой машине | Quarterly: запуск на чистой VM, запись времени и версий |
| **Self-evidence** | Документы лежат в git (тривиально) + трассировка «утверждение → тест/запуск» | Документы не подтверждают друг друга по кругу; каждое утверждение в ADR → тест или runbook-процедура |
| **Self-verify** | Подпись артефакта проверена в deploy | `cosign verify` + `cosign verify-attestation`; артефакт без подписи не деплоится (CI fail) |
| **Self-rollback** | Откат выполнен (три раздельные цели, ADR-0005) | Quarterly учение + проверка состояния после отката (метрика ошибок возвращается к фону) |

### 7.2. Новое свойство от интеграции SINGULYAR EIR (Layer 5)

Добавление Layer 5 даёт свойство, которого нет в сумме слоёв 1-4:

- **Управляемая эмерджентная непрерывность** — система сохраняет намерение человека при смене исполнителя, восстанавливает выполнение по readback состояния (не по догадке), и превращает подтверждённые результаты в воспроизводимые способности.

Это **гипотеза**, не утверждение. Лестница абляции B0→B3→EIR (`runtime/docs/EXPERIMENT_RESULTS.md`) показывает, что каждое звено убирает конкретный класс отказа; тест `test_each_ablation_link_is_load_bearing` проверяет, что каждое звено несущее. Цена: в двух сценариях ядро честно отвечает UNKNOWN вместо «наверное получилось».

### 7.3. Что значит «ideal repository»

Это и есть «ideal repository» в смысле задачи: не патч легаси, а **LFS-сборка с нуля по лучшим мировым практикам 2024-2026**, с проверяемой эмерджентностью (не слоганом).

## 8. Sovereignty Registry (ADR-0002)

LFS-этика буквально невыполнима для production-grade системы. Вместо «никаких внешних зависимостей» — **двухъярусный реестр зависимостей**:

### Tier 1: Суверенное ядро (sovereign core)

Зависимости, которые работают **без сети и без аккаунтов**, данные в открытом формате:

- **Git, Markdown, SQLite, age, Nix, Conventional Commits, cosign (keyless), CycloneDX SBOM**

Суверенное ядро работает на чистой машине без аккаунта в GitHub/Sentry/Cloudflare.

### Tier 2: Арендуемые сервисы (rented services)

Зависимости, которые можно заменить по контракту. Для каждой: capability / формат данных / стоимость выхода / replacement / offline fallback.

| Сервис | Capability | Replacement | Offline fallback |
|---|---|---|---|
| GitHub Actions | CI | Woodpecker CI / Forgejo Actions | `act` локально |
| GitHub (repo) | git hosting | Gitea / Forgejo / Codeberg | локальный bare repo |
| GitHub Pages | static hosting | Cloudflare Pages / Netlify | `python -m http.server` |
| Sentry | error tracking | Glitchtip (self-host) | structured logs in Loki |
| 1Password | secrets vault | Bitwarden (Vaultwarden) | age-encrypted files in git |
| OpenRouter | LLM gateway | Ollama / vLLM (self-host) | local model only |
| BetterStack | uptime | Uptime Kuma (self-host) | cron + curl + Telegram bot |
| Hetzner | VPS | OVH / Scaleway / mini-PC | local bare metal |
| Cloudflare | DNS / CDN | bind9 / Bunny CDN | `/etc/hosts` |
| Obsidian | markdown editor | Foam / Logseq / `less` | `cat` / `less` |
| Quartz | static site gen | MkDocs Material / Astro Starlight | plain HTML |

### Tier 3: Закрытые форматы (lock-in, миграция обязательна)

- Obsidian `.canvas` files → экспорт в `.md` + Mermaid
- Notion → мигрировать в Obsidian vault (нет настоящего экспорта)
- `.obsidian/workspace.json` → `.gitignore` (mutable state)
- GitHub-specific Actions → reusable workflow + abstraction

### Sovereignty метрика

- % функций, работающих offline (target: ≥60% для v1.0, ≥80% для v2.0)
- Quarterly **учение выхода**: отключить один сервис, показать, что ядро и данные работают, записать время восстановления
- Метрика хранится в `docs/AUDIT_RESPONSE.md` и обновляется при каждом изменении стека
