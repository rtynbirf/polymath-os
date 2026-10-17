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

| **0017-ecosystem-governance-protocol** | Cross-repo execution was ad-hoc (manual API calls). No formal protocol for audit → issue → PR → merge cycle. | ADR-0017 (Accepted, v2.5.0) — formalizes: audit cadence, cross-repo execution protocol (Intent→GitAdapter→PR→merge), governance workflow, issue lifecycle. All 5 critical findings MERGED. | `docs/adr/0017-ecosystem-governance-protocol.md` |

| **0018-genomic-architecture** | No formalization of the holographic/genomic principle (each part = whole at contract level). | ADR-0018 (Accepted, v2.7.0) — each adapter carries full Adapter contract, each audit carries full methodology, each repo carries AGENTS.md. Holographic invariant: contract + methodology + rules + intent in each part. | `docs/adr/0018-genomic-architecture.md` |
| **0019-observability-first** | SINGULYAR EIR kernel has no structured trace output — no real-time observability. | ADR-0019 (Accepted, v2.7.0) — structured JSON traces to stderr at key state transitions (INTENT_ACCEPTED, CAPABILITY_SELECTED, EXECUTION_STARTED, EVIDENCE_VERIFIED, STATE_TRANSITION). OTel-compatible attribute names. Zero external deps. | `docs/adr/0019-observability-first.md` |

| **0020-manifest-driven-architecture** | Hash not verified at loader (AUDIT_CELL65_LLM L4). No HoloManifest pattern. Version-marker  lets equal through. | ADR-0020 (Accepted, v2.8.0) — hash-pin-at-loader (verify_model_hash), PREPARED verdict (documented), HoloManifest pattern (documented), version-marker strict , eir:// URI scheme (documented). | `docs/adr/0020-manifest-driven-architecture.md` |

| **0021-decree-as-supreme-law** | Human's will (PAROLE) not recorded as binding law. ADRs written by AI, not by human's raw expression. | ADR-0021 (Accepted, v3.2.0) — Decree Log: SQLite append-only hash-chained journal of human's raw expressions. DECREE > ADR > code. check_compliance() enforces prohibition decrees. 8 tests. | `docs/adr/0021-decree-as-supreme-law.md` |

| **0022-decree-portal-as-human-interface** | Human needs direct decree interface. | ADR-0022 (Accepted). apps/browser/decree-portal.html. | `docs/adr/0022-decree-portal-as-human-interface.md` |

| **0023-agent-card-protocol** | 2026 A2A ecosystem (Google A2A, 50+ partners) requires Agent Card discovery. Polymath-OS agents need to be discoverable + advertise decree_scope. | ADR-0023 (Accepted, v3.10.0) — Agent Card Protocol at `.well-known/agent.json`. JSON schema with id/name/version/capabilities/decree_scope/endpoints/auth. Polymath-OS-specific `decree_scope` extension. 3 default cards: singulyar-eir.local, polymath-os.browser, cell65-host.llm. 12 tests. | `docs/adr/0023-agent-card-protocol.md` |

| **0024-decree-enforced-multi-agent-communication** | Standard A2A (Google) and MCP (Anthropic) trust agents — no supreme law layer. Polymath-OS unique: human's decrees must be enforced on inter-agent messages BEFORE execution. | ADR-0024 (Accepted, v3.10.0) — Decree-Enforced Multi-Agent Communication. AgentMesh class routes Intents between agents with decree gate. DECREE_BLOCK JSON-RPC error response. Evidence Ledger audit trail. **UNIQUE EMERGENT СИНГУЛЯР property** — no other agent system has decree-enforced multi-agent communication. 21 tests. | `docs/adr/0024-decree-enforced-multi-agent-communication.md` |

| **0025-decree-driven-a2a-client** | ADR-0024 only enforces INBOUND decrees — when polymath-os acts as A2A client (sends Intent to external agent), decree gate is too late. Sensitive data already on the wire before remote agent checks. | ADR-0025 (Accepted, v3.11.0) — Decree-Driven A2A Client. A2AClient class checks OUTBOUND decree gate BEFORE any network request. Default scope="outbound" for outbound-only decrees (PII, encryption, etc.). v0.6.1 regex extension: added {send, share, transmit, expose} verbs to _PROHIBITION_REGEX. 17 tests. **Symmetric decree enforcement** (inbound ADR-0024 + outbound ADR-0025). | `docs/adr/0025-decree-driven-a2a-client.md` |

| **0026-decree-driven-adr-amendment-mechanism** | ADR-0016 specifies the meta-process for ADRs (lifecycle: Proposed→Accepted→Deprecated→Superseded) but provides no automation. Per ADR-0021 (decree as supreme law), decrees should drive ADR operations. | ADR-0026 (Accepted, v3.12.0) — **Closes ADR-0016 (target-for-v1.0 → fully implemented v3.12.0)**. AdrAmender class processes decrees with category='amendment' and: (1) creates new ADRs from template, (2) amends existing ADRs (append-only amendments.log, original file immutable per ADR-0016 §3), (3) supersedes ADRs (generates new ADR with Supersedes header), (4) deprecates ADRs. New 'amendment' decree category. 4 regex patterns: create/amend/supersede/deprecate. 24 tests. **Decrees now drive meta-architecture** — the human's word modifies the architectural rules, not just runtime behavior. | `docs/adr/0026-decree-driven-adr-amendment-mechanism.md` |
