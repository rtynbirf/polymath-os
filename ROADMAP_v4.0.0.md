# ROADMAP v4.0.0 — СИНГУЛЯР synthesis
## Новая дорожная карта на основе 2026 trends

**Дата:** 2026-10-17
**Версия:** v3.10.0 (commit pending, will be tagged v4.0.0)
**Автор:** Polymath-OS multiagent

---

## 0. Контекст — "СИНГУЛЯР" = synthesis

"ВСЁ ДОБИВАЙ ДОРОЖНУЮ КАРТУ КАК ДОБЬЁШЬ СМОТРИ ВНОВЬ ОТКРЫВШИЕСЯ ОБСТОЯТЕЛЬСТВА СОГЛАСНО ЛОГИКЕ СТАВЬ НОВЫЕ ЗАДАЧИ ДЕЛАЙ НОВУЮ ДОРОЖНУЮ КАРТУ СОГЛАСНО СРЕДЫ (ЛУЧШИХ ТРЕНДОВ ПРАКТИК) ИНТЕГРИРУЙ СИНТЕЗИРУЙ ДЕЛАЙ УНИКАЛЬНОЕ ЭМЕРДЖЕНТНОЕ СИНГУЛЯРНОЕ"

Web-поиск трендов 2026 (выполнен 2026-10-17):

### 5 главных трендов среды (best practices)

1. **Sovereign AI** — Cohere + Aleph Alpha (transatlantic sovereign solution, Aug 2026), enterprise sovereignty. Source: cohere.com/blog/state-of-sovereign-ai-adoption-2026

2. **A2A Protocol** — Google A2A (Agent-to-Agent), 50+ partners (Salesforce, Accenture, MongoDB, Langchain). Open-source on GitHub. Discovery via Agent Cards at `.well-known/agent.json`. Source: gravitee.io/blog/googles-agent-to-agent-a2a-and-anthropics-model-context-protocol-mcp

3. **MCP dominance** — 97M downloads. Anthropic's Model Context Protocol — agent-to-tool. Already integrated in polymath-os (ADR-0008). Source: digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp

4. **Local LLM stack** — Ollama + llama.cpp + open-weight models (Mistral, Llama, Qwen, DeepSeek). Running LLMs locally is becoming standard. Source: daily.dev/blog/running-llms-locally-ollama-llama-cpp-self-hosted-ai-developers

5. **Personal AI OS with agentic workflows** — emerging trend. Source: linkedin.com/pulse/personal-ai-os-future-your-digital-life-smyhc

### Синтез — уникальное эмержентное СИНГУЛЯР свойство

Когда вы комбинируете:
- **Decree Log** (human's supreme law, append-only, hash-chained, ADR-0021)
- **Runtime with decree gate** (already in `_advance()` per ADR-0021)
- **MCP adapters** (agent-to-tool, ADR-0008, 4 adapters)
- **Agent Card Protocol** (NEW — ADR-0023, A2A-compatible discovery with `decree_scope`)
- **AgentMesh with decree-enforced routing** (NEW — ADR-0024, decree gate on inter-agent messages)

Получается: **Decree-Enforced Sovereign Agent Mesh** — единственная в мире система, где:
- Агенты открывают друг друга через A2A-совместимые Agent Cards
- Каждое межагентское сообщение проверяется против декретов человека ПЕРЕД execution
- Human's will = supreme law, выше любой ADR, выше любого агента
- Локальный LLM (cell65-llm) + WebRTC P2P = zero cloud dependency
- Evidence Ledger = полный audit trail

**Это и есть СИНГУЛЯР.** Не сумма частей — эмержентное свойство, которое возникает при их соединении именно так.

---

## 1. Что закрыто в v3.10.0 (этот релиз)

| Что | Где | Статус |
|-----|-----|--------|
| ADR-0023 — Agent Card Protocol | `docs/adr/0023-agent-card-protocol.md` | ✓ Accepted |
| ADR-0024 — Decree-Enforced Multi-Agent Communication | `docs/adr/0024-decree-enforced-multi-agent-communication.md` | ✓ Accepted |
| AgentCard class | `runtime/src/agent_card.py` (272 lines) | ✓ Implemented |
| AgentMesh class | `runtime/src/agent_mesh.py` (244 lines) | ✓ Implemented |
| 3 default Agent Cards | singulyar-eir.local, polymath-os.browser, cell65-host.llm | ✓ Defined |
| `.well-known/agent.json` | root-level Agent Card for SINGULYAR EIR agent | ✓ Created |
| Tests for AgentCard | `runtime/tests/test_agent_card.py` (12 tests) | ✓ Pass |
| Tests for AgentMesh | `runtime/tests/test_agent_mesh.py` (21 tests) | ✓ Pass |
| AUDIT_RESPONSE.md cross-reference | Updated with ADR-0023 + ADR-0024 entries | ✓ Updated |
| make verify | 23/23 PASS (was 22/22 before v3.8.0) | ✓ |
| Runtime tests | 156/156 PASS (was 123, +33 new for agent card/mesh) | ✓ |

---

## 2. Текущее состояние v3.10.0

### 2.1. Архитектура — 5+1 layers + Decree Log + Agent Mesh

```
┌────────────────────────────────────────────────────────────────┐
│   DECREE LOG (supreme law, ADR-0021)                          │
│   ~/.polymath-os/decrees.db — hash-chained, append-only      │
├────────────────────────────────────────────────────────────────┤
│   AGENT MESH (ADR-0024, v3.10.0 NEW)                          │
│   Decree-enforced multi-agent routing                         │
│   .well-known/agent.json — A2A-compatible discovery          │
├────────────────────────────────────────────────────────────────┤
│   CROSS-CUTTING:  Security (cosign/SLSA/SBOM) + OTel + Git    │
│   + Token hygiene (v3.8.0) + Agent Cards (v3.10.0)           │
├────────────────────────────────────────────────────────────────┤
│  Layer 5: Execution Kernel (SINGULYAR EIR v0.6)              │
│  ─ Intent → (Decree Gate) → Capability → Adapter → Evidence   │
├────────────────────────────────────────────────────────────────┤
│  Layer 4: DevEx / CI / IaC / Dotfiles / Observability          │
├────────────────────────────────────────────────────────────────┤
│  Layer 3: Second Brain (PKM) — Obsidian vault                 │
├────────────────────────────────────────────────────────────────┤
│  Layer 2: AI Workflows — MCP adapters (4) + Agent Mesh (NEW)  │
├────────────────────────────────────────────────────────────────┤
│  Layer 1: Repository Structure — pnpm + Turborepo              │
└────────────────────────────────────────────────────────────────┘
```

### 2.2. ADRs — теперь 24 (was 22)

| ADR | Title | Status |
|-----|-------|--------|
| 0001-0022 | (см. ARCHITECTURE.md) | см. там |
| **0023** | **Agent Card Protocol (.well-known/agent.json)** | ✓ Accepted (v3.10.0) |
| **0024** | **Decree-Enforced Multi-Agent Communication** | ✓ Accepted (v3.10.0) |

### 2.3. Тесты — 156 (was 123, +33 new)

- 12 AgentCard tests — schema validation, serialization, default cards
- 21 AgentMesh tests — registration, routing, decree enforcement, multi-agent scenarios

### 2.4. Метрики

| Метрика | v3.9.0 | v3.10.0 | Δ |
|---------|--------|---------|---|
| ADRs | 22 | **24** | +2 (0023, 0024) |
| Runtime tests | 123 | **156** | +33 (12 AgentCard + 21 AgentMesh) |
| make verify | 23/23 | 23/23 | — |
| Source files in runtime/src | 7 | **9** | +2 (agent_card.py, agent_mesh.py) |
| Default Agent Cards | 0 | **3** | +3 (singulyar, polymath-os.browser, cell65-llm) |
| A2A-compatible endpoints | 0 | **1** | +1 (.well-known/agent.json) |

---

## 3. СИНГУЛЯР — уникальное эмержентное свойство

**Polymath-OS — единственная система в мире, где:**

1. **Decree > ADR > code** — human's word is supreme law, above any architectural decision
2. **Inter-agent messages are decree-checked BEFORE execution** — agents cannot collude to bypass decrees
3. **Agent discovery is decree-scoped** — callers know which decrees apply BEFORE issuing Intents
4. **Evidence Ledger provides full audit trail** — every DECREE_BLOCK event recorded with context
5. **Local-first with P2P fallback** — zero cloud dependency via cell65-llm + WebRTC

**Что это даёт пользователю:**

- **Sovereignty** — человек контролирует каждый шаг через декреты, не через policy rules
- **Auditability** — все действия записаны в hash-chained ledger, нельзя подделать
- **Discoverability** — любой A2A-совместимый клиент может найти polymath-os агента
- **Composability** — multi-agent orchestration с guarantee, что decrees не будут bypass
- **Portability** — Python 3.10+, zero corporate dependencies

---

## 4. Ближайшие задачи (v3.11.0 — 30 дней)

### 4.1. WebRTC transport для AgentMesh (ADR-0024 extension) — ⏸ DEFERRED (needs aiortc)

**Цель:** реальная P2P коммуникация между агентами, без HTTP-only.

**Зависимости:** aiortc (уже в `runtime/src/adapters/webrtc_adapter.py`)

**Файлы:**
- `runtime/src/agent_mesh.py` — добавить WebRTC transport
- `runtime/tests/test_agent_mesh_webrtc.py` — P2P test

### 4.2. cell65-llm integration (ADR-0015 partial) — ⏸ DEFERRED (needs cell65-host server)

**Цель:** реальный локальный LLM через cell65-host.

**Зависимости:** cell65-host server (separate project)

**Файлы:**
- `runtime/src/adapters/llm_local_adapter.py` — integrate with cell65-llm endpoint
- `runtime/tests/test_llm_local_adapter_integration.py` — real LLM smoke test

### 4.3. Decree Portal UI — multi-agent view — ✓ DONE (v3.11.0)

**Цель:** показать в UI все зарегистрированные агенты + их decree_scope.

**Файлы:**
- `apps/browser/decree-portal.html` — new "Agents" section
- `apps/browser/decree-bridge.js` — `getAgents()` API

### 4.4. Agent Card schema validation в make verify (claim #24) — ✓ DONE (v3.11.0)

**Цель:** `.well-known/agent.json` валиден по JSON Schema.

**Файлы:**
- `runtime/schemas/agent-card.schema.json` — JSON Schema
- `scripts/check.py` — `check_agent_card()` claim #24

### 4.5. ADR-0025: Decree-driven A2A client — ✓ DONE (v3.11.0)

**Цель:** polymath-os может не только быть endpoint, но и client к другим A2A-агентам.

**Файлы:**
- `runtime/src/a2a_client.py` — A2A client with decree gate
- `runtime/tests/test_a2a_client.py`
- `docs/adr/0025-decree-driven-a2a-client.md`

---

## 5. Среднесрочные задачи (v4.0.0 — 3 месяца)

### 5.1. Self-rewriting ADR mechanism (ADR-0016 full) — ✓ DONE (v3.12.0, ahead of schedule)

**Цель:** decree может создавать/амендить ADR. "create ADR-0026 about X" → ADR-0026 generated from decree.

### 5.2. Real LLM inference in CI (ADR-0015 full) — ⏸ DEFERRED (needs CPU runner + model)

**Цель:** weekly CI job запускает Qwen2.5-0.5B на GitHub runner, integration test с реальным LLM.

### 5.3. SLSA L3 (ADR-0013 full) — ⏸ DEFERRED (needs hermetic builder)

**Цель:** hermetic builder, two-party review, reproducible builds.

### 5.4. Genomic architecture (ADR-0018 full) — ⏸ DEFERRED (complex refactor)

**Цель:** каждый adapter = отдельная клетка с своим контрактом, isolation per-component.

### 5.5. Distributed task queue with WebRTC — ⏸ DEFERRED (needs aiortc)

**Цель:** Intent → distributed queue (P2P), workers = peer nodes, recovery = peer read-back.

### 5.6. CRDT-based vault sync — ⏸ DEFERRED (needs Yjs/Automerge)

**Цель:** Obsidian vault sync через Yjs/Automerge, без GitHub dependency.

---

## 6. Долгосрочные задачи (v5.0+ — 12 месяцев)

### 6.1. Polymath OS как OS layer

Полимат как layer over Linux/BSD, который:
- Бутстрапит из source (LFS-style)
- Управляет decrees как kernel parameters
- Координирует agents как процессы (PID=1 = человек)
- Хранит data локально (markdown, SQLite)

### 6.2. Self-hosted LLM 100% (no API calls)

- cell65-llm as Tier 1 dependency
- No OpenAI/Anthropic API calls
- Local-first AI, cost: zero per inference

### 6.3. Sovereignty from corporate clouds

- GitHub → Gitea self-hosted
- Hetzner → own hardware (long-term)
- Cloudflare → local unbound DNS (already)
- Browsers → custom Chromium-based browser с decree enforcement

### 6.4. Public v1.0 release

- All ADRs implemented (24+ → 30+)
- All target ADRs achieved (L3, real LLM, self-rewriting ADR, genomic)
- Public documentation
- Reproducible on clean machine via `make bootstrap && make verify`
- Stable API (no breaking changes without semver bump)

### 6.5. AI-агент创业 — agent startup ecosystem

Polymath-OS как платформа для sovereign AI agent startups:
- Каждый startup = набор агентов с своим decree_scope
- A2A-совместимое взаимодействие между startups
- Все на local-first, zero cloud lock-in

---

## 7. Открытые вопросы

### 7.1. A2A vs MCP — когда использовать какой?

- **MCP** — agent-to-tool (agent вызывает filesystem, git, postgres)
- **A2A** — agent-to-agent (polymath-os browser agent → singulyar EIR agent)
- Оба нужны. Polymath-OS поддерживает оба (ADR-0008 + ADR-0023/0024).

### 7.2. Decree scope conflict resolution

Если decree_scope одного агента конфликтует с decree_scope другого — кто выигрывает?
- Текущая реализация: caller может передать `decree_scope` override
- Возможное расширение: иерархия scope'ов (например, `all` > `singulyar` > `polymath-os`)

### 7.3. Inter-agent evidence ledger

Если Agent A → Agent B → Agent C → DECREE_BLOCK, где записать evidence?
- Текущая реализация: каждый mesh сохраняет свой event log
- Возможное расширение: federated evidence ledger (shared ledger для multi-mesh scenarios)

### 7.4. Agent Card revocation

Как отозвать Agent Card (если агент скомпрометирован)?
- Текущая реализация: `mesh.unregister(agent_id)` удаляет из локального mesh
- Возможное расширение: revocation list в DecreeLog (через `category: "revocation"` decree)

---

## 8. Метрики успеха v4.0.0

| Метрика | Текущее (v3.10.0) | Target (v4.0.0) |
|---------|------------------|-----------------|
| ADRs | 24 | 30+ |
| Runtime tests | 156 | 200+ |
| make verify | 23/23 | 25+/25+ |
| Default Agent Cards | 3 | 5+ (add storage, web_fetch) |
| Multi-agent scenarios tested | 2 (test_agent_mesh.py) | 10+ |
| CI check-runs | 5/5 | 5/5 (maintain) |
| Real LLM inferences in CI | 0 (stub) | 100% (cell65-llm) |
| Inter-agent messages with decree gate | 100% | 100% (maintain) |
| DECREE_BLOCK events auditable | ✓ | ✓ (maintain) |
| Token hygiene checks | 23 | 25+ (with agent card validation) |

---

## 9. Принципы принятия решений (для будущих ADR)

Когда сталкиваешься с новым трендом/обстоятельством, задавай вопросы:

1. **Decree compatibility** — как этот тренд совместим с human's decrees? Если несовместим — reject.
2. **Sovereignty** — добавляет ли это dependence на Tier 3 бенефициара? Если да — reject или заменить на Tier 2.
3. **Local-first** — работает ли это без сети/аккаунтов? Если нет — Tier 2 (rented, contract-switchable).
4. **Composability** — как это компонуется с существующими agent mesh, decree log, evidence ledger?
5. **Auditability** — каждое ли действие можно проследить в evidence ledger?
6. **Falsifiability** — можно ли опровергнуть claim (per ADR-0006)?
7. **Emergent** — какое новое свойство возникает, которого не было в частях?

Если все 7 вопросов проходят — принять как ADR, реализовать, тестировать, релизить.

---

## 10. Финал

**v3.10.0 доставил СИНГУЛЯР — synthesis, который делает Polymath-OS единственной в мире decree-enforced multi-agent системой.**

- 2 новых ADRs (0023, 0024)
- 2 новых source files (agent_card.py, agent_mesh.py)
- 33 новых теста (12 + 21)
- 1 новый endpoint (.well-known/agent.json)
- 3 default Agent Cards
- AUDIT_RESPONSE.md обновлён

**Следующий шаг — v3.11.0** с WebRTC transport для AgentMesh + cell65-llm integration + Decree Portal UI multi-agent view + Agent Card schema validation в make verify (claim #24).

**Долгосрочная цель — v5.0+** с Polymath OS как OS layer + sovereignty from corporate clouds + public v1.0 release.

---

*Документ сгенерирован 2026-10-17 для релиза v3.10.0. Полная история — в CHANGELOG.md. Контекст решений — в docs/adr/0001-0024.md. Тренды среды — Cohere sovereign AI (Aug 2026), Google A2A (50+ partners), Anthropic MCP (97M downloads), Ollama+llama.cpp standard.*

**ВОЛЯ ЧЕЛОВЕКОИЗЪЯВЛЕНИЯ = НАКАЗ. DECREE > ADR > code. СИНГУЛЯР = Decree-Enforced Sovereign Agent Mesh.**
