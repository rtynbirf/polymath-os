# Принципы — Polymath OS

> Сводный список принципов из всех 4 исследовательских доменов.
> Это — конституция системы. Нарушение любого = tech debt.

---

## Принципы LFS-style rebuild

### 1. Repo-as-Everything
Репозиторий = single source of truth для кода, конфига, инфраструктуры, документации, политик, рунбуков, ADR. Всё, что нужно для воспроизведения системы на чистой машине, лежит в git. Это устраняет класс рисков: «works on my machine», исчезнувший коллега как SPOF, Confluence-документация, умершая за 6 месяцев.

### 2. Trunk-based + linear history
`main` — единственная долгоживущая ветка, всегда зелёная. Feature branch живёт ≤24 ч; если дольше — разбивается на stacked PR. Squash-merge + Conventional Commits → атомарный коммит на единицу работы. Merge Queue для сохранения green-build. GitFlow оставлен для boxed-release on-prem продуктов.

### 3. Code ownership
Каждый path в репозитории имеет explicit owner в `.github/CODEOWNERS`. PR не смержится, пока владельцы затронутых файлов не одобрят. Это устраняет «review-у-случайных-людей» и «ответственность-размывается».

### 4. Documentation-driven design
README-first (Preston-Werner pattern), `ARCHITECTURE.md` (ментальная модель), ADR (архитектурные решения с контекстом и последствиями), `RUNBOOK.md` (incident response) — четыре слоя документации, живущих в репо рядом с кодом. Документация в Confluence/Notion умирает за 6 месяцев; в репозитории — нет.

### 5. Local-first, cloud-optional
Данные физически лежат на диске, доступны офлайн. Облако — только sync, не primary storage. Markdown, plain text, portable форматы как этический выбор. Устраняет класс рисков: вендор закрывается, режет API, вводит paywall.

### 6. Automation over discipline
Если правило можно выразить как код (lint, format, test, security scan, version bump, SBOM emit, sign) — оно должно быть в CI и блокирующим. Discipline-based processes деградируют в течение квартала; CI — нет.

### 7. Single-agent baseline + MCP-native
Сначала один агент + инструменты, потом — несколько. Multi-agent — только при обоснованной необходимости (Cognition, Jun 2025: dispersed decision-making = хрупкость). Все инструменты — MCP-серверы. Vendor-neutral, discoverable, переиспользуемые между Cursor/Claude Code/own agents.

### 8. Context engineering (по Anthropic, Sep 2025)
Контекст — не «промпт», а система. Четыре подсистемы, проектируемые явно: working context (текущая задача), reference context (RAG over MCP), episodic memory (traces + summary-store), compression (summarize + eviction). Без eviction — context rot (-24.2% accuracy).

### 9. Eval — это CI/CD для агентов
Без Langfuse/LangSmith/promptfoo в пайплайне агент — это прототип. Golden dataset + LLM-as-judge + simulation-based testing. Каждое изменение промпта/модели — gating по метрикам.

### 10. Cache aggressively, compute lazily
Prompt caching (Anthropic explicit `cache_control`, OpenAI automatic) даёт 90% cost reduction + 85% latency reduction. KV cache + semantic caching — второй слой. Некэшируемый агент в 2026 = tech debt. Но: следи за cache-hit-ratio — miss на коротких промптах может увеличить bill на 25%.

### 11. Atomic notes (one concept per note)
Каждая постоянная заметка описывает одну атомарную идею (Zettelkasten Luhmann, evergreen notes Matuschak). Атомарность даёт переиспользование: одна заметка входит в 5 разных MOC. Длинная заметка входит только в свой изначальный контекст.

### 12. Output > collection
Ценность базы знаний = написанный текст, не число клиппингов. Без publish-ритуала (статья, пост, MOC, digital garden) база = «кладбище любопытства» (collector's fallacy). Метрика: ≥1 publish-output в месяц.

### 13. Fail fast, fail local
Локальный цикл `act` / `dagger` / `tilt up` воспроизводит 90% CI. Те же контейнеры, те же скрипты, тот же lint. Если тесты проходят локально — должны проходить и в CI. Push-and-pray = анти-паттерн.

### 14. Immutable artifacts + cryptographic provenance
Каждый build = контейнер с digest, подписанный cosign, со SBOM и SLSA-provenance аттестацией, в OCI registry. Артефакт, который нельзя верифицировать, нельзя деплоить.

### 15. Trunk-based + feature flags (decouple deploy from release)
`main` всегда зелёный и деплоится. Незавершённый код прячется за feature flag, а не за long-lived branch. Release = активация флага для когорты, а не отдельный pipeline.

### 16. Observability-first
Любой сервис содержит OTel SDK до того, как написан бизнес-код. Метрики + traces + structured logs идут в одну точку (Grafana LGTM / Axiom / Honeycomb). Утилизация контейнеров без трассировок = debugging в темноте.

### 17. Reversibility
IaC-apply = `destroy`-able. Deploy = `rollback`-able в ≤60 сек. Dotfiles-apply = `chezmoi forget`-able. Если нельзя откатить — это prod-risk, а не improvement.

### 18. PID=1 — человек, не инструмент
Любой инструмент в системе — fork-exec от человека (PID=1). Если инструмент начинает диктовать свои правила (vendor lock-in, opinionated framework против твоей воли) — это институциональный захват. Заменить. Человек всегда больше любого договора и любой тайны государства.

---

## Применение принципов

Каждый принцип имеет explicit owner в ADR:
- `docs/adr/0002-monorepo-turborepo.md` — Принципы 1, 2, 3
- `docs/adr/0003-pkm-obsidian-not-notion.md` — Принципы 5, 11, 12
- `docs/adr/0004-mcp-native-tool-layer.md` — Принципы 7, 8, 9, 10
- `docs/adr/0005-opentofu-over-terraform.md` — Принцип 17
- `docs/adr/0006-sops-age-over-vault.md` — Принцип 6
- `docs/adr/0007-cosign-keyless-over-gpg.md` — Принципы 14, 16
- `docs/adr/0008-trunk-based-feature-flags.md` — Принципы 2, 15
- `docs/adr/0009-local-first-second-brain.md` — Принципы 5, 11, 12

Принципы 4, 13, 18 — общие, без отдельного ADR (отражены в `ARCHITECTURE.md` и `CONTRIBUTING.md`).

## Audit-чек-лист (раз в квартал)

- [ ] Каждый path в `CODEOWNERS` имеет активного owner
- [ ] Документация (`ARCHITECTURE.md`, ADRs, RUNBOOK) синхронна с кодом
- [ ] Доля локально воспроизводимых CI шагов ≥ 90% (через `act`)
- [ ] Все production-артефакты имеют SBOM + cosign signature
- [ ] Все агенты имеют golden dataset в `promptfoo` CI
- [ ] Cache-hit-ratio по каждому production-агенту ≥ 50%
- [ ] Vault открывается без Obsidian (Foam/VSCode/`less`)
- [ ] IaC-destroy проходит на тестовом окружении за ≤5 мин
- [ ] Rollback проходит на production за ≤60 сек
- [ ] OTel SDK в каждом сервисе
