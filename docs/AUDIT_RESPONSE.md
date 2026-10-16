# AUDIT_RESPONSE — Polymath OS

> Ответ на аудит SINGULYAR EIR v0.3 (`runtime/docs/AUDIT_POLYMATH.md`).
> 11 замечаний к Polymath OS (A1-A11) + 11 к RUNBOOK (R1-R11) + интеграция SINGULYAR EIR как Layer 5.

---

## Соответствие замечание → действие

| # | Замечание (audit) | Действие | Где зафиксировано |
|---|---|---|---|
| **0001** | — (bootstrap ADR, не audit-fix) | Записываем архитектурные решения вообще | `docs/adr/0001-record-architecture-decisions.md` |
| **A1** | LFS-этика против фактического стека (GitHub/Sentry/1Password/OpenRouter/etc.) | Введён **Sovereignty Registry** — двухъярусный реестр зависимостей: *суверенное ядро* (git, markdown, SQLite, age, Nix — работает без сети и аккаунтов) и *арендуемые сервисы* (заменяемы по контракту). | `docs/adr/0002-sovereignty-registry.md`, `ARCHITECTURE.md` §8 |
| **A2** | Арифметика roadmap: «4 фазы × ~22 дня», но в таблице 7/14/39/30 | Переписан roadmap на **exit gates** вместо календарной длины. Длительности — ориентиры, не обязательство. | `docs/adr/0003-exit-gates-not-calendar.md`, `ROADMAP.md` |
| **A3** | SLSA Level 2+ vs Level 3 в одном отчёте | Целевой уровень v1.0 — **Build L2**. L3 заявляется только после доказанной изоляции сборщика. Убрано «2+». | `docs/adr/0004-slsa-build-l2-target.md`, `TZ.md` §4 |
| **A4** | «Self-rollback ≤60 сек» не откатывает миграции и данные | Разделены **три цели**: (1) откат кода — время; (2) безопасные миграции по схеме expand/contract; (3) восстановление данных с RPO/RTO. | `docs/adr/0005-separate-rollback-targets.md`, `TZ.md` §4, `docs/runbook/RUNBOOK.md` §2 |
| **A5** | Шесть «self-*» — заявления, не измерения | Каждое свойство переформулировано **опровергаемо**: что реально гарантирует + свидетельство, которое требуется. | `docs/adr/0006-falsifiable-self-properties.md`, `ARCHITECTURE.md` §5 |
| **A6** | «Секрет не меняющийся 90 дней = скомпрометирован» — риторика | Ротация по классам секретов, приоритет короткоживущих OIDC кред. Компрометация предполагается при индикаторе, а не по календарю. | `docs/runbook/RUNBOOK.md` §7, `SECURITY.md` |
| **A7** | Multi-agent: проповедь single-agent, но использовали 4 параллельных | Явное разделение: *исследование* — параллельные агенты; *исполнение с побочными эффектами* — single executor + детерминированный независимый проверяющий (тесты/схемы/readback, не второй LLM). | `docs/adr/0007-multi-agent-research-vs-execution.md`, `docs/03-ai-workflows.md` |
| **A8** | MCP — текущая ревизия спецификации не отражена | MCP закреплён за тонким внутренним адаптером (как в SINGULYAR — `Capability` + `Adapter`), версия закреплена, миграции запланированы. | `docs/adr/0008-mcp-version-pin.md`, `docs/03-ai-workflows.md` |
| **A9** | Self-publish из одного репо с приватным vault — механизм выбора не описан | Default-deny: публикуется только заметка с явным `publish: true` + CI-проверка (секреты/персональные данные). Публичный сайт собирается из **экспорта** (отдельный репо), не из vault. | `docs/adr/0009-default-deny-vault-publish.md`, `docs/04-second-brain.md` |
| **A10** | Метрики приёмки как суррогаты (coverage 80%, 100% OTel) | Метрика привязана к риску и способу измерения. Для критичных модулей — **мутационный контроль**. Реальный пример: после 35 зелёных тестов SINGULYAR подмена INCONCLUSIVE→CONFIRMED их не провалила → тест добавлен только после мутации. | `docs/adr/0010-mutation-testing-critical-paths.md`, `docs/05-devex-ci.md`, `TZ.md` §4 |
| **A11** | Мелкое: Docker Desktop vs act/devcontainer/Testcontainers | Указан container runtime: **colima** (macOS) / **podman** (Linux) / **containerd+nerdctl** (alt). Закреплено в ADR. | `docs/adr/0011-container-runtime.md`, `docs/05-devex-ci.md` |
| **RUNBOOK R1-R11** | force-unlock без проверки, `tofu destroy` защита комментарием, `git checkout` без ревью, helm rollback как универсальное лекарство, `git add .`, solo on-call без heartbeat, `curl /health`, backup без RPO/RTO, нет runbooks на painful scenarios, процедуры без предусловий/проверки, инцидент без следа | **Полная замена RUNBOOK.md** на усиленную версию (`runtime/docs/RUNBOOK_HARDENED.md`), адаптированную под Polymath OS. Шаблон процедуры: ПРЕДУСЛОВИЯ → ПРЕДПРОСМОТР → ДЕЙСТВИЕ (⛔=необратимое) → ПРОВЕРКА → ЕСЛИ УПАЛО → СЛЕД. | `docs/runbook/RUNBOOK.md` (заменён) |
| **Интеграция** | SINGULYAR EIR не упоминался в Polymath OS | SINGULYAR EIR v0.3 **интегрирован как Layer 5: Execution Kernel**. Это ядро, которое сохраняет намерение при смене исполнителя и не объявляет успех без подтверждённого состояния. | `docs/adr/0012-singulyar-eir-as-layer-5.md`, `ARCHITECTURE.md` §2 (Layer 5 добавлен) |

## Самоаудит v0.2 → v0.3 (V1-V12)

SINGULYAR команда сама провела самоаудит v0.2 и устранила 12 дефектов (V1-V12) в v0.3. Подробности — в `runtime/docs/AUDIT_POLYMATH.md` §C. Все 40 тестов v0.3 проходят, включая реальную смерть процесса (`os._exit`) между эффектом и записью.

## Принятая философия интеграции

Из Pasted Content коллег: **«Управляемая эмерджентная непрерывность»** — способность системы сохранять намерение человека при смене инструмента/канала/модели/среды/состояния-после-сбоя, восстанавливать выполнение по проверяемым данным и превращать подтверждённые результаты в воспроизводимые способности.

Это — гипотеза, не утверждение. СINGULYAR EIR — её инженерная реализация в прототипе. Polymath OS — её контекст (окружение, в котором EIR живёт: репо, second brain, devex, AI-стек).

Эмерджентность теперь **проверяема** через лестницу абляции B0→B3→EIR (`runtime/docs/EXPERIMENT_RESULTS.md`): каждое звено убирает конкретный класс отказа; тест `test_each_ablation_link_is_load_bearing` проверяет, что каждое звено несущее. Цена: в двух сценариях ядро честно отвечает UNKNOWN вместо «наверное получилось».

| **0013-slsa-build-l3-target** | ADR-0004 v1.0 SLSA L2 — build platform can forge provenance (no hermetic isolation). | ADR-0013 (Proposed, Gate-6 candidate) — v2.0 target = SLSA L3 via `slsa-framework/slsa-github-generator` + hermetic builder (`--network=none`) + reproducible build + trusted builder separation. | `docs/adr/0013-slsa-build-l3-target.md` (Proposed) |

| **0014-webrtc-adapter-as-tier2-dependency** | LIMITATIONS.md item 8 — no air-gapped P2P adapter; HTTPAdapter only covers REST. | ADR-0014 (Accepted, Gate-7) — WebRTCAdapter Python-порт of singulyar ·17 ЗАЛ; uses aiortc (Tier 2 optional). NotExecuted when aiortc absent (honest UNAVAILABLE per ADR-0006). | `docs/adr/0014-webrtc-adapter-as-tier2-dependency.md` |
| **0015-real-llm-inference-in-ci** | LIMITATIONS.md item 9 — integration test exists but SKIPs in default CI; LLM inference never exercised automatically. | ADR-0015 (Proposed, Gate-7) — weekly CI job runs real Qwen2.5-0.5B on CPU runner; closes item 9 fully when implemented in v2.0. | `docs/adr/0015-real-llm-inference-in-ci.md` |

| **0016-self-rewriting-adr-mechanism** | ADR-0001 bootstraps ADR pattern but doesn't specify how to amend it. | ADR-0016 (Accepted, Gate-7) — meta-ADR specifying ADR lifecycle (Proposed→Accepted→Deprecated→Superseded), addition/amendment/supersession process, recursive self-description. | `docs/adr/0016-self-rewriting-adr-mechanism.md` |
