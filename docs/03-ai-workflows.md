# AI Workflows — Layer 2

> Best-in-class практики для AI-augmented workflows / agent stacks / context engineering (2024-2026).

---

## Принципы

1. **Context — система, не промпт.** Контекст архитектурируется: working / reference / episodic / compression (по Anthropic, Sep 2025).
2. **Контекст — конечный и дорогой.** Context rot = -24.2% accuracy, когда релевантная информация погружена в длинный контекст.
3. **Сначала один агент, потом — несколько.** Cognition (Jun 2025): "Don't Build Multi-Agents".
4. **Tools > prompts.** Function calling + MCP точнее, дешевле, проверяемее.
5. **Eval = CI/CD для агентов.** Без promptfoo/Langfuse в пайплайне — это прототип.
6. **Cache aggressively, compute lazily.** Anthropic prompt caching = -90% input cost, -85% latency.
7. **Code is the deliverable, not the agent.** Claude Code / Aider-стиль: деливерабл = патч, коммит, PR.

## Стек (Polymath OS defaults)

| Категория | Tool | Зачем |
|---|---|---|
| Tool interface | **MCP** | Industry standard (donated to Linux Foundation / AAIF, Dec 2025) |
| Coding agent primary | **Claude Code** (terminal) | Repo-aware, лидер coding-agent index (64.8%) |
| Coding agent IDE | **Cursor** (Composer) | Multi-file editing, IDE-polish |
| Coding agent git-native | **Aider** | Transparent diffs, git-native flow |
| Coding agent autonomous | **Codex** (OpenAI) | Long-running tasks, mobile-handoff |
| Local LLM | **Ollama** (dev) + **vLLM** (prod) | Privacy-tasks, no cloud, offline |
| Local embeddings | `nomic-embed-text` через Ollama | Локальные векторы, ничего в облако |
| Eval (offline) | **promptfoo** (CI) | Golden dataset regression |
| Eval (online) | **Langfuse** (self-hosted) | Production traces |
| Eval (advanced) | **Braintrust** | CI-integrated evals |
| Observability | Langfuse + OpenTelemetry | Traces, metrics, logs |
| Gateway | **OpenRouter** | Multi-provider routing, fallback |

## Паттерны

### Single-agent + multi-tool (Anthropic baseline)

```
User → [LLM] → tool_call(MCP) ─┐
       ↑                       │
       └── tool_result ────────┘
                ↓
         structured output (JSON Schema) → downstream
```

Это рабочая лошадка. Anthropic engineering blog, OpenAI cookbook, Cursor, Claude Code — все ходят вокруг этого паттерна.

### Plan-and-Execute (long-horizon)

```
[Planner LLM] ── план ──→ [Executor LLM] ── действия ──→ results
       ↑                                              │
       └──── re-plan (если не получилось) ───────────┘
```

Лучше, чем ReAct, для long-horizon: меньше токенов в каждом цикле, чёткая трассировка, возможность параллельного выполнения.

### Context engineering (Anthropic)

```
┌─────────────────────────────────────────────────┐
│  1. Working context   — текущая задача, окно    │
│  2. Reference context — RAG / retrieval / MCP   │
│  3. Episodic memory   — прошлые run-ы, traces   │
│  4. Compression       — summarize + eviction    │
└─────────────────────────────────────────────────┘
```

### MCP-нативный агент

```
Agent ── MCP client ──┬── MCP server: filesystem
                      ├── MCP server: git
                      ├── MCP server: postgres
                      ├── MCP server: web-search (Ollama)
                      └── MCP server: own services
```

MCP Registry (Sep 8, 2025) — "app store для MCP-серверов".

### Prompt caching как архитектурное решение

Не «оптимизация в конце», а проектирование под cache-hit:

```
[Static system prompt] [long docs] [few-shot]  ← cache_control: persistent
                                              ↓
[user turn 1..N]                              ← cache hit 0.1× cost
```

Anthropic: -90% cost, -85% latency. **Ловушка**: cache-miss на коротких промптах может увеличить bill на 25%. Метрика: cache-hit-ratio.

## Anti-patterns

- **Prompt spaghetti** — один мега-промпт с 30+ инструментами, 5K-токенным system message.
- **Multi-agent без причины** — dispersed decision-making + context propagation = хрупкость.
- **Unmanaged context** — добавлять, не удалять. Context rot.
- **Tool sprawl** — 50 MCP-серверов «на всякий случай».
- **Reflexion на той же модели** — повторяет те же заблуждения. Нужен другой model для critique.
- **Over-engineered orchestration** — LangGraph с 40 нодами для single-agent задачи.
- **Eval после продакшена** — golden dataset должен быть в CI с первого дня.
- **Vendor lock-in без fallback** — только OpenAI или только Anthropic.
- **Caching без метрики** — cache-hit-ratio обязательно.

## LFS-рекомендации

См. `ROADMAP.md` Фаза 2, дни 29-35. Резюме:

1. OpenRouter или self-hosted proxy как единый gateway
2. MCP как единственный tool-интерфейс (никаких ad-hoc functions)
3. Single-agent baseline + 4 подсистемы context engineering
4. Coding-agent стек: Claude Code (primary) + Cursor (IDE) + Aider (git-native) + Ollama (privacy)
5. promptfoo в CI + Langfuse в production
6. Local LLM fallback: Ollama (dev) + vLLM (prod) + llama.cpp (edge)
7. DSPy + MIPRO для повторяющихся задач с метрикой (не для одноразовых)
8. A2A-ready если несколько агентов разных вендоров
9. Quarterly anti-pattern audit: tool count, context-size, eval coverage
10. Documentation-as-code: каждый агент = MCP-server-описание

## Референсы

- Anthropic context engineering: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- MCP: https://www.anthropic.com/news/model-context-protocol
- MCP Registry: https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview
- A2A protocol (Google): https://github.com/a2aproject/a2a
- Cognition "Don't Build Multi-Agents": https://cognition.com/blog/dont-build-multi-agents
- promptfoo: https://www.promptfoo.dev
- Langfuse: https://langfuse.com
- Claude Code: https://www.anthropic.com/claude-code
- Aider: https://aider.chat
- Cursor: https://cursor.com
- Ollama: https://ollama.com
- vLLM: https://github.com/vllm-project/vllm
