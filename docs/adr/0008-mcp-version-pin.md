# ADR-0008: MCP — тонкий внутренний адаптер, версия закреплена, миграции запланированы

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A8 (MCP — актуальная ревизия спецификации)

## Context

Отчёт Polymath OS фиксировал передачу MCP в Linux Foundation (дек. 2025) и протокол A2A. По вторичным источникам действующая ревизия спецификации MCP — 2026-07-28 (stateless-ядро, убран `initialize`-handshake), а семантические соглашения OpenTelemetry для GenAI на момент проверки не стабильны. Отчёт не отражал эту динамику.

Без фиксации версии и плана миграций:
- Обновление MCP-сервера может сломать интеграцию
- Тесты против нестабильного интерфейса = flaky
- Migration становится реактивной (после падения), не проактивной

## Decision

### 1. MCP за тонким внутренним адаптером

В Polymath OS MCP — не прямая зависимость, а **тонкий слой адаптеров** поверх наших интерфейсов. Это та же архитектура, что в SINGULYAR EIR:
- `Capability` (dataclass) — декларирует, что может adapter
- `Adapter` (abstract class) — `execute(intent, idempotency_key)` + `read_state(intent, idempotency_key) → Observation`
- Конкретные адаптеры — MCP-клиенты (filesystem, git, postgres, web-search) — реализуют `Adapter`

Если MCP-спецификация меняется — обновляем **только адаптер**, не бизнес-логику.

### 2. Версия MCP закреплена в `flake.nix` / `package.json`

```nix
# flake.nix
mcpVersion = "2026-07-28";  # stateless core
```

```json
// package.json
"dependencies": {
  "@modelcontextprotocol/sdk": "pinned-sha"
}
```

Обновление — через PR с явной миграцией (см. §3).

### 3. План миграций

- **Квартальный review**: проверить, изменилась ли спецификация MCP с момента последнего обновления.
- **Migration ADR**: каждое значимое обновление — отдельный ADR (`docs/adr/NNNN-mcp-update-YYYY-MM.md`) с:
  - что изменилось в спецификации
  - какие адаптеры затронуты
  - breaking changes (если есть)
  - backward compat strategy
- **CI gate**: `mcp-compat-check` — verify, что наши адаптеры соответствуют pinned версии.
- **Fallback**: если MCP-спецификация делает breaking change без backward compat — fallback на ad-hoc function definitions (документировано в ADR-0004-mcp-fallback — будет создан если случится).

### 4. OpenTelemetry GenAI семантика — не stabilна

Не использовать её как hard dependency. Структурируем traces через **наш собственный** атрибут-набор (intent_id, capability_id, evidence_verdict), и маппинг в OTel GenAI semconv — отдельный слой (best-effort).

## Consequences

- **Positive:**
  - Изменение MCP-спецификации не ломает систему: обновляется только adapter-слой
  - Версия зафиксирована — тесты стабильные
  - Миграции — проактивные (quarterly review), не реактивные
- **Negative:**
  - Adapter overhead: каждый MCP-сервер — обёртка над нашим `Adapter` интерфейсом
  - Quarterly review — задача, не делается сама
  - OTel GenAI semconv fallback — дублирование атрибутов
- **Neutral:**
  - MCP Registry (Sep 2025) используется для discovery, но version-pinned в наших deps.

## Alternatives Considered

### Прямая зависимость от MCP-SDK без adapter layer
Отвергнуто: ломается при каждом обновлении спецификации.

### «Следуем latest» без pin
Отвергнуто: flaky тесты, неожиданные breaking changes.

### Переписываем на A2A
Отвергнуто: A2A — надстройка над MCP для agent-to-agent, не замена. Когда у нас ≥2 агента разных вендоров — A2A-ready (см. ADR-0007).

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A8
- MCP: https://modelcontextprotocol.io/
- SINGULYAR Adapter pattern: `runtime/src/singulyar_runtime.py` (class Adapter, class _EffectAdapter)
- A2A: https://github.com/a2aproject/a2a
