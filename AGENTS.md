# AGENTS.md — Polymath OS

> README.md — для людей, этот файл — для машин. Не смешивать: здесь только
> то, что нужно агенту, чтобы работать с репой и не ломать дом.

## Кто мы

Open-source LFS-style rebuild персональной операционной системы. Это не
«отчёт», а рабочий reproducible код: 5 слоёв + cross-cutting concerns,
всё в одном self-contained git-дереве. Лицензия: MIT.

**Главное правило: НЕ СЛОМАЙ `make verify`.** Open-source contract. Если
`make verify` выходит ≠0 — что-то сломано. Каждый PR обязан проходить.
Перед commit'ом — всегда проверяй.

## 5 слоёв + cross-cutting

1. **Repository Structure** — pnpm + Turborepo + Changesets + CODEOWNERS
2. **AI Workflows** — MCP-native, version pinned 2026-07-28 (ADR-0008)
3. **Second Brain (PKM)** — vault/ (PARA+MOC), Obsidian config, Quartz v4 garden
4. **DevEx / CI / IaC** — OpenTofu + Nix Flakes + cosign/SLSA L2 + OIDC trust
5. **Execution Kernel** — SINGULYAR EIR v0.6.1 in `runtime/`

Cross-cutting: Security (cosign/SLSA/SBOM) + OpenTelemetry + git.

## Порядок чтения ADRs

Если времени мало, читай в порядке:
1. ADR-0002 (Sovereignty Registry) — что суверенное, что арендованное
2. ADR-0012 (SINGULYAR EIR as Layer 5) — ядро, которое сохраняет намерение
3. ADR-0006 (Falsifiable self-*) — каждое самодействие имеет отрицательный тест
4. ADR-0016 (Self-rewriting ADR mechanism) — как менять правила
5. ADR-0009 (Default-deny vault publish) — что публикуется, что нет

Остальные ADRs (0001-0015) — по контексту задачи.

## Контракты (7)

1. **Sovereignty** — Tier 1 (offline) > Tier 2 (replaceable) > Tier 3 (closed)
2. **Falsifiability** — каждое утверждение проверяемо через `make verify`
3. **Default-deny** — `publish: true` требуется, не `publish: false`
4. **Failover** — `NotExecuted` raised, kernel doesn't lie CONFIRMED
5. **Audit** — recursive, методология generic across levels
6. **Drill** — еженедельный sovereignty drill (Monday 03:00 UTC)
7. **Self-rewriting** — ADRs могут быть superseded via new ADR (ADR-0016)

## Команды

```
make help        # список всех команд
make verify      # 20 проверок (12 original + 8 pattern)
make test        # verify + cd runtime && python3 scripts/check.py
make bootstrap   # nix develop + pnpm install (если nix/pnpm доступны)
make dev         # tilt up
make lint        # pnpm turbo run lint (biome check . from root)
make typecheck   # pnpm turbo run typecheck
make build       # pnpm turbo run build (non-blocking on Quartz v4)
make ci-local    # act -W .github/workflows/ci.yml -j ci
make sign        # cosign sign --yes $image (interactive)
make clean       # rm node_modules/dist/.next/.turbo/target/__pycache__
```

## Конвенции

### Файлы
- **Не коммитить**: `.env`, `.env.local` (используй SOPS+age per ADR-0002 Tier 1);
  `*.age` private keys, `age-identity.txt`; `vault/.obsidian/workspace*`;
  `__pycache__/`, `*.pyc`; `node_modules/`, `dist/`, `.turbo/`, `.next/`
- **Markdown**: русский prose в комментариях, английский для identifiers/URL/commands
- **Conventional Commits**: trunk-based, ≤24h feature branch, squash-merge

### Добавление новой зависимости
1. Добавить в `package.json` (для JS/TS) или `pyproject.toml` (для Python)
2. Проверить ADR-0002 Tier (sovereign core? rented? closed format?)
3. `make verify` check 06 (Sovereignty Registry covers package.json deps) должен пройти

### Добавление нового ADR
1. Копировать `docs/adr/template.md` → `docs/adr/NNNN-<kebab-slug>.md`
2. Заполнить Date, Status (Proposed), Context, Decision, Consequences
3. Добавить строку в `docs/AUDIT_RESPONSE.md` (cross-reference)
4. `make verify` check 05 (AUDIT_RESPONSE cross-references all ADRs) должен пройти
5. Per ADR-0016: если это мета-ADR (изменяет процесс ADR), явно указать

### Добавление нового адаптера (SINGULYAR EIR consumer)
1. Создать `runtime/src/adapters/<name>_adapter.py`
2. Subclass `singulyar_runtime.Adapter`
3. Реализовать `execute(intent, key)` + `read_state(intent, key) → Observation`
4. Объявить `CAPABILITIES` tuple (Capability dataclass)
5. Tri-state Observation: PRESENT/ABSENT/UNAVAILABLE (per ADR-0006)
6. NotExecuted on no-effect (per ADR-0007); RuntimeError on effect-may-have-happened
7. Написать тесты в `runtime/tests/test_<name>_adapter.py`
8. S15 partial cache-miss test (sibling key doesn't pollute absent key)
9. Добавить в `runtime/pyproject.toml` `also_copy` (для mutmut)
10. `cd runtime && python3 scripts/check.py` должен пройти

### Запуск sovereignty drill
```bash
python3 scripts/sovereignty_drill.py --service sentry
# JSON: {verify_pass, runtime_tests_pass, recovery_time_ms}
```

### Запуск multi-agent demo
```bash
PYTHONPATH=runtime/src:runtime/src/adapters python3 scripts/multi_agent_demo.py -n 5
# JSON: {agent_count, final_ledger_event_count, duplicate_writes, lead_violations}
```

## Реальные consumers SINGULYAR EIR ядра

| Adapter | Транспорт | Risk | Offline | Source |
|---|---|---|---|---|
| LLMLocalAdapter | Offline LLM (rule-layer deterministic) | low-medium | True | singulyar ·21 ОБЩЕНИЕ |
| HTTPAdapter | REST request/response | low-medium | False | standard REST |
| WebRTCAdapter | Air-gapped P2P (no STUN/TURN) | low-medium | True | singulyar ·17 ЗАЛ |

Все 3 реализуют один контракт: `execute(intent, key)` + `read_state(intent, key) → Observation tri-state`.

## 9 паттернов из AUDIT_SINGULYAR (machine-checked)

| # | Паттерн | CI check | Status |
|---|---|---|---|
| 1 | Manifest exclusivity | check.py #13 | dormant |
| 2 | Counter-from-source | check.py #14 | dormant |
| 3 | CSP no scheme-only connect-src | check.py #15 | dormant |
| 4 | Sovereignty drill runner exists | check.py #16 | ACTIVE |
| 5 | Sequential triage rule-layer-first | check.py #17 | ACTIVE |
| 6 | No silent SW registration failure | check.py #18 | dormant |
| 7 | Storage eviction with protected-key Set | check.py #19 | dormant |
| 8 | Identity backup documented | check.py #20 | dormant |
| 9 | Sovereignty drill in CI weekly | sovereignty_drill.yml cron | ACTIVE |

## Честные границы

- **Real LLM weights**: нет в CI по умолчанию (ADR-0015 Proposed, v2.0)
- **WebRTC async send**: NotImplementedError (v0.5 — asyncio bridge)
- **Multi-writer**: per-ledger-file only (cross-ledger v0.5)
- **SLSA L3**: ADR-0013 Proposed (hermetic builder v2.0)
- **publish-garden.yml**: падает на Quartz v4 bootstrap (upstream git repo)
- **Mutation score**: 64.5% (target ≥80%, Gate-2.5 pending)

Per ADR-0006: каждый пробел DOCUMENTED в `runtime/docs/LIMITATIONS.md`.

## Истина о числах

Счётчики: из `make verify` (20 checks) + `cd runtime && python3 scripts/check.py` (86 tests).
Числа в release notes — из реальных run. Если `make verify` не проходит —
числа в release notes не имеют силы.

Один факт — одно место.
