# ADR-0012: SINGULYAR EIR как Layer 5 — Execution Kernel

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Source:** Pasted Content (бриф коллег), SINGULYAR EIR v0.3

## Context

Polymath OS изначально описывал 4 слоя: Repository / AI Workflows / Second Brain / DevEx-CI + cross-cutting (security / OTel / git). Эти слои — **окружение** (env), в котором работает человек-полимат.

Но в окружении не хватает **исполнительного ядра** — компонента, который:
- принимает намерение человека (`Intent`)
- выбирает исполнителя (`Capability` + `Adapter`)
- выполняет с idempotency key + write-ahead
- проверяет результат через **независимый verifier** (не тот же executor)
- восстанавливается после сбоя по **readback состояния**, не по догадке
- не объявляет успех без подтверждённого состояния

Паста от коллег明确提出 гипотезу: **«Управляемая эмерджентная непрерывность»** — способность системы сохранять намерение человека при смене инструмента/канала/модели/среды/состояния-после-сбоя.

SINGULYAR EIR v0.3 — инженерная реализация этой гипотезы в Python-прототипе:
- 40 тестов, включая реальную смерть процесса (`os._exit`) между эффектом и записью
- Лестница абляции B0→B3→EIR доказывает, что каждое звено несущее
- SQLite-ledger с WAL, hash-linked events, проверкой при открытии
- Схемы Intent/Capability/Evidence (JSON Schema, fail-closed validator)
- HTML-демо воспроизводит реальные журналы ядра по 14 сценариям сбоев

## Decision

### Layer 5: Execution Kernel (SINGULYAR EIR)

Добавить 5-й горизонтальный слой в архитектуру Polymath OS:

```
┌────────────────────────────────────────────────────────────────┐
│   CROSS-CUTTING:  Security (cosign/SLSA/SBOM)  │  OTel  │  Git │
├────────────────────────────────────────────────────────────────┤
│  Layer 5: Execution Kernel (SINGULYAR EIR)                    │
│  ─ Intent → Capability → Adapter → Observation → Evidence     │
│  Цель: сохранить намерение при смене исполнителя;             │
│       не объявлять успех без подтверждённого состояния        │
├────────────────────────────────────────────────────────────────┤
│  Layer 4: DevEx / CI / IaC / Dotfiles / Observability          │
├────────────────────────────────────────────────────────────────┤
│  Layer 3: Second Brain (PKM)                                   │
├────────────────────────────────────────────────────────────────┤
│  Layer 2: AI Workflows / Agent Stack                           │
├────────────────────────────────────────────────────────────────┤
│  Layer 1: Repository Structure / Monorepo                     │
└────────────────────────────────────────────────────────────────┘
```

### Что Layer 5 добавляет к 4 существующим

| Свойство | Без Layer 5 | С Layer 5 |
|---|---|---|
| Intent preservation | agent может «забыть» исходную цель при long task | intent_id + HMAC fingerprint; `recover` проверяет соответствие |
| Failover | ad-hoc fallback, риск дублирования эффекта | `NotExecuted` гарантия → safe failover |
| Verification | agent claim «я сделал» | independent verifier: PASS/FAIL/INCONCLUSIVE по readback состояния |
| Recovery after crash | restart, не знаю что произошло | `_rehydrate` → UNKNOWN → `recover()` по readback |
| Consent | implicit | explicit `WAITING_FOR_HUMAN` для high-risk, `grant_consent`/`cancel` |
| Ledger | mutable logs | hash-linked SQLite events, fingerprints (не payload) |
| UNKNOWN outcome | смешивается с ABSENT/FAIL | first-class status, честный ответ «не могу сказать» |

### Где живёт код

```
polymath-os/runtime/    # SINGULYAR EIR v0.3
├── src/
│   ├── singulyar_runtime.py    # ядро: state machine, policy, recovery
│   ├── sqlite_ledger.py        # durable hash-linked journal (WAL)
│   └── schema_validate.py      # fail-closed validator
├── schemas/
│   ├── intent.schema.json
│   ├── capability.schema.json
│   └── evidence.schema.json
├── tests/             # 40 тестов, включая реальную смерть процесса
├── experiments/       # ablation B0→B3→EIR
├── prototype/         # HTML replay реальных журналов
├── docs/              # AUDIT_POLYMATH, ROADMAP, TECHNICAL_SPEC, ...
└── scripts/check.py   # тесты, демо, отчёты, контрольные суммы
```

### Интеграционные точки с другими слоями

- **Layer 1 (Repository):** `runtime/` в monorepo, изменения через PR с eval-gate
- **Layer 2 (AI Workflows):** AI agents → SINGULYAR `Intent` (через adapter), `Capability` объявляется для каждого MCP-tool
- **Layer 3 (Second Brain):** each ADR / RUNBOOK procedure → potential `Intent` template; incident → `Intent` + `Evidence` в `runtime` ledger
- **Layer 4 (DevEx/CI):** `runtime/tests/` в CI pipeline; mutation testing на `singulyar_runtime.py` (ADR-0010)
- **Cross-cutting:** cosign signing на `runtime/` releases; OTel traces с `intent_id`/`capability_id`/`evidence_verdict` атрибутами; git — источник правды

### Эмерджентность — проверяемая гипотеза

Не утверждение, а **гипотеза**. Что доказано и что нет — `runtime/docs/LIMITATIONS.md`. Как опровергнуть — `runtime/docs/EXPERIMENT_PLAN.md`.

Лестница абляции (`runtime/docs/EXPERIMENT_RESULTS.md`):
- B0: нет политики → любой сбой = ложный CONFIRMED
- B1: добавлена policy → ловит нарушения permissions
- B2: добавлен failover → ловит «адаптер не исполнил»
- B3: добавлен verifier → ловит «адаптер сказал ок, но эффекта нет»
- EIR: добавлен write-ahead+readback → ловит «сбой между эффектом и записью»

Тест `test_each_ablation_link_is_load_bearing` проверяет, что каждое звено действительно **несущее**: его удаление проваливает конкретный класс сценариев.

## Consequences

- **Positive:**
  - Появляется 5-й слой — исполнительное ядро, без которого 4 других — окружение без execution.
  - Эмерджентность — гипотеза, а не декларация (исправляет A5).
  - Инцидент = `Intent` + `Evidence` (исправляет R11).
  - Честный UNKNOWN — никогда «наверное получилось».
- **Negative:**
  - SINGULYAR EIR v0.3 — прототип (не production). Дорожная карта в `runtime/docs/ROADMAP.md`.
  - 40 тестов — на synthetic data. Production migration — отдельная работа.
  - Интеграция с MCP-серверами требует написания adapter-классов для каждого MCP-tool.
- **Neutral:**
  - `runtime/` как git submodule или monorepo subdir — ADR-0012 фиксирует: monorepo subdir (in-tree).

## Alternatives Considered

### Оставить 4 слоя (без Execution Kernel)
Отвергнуто: 4 слоя — окружение, но не execution. Без ядра эмерджентность — только слоган.

### Использовать готовое (LangGraph / Temporal / Inngest)
Частично: Temporal — для long-running workflows (можно добавить как adapter). Но SINGULYAR EIR — более тонкий слой с фокусом на intent preservation + evidence verification, чего Temporal сам по себе не даёт.

### Layer 5 = «AI Orchestrator» (не EIR)
Отвергнуто: orchestrator — про сoordination, не про intent preservation. SINGULYAR — про intent preservation.

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` (весь)
- SINGULYAR EIR v0.3: `runtime/` (in-tree)
- TECHNICAL_SPEC: `runtime/docs/TECHNICAL_SPEC.md`
- ROADMAP интеграции: `runtime/docs/ROADMAP.md` (последняя секция)
- EXPERIMENT_RESULTS: `runtime/docs/EXPERIMENT_RESULTS.md`
- LIMITATIONS: `runtime/docs/LIMITATIONS.md`
- Pasted Content (бриф коллег): `/home/z/my-project/upload/Pasted Content_1792135112722.txt`
