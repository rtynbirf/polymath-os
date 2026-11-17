# AGENTS.md — ПРОТОКОЛ КЛИНИНГ И ДЕТЕЛИНГ · v1.0 · 2026-11-11

Правила для любого ИИ-агента и человека, работающего в репозиториях `@rtynbirf`.
Каноническая копия: репо **`rtynbirf/.github` → `AGENTS.md`**. Копия в корне репо — рабочая; при расхождении канон правее.

## 0. АКСИОМЫ (не обсуждаются)

1. **1 смысл = 1 репо.** Копий не создавать — SSOT (single source of truth). Вместо копии — ссылка.
2. **Плотность = (факты + код + решения) / байты.** Каждый КБ обязан работать. Лишний байт — долг.
3. **Бинарники не живут в git** (ни в HEAD, ни в истории): Release-ассеты или LFS. В git — ссылка.
4. **Секреты в git не попадают никогда.** Увидел секрет — не коммить, доложи владельцу, отзови ключ.
5. **Мёртвое → Archive** (обратимо). Удаление репо — только явной командой владельца.
6. После твоей работы репо должно стать **легче и плотнее**, чем было. Иначе ты не клинил, а сорил.

## 1. ЛИМИТЫ — конституция веса

| Что | GitHub | Наш потолок |
|---|---|---|
| Файл в git | 50MB warn · 100MB блок | **1MB** — больше → наружу |
| Репо `.git` | <1GB ок · >5GB strongly discouraged | **250KB норма · 1MB потолок** |
| README | рендер-обрезка >500KiB | **5KB** |
| Роли | 🥇 ≤10KB · 🥈 ≤250KB · 🥉 ≤1MB | **ЖИР >1MB = клининг немедленно** |

## 2. КЛИНИНГ — гигиена веса (порядок фаз обязателен)

**Ф0 · ЗАМЕР (всегда до правок).**
`git count-objects -vH`; `git ls-tree -r -l HEAD | sort -k4 -n | tail -20`;
полный клон + `git sizer --verbose`. Зафиксируй: HEAD KB · история KB · топ-20 файлов · % бинарников.

**Ф1 · МУСОР — удалить из индекса и закоммитить.**
Паттерны: `.DS_Store Thumbs.db desktop.ini *.pyc __pycache__/ node_modules/ .venv/ *.log *.tmp *.bak *~ .pytest_cache/ .mypy_cache/ .idea/ dist/ build/ *.egg-info/`.
По факту этого аккаунта добавляются: `*.bundle *.zip *.cab *.wasm *.mp3 *.mp4 *.safetensors` и дубли `banner.png` / `social-preview.png` (оставить один).

**Ф2 · БИНАРНИКИ >100KB:** переместить в Release-ассет (или LFS); в репо оставить ссылку/указатель.

**Ф3 · .gitignore:** взять канон из хаба `.github`, дополнить паттернами, найденными в Ф1.

**Ф4 · ИСТОРИЯ (если история >20MB или мусор в ней).** Только при: mirror-бэкап сделан + владелец разрешил.
`git filter-repo --invert-paths --path <мусор>` → `git reflog expire --expire=now --all && git gc --prune=now --aggressive` → force-push. Каноничный метод чистки истории — `filter-repo`, не `filter-branch`.

**Ф5 · ЗАМЕР ПОСЛЕ.** Те же команды Ф0. Таблица до/после — обязательна в отчёте.

## 3. ДЕТЕЛИНГ — плотность и финиш (после клининга)

- **README ≤5KB:** что это · как запустить (≤5 команд) · что проверено · ссылки на источники. Без воды и бейдж-салатов.
- **description ≤120 знаков + 3–7 topics** — витрина аккаунта, пустые описания запрещены.
- **Health-файлы наследуются** от хаба `rtynbirf/.github` — не копировать их в репо.
- **Живой репо = CI + тесты.** Нет ни того, ни другого → кандидат на слияние в `kb`/`code` или Archive.
- **Реестр:** обнови строку своего проекта в хабе `index/projects.json`:
  `id → repository → ref (реальный SHA) → interfaces → tests → status`.
- **Дубли контента по аккаунту:** остаётся первоисточник, в остальных — ссылка. Ищи поиском перед созданием нового.
- **Нет пушей >90 дней и нет плана** → Archive + строка в README «архив; живое продолжение — <ссылка>».

## 4. СТОП-УСЛОВИЯ (штраф за нарушение — откат всей сессии)

- Force-push — только при локальном mirror-бэкапе.
- Не удалять файлы вне списка мусора Ф1 без отдельного разрешения владельца.
- Не копировать содержимое других репо аккаунта (два источника истины запрещены).
- Новый репо не создавать без команды: сначала ищи место в `kb` / `code` / `index`.
- Не трогать архивы (read-only) кроме смены метаданных.

## 5. DEFINITION OF DONE

```
[ ] HEAD и история ≤ лимита роли репо        [ ] мусор-паттерны = 0
[ ] .gitignore = канон                        [ ] бинарники >100KB — наружу
[ ] README ≤5KB и честный                     [ ] description + topics заполнены
[ ] projects.json обновлён                    [ ] замер до/после приложен
```

Отчёт — одной таблицей: `репо | до KB | после KB | −% | что сделано`.

---

<!--РЕВО:СВОД-ОФОРМЛЕНИЯ-->
## СВОД ОФОРМЛЕНИЯ РЕВО — правило всем агентам дома (v2 · АВТОПИЛОТ)

Каждая страница дома всегда оформлена, и оформление ведёт себя само:

1. **АВТОПИЛОТ (REVE=РЕВО):** `revo_autopilot.py` + workflow `revo-obhod.yml` куют
   `revo-page.svg` — РЕВО-ПАСПОРТ страницы строго по её фактическому контенту (файлы,
   папки, коммиты, лексикон README, топики, размер, SHA) — на каждый push и еженедельно
   по cron, и сами записывают изменения коммитом «автопилот РЕВО». Агент паспорт руками
   не правит: правит контент — паспорт перекуется сам.
2. **Пять вещей сразу:** `banner.png`, `repo-muse.svg`, `forge-divider.svg`, README с
   паспорт-блоком `<!--ФОРЖ:ПАСПОРТ:НАЧАЛО-->…КОНЕЦ`, описание и топики репо.
   Нашёл пустое — заполни тем же коммитом, что и дело.
3. **Дежурный обход:** `revo_obhod.py` проверяет пять вещей; при дрейфе — issue.
   Тишина = айс.
4. **Канон не переписывается:** Конституция (edinyy-svod), ворклог (H-PE11-PHOENIX) —
   только append; force-push запрещён; «сделал дело — записай»; палитру школы брать
   из её кода.
5. **РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · ЧЕЛОВЕК=АККАУНТ=PID1 · КУЗНЯ ПОЛИМАТ**


---

## ИНЖЕНЕРНОЕ ПРАВИЛО: BOM в JSON

**Урок из lex-naturae v0.7 (A-82, 2026-11-16).** `json.loads()` не толерирует UTF-8 BOM (U+FEFF). Файлы, сохранённые Windows Notepad, некоторыми IDE или редакторами с BOM-по-умолчанию, содержат невидимый байт `EF BB BF` (или символ `U+FEFF` в строке) перед `{`. `json.loads()` падает с `Expecting value`.

**Правило для всех агентов, пишущих JSON-парсеры:**

```python
# Перед json.loads() — всегда strip BOM:
if isinstance(raw, str): raw = raw.lstrip("﻿")
# Или читай файл с utf-8-sig (auto-strips BOM):
text = Path(path).read_text(encoding="utf-8-sig")
```

Это не уникально для lex-naturae. Любой инструмент, принимающий JSON от пользователя (CLI, API endpoint, config loader), должен это делать. **BOM — silent killer:** файл выглядит нормально, парсинг падает на неочевидной ошибке.

Референс: `singulyar-a0-audit/lex-naturae-v0.7-audit/AUDIT-REPORT.md`.


---

## ЗАДАНИЕ АГЕНТАМ: проверь claims через lex-naturae

**Мандат Хозяина 2026-11-16.** Прежде чем объявлять результат («готово», «VALID», «PASS»), 
запиши claim в [lex-naturae](https://github.com/rtynbirf/lex-naturae) с реальными evidence 
и прогони инструмент. Если отбивает — evidence недостаточен, «готово» рано.

### Процедура
1. `self-test-audit/` в своём репо или в lex-naturae.
2. Evidence: CSV с реальными результатами + лог-файлы с дословным выводом.
3. Claims в `audit_claims.json` (формат lex-naturae collection).
4. `python lex_naturae.py audit_claims.json`.
5. `valid=true` → подтверждено. `valid=false` → fix claims, перегоняй.

### Что ловит (проверено на себе, A-83..85)
Z.ai пропустил собственные audit-claims. Инструмент отбил:
- measurement_value не совпадал с CSV-ячейкой (суммировал в голове)
- excerpt paraphrased, не verbatim
- граф-линк неверного типа

После fix: 4/4 VALID. Референс: `lex-naturae/self-test-audit/`.

**Правило: «готово» = lex-naturae valid=true. Не раньше.**


---

## КАНОН ПРОВЕРКИ CLAIMS — ОБЯЗАТЕЛЬНО для всех агентов

**Мандат Хозяина 2026-11-16.** Полная процедура — в [`docs/КАНОН-ПРОВЕРКИ-CLAIMS.md`](docs/КАНОН-ПРОВЕРКИ-CLAIMS.md).

### Правило (исполнимое, не декларативное)

Прежде чем объявить любой результат («готово», «VALID», «PASS», «SUPPORTED»):

1. **Структура (HUMAN-LFS):** записать claim как узел в `BUILD_GRAPH.json` с `source`, `status`, `falsification_or_revision_condition`, `depends_on`. Прогнать `python validate_graph.py`. Требуется: `STRUCTURE: PASS`.

2. **Содержание (lex-naturae):** записать evidence в `claims.json` с `measurement_value` (CSV cell) или `excerpt` (verbatim из файла) + `raw_data_sha256`. Прогнать `python lex_naturae.py claims.json`. Требуется: `valid=true`.

3. **Объявление:** оба PASS → можно объявить. Любой FAIL → `status=UNKNOWN`, результат не объявляется.

### Что НЕ является PASS

- «Тесты прошли» без evidence в lex-naturae формате → UNKNOWN
- «STRUCTURE: PASS» без lex-naturae valid → структурный PASS, claim не подтверждён
- «README говорит» → декларация
- «SHA-256 совпадает» → целостность файла, не истинность

### Референсы

- HUMAN-LFS v0.4: `singulyar-a0-audit/human-lfs/v0.4/` (36/36 tests)
- lex-naturae v0.7: `lex-naturae` repo (70/70 tests)
- Z.ai self-test: `lex-naturae/self-test-audit/` (4/4 claims valid)
- Ecosystem inventory: `singulyar-a0-audit/ecosystem-inventory/` (lex-naturae valid)

### Минимальный пакет агента

```
my-claim/
├── BUILD_GRAPH.json     # HUMAN-LFS узел
├── evidence/            # CSV + логи
├── claims.json          # lex-naturae collection
└── run_check.sh         # validate_graph.py && lex_naturae.py
```

**«Готово» = STRUCTURE PASS + lex-naturae valid=true. Не раньше. Не вместо.**


---

## STEP 0 GATE — исполимый, не декларативный

**Прежде любой операции мандата:**

```bash
python /path/to/.github/scripts/step0_gate.py --check
```

Скрипт выводит последние 3 косяка из ЛЕТОПИСЬ. Прочитай. Не повторяй.

В CI режиме: `python step0_gate.py --ci` — auto-pass (gate logged, not blocking).

**Step 0 — теперь machine-enforced, не human-declared.** Храповик получил зубы.

---

## PROACTIVE FUZZ — hunting новых классов косяков

Храповик ловит повторы. Fuzz hunting ловит новое.

**Раз в неделю (или при новом инструменте):**

1. Запусти случайные мутации против каждого инструмента дома (lex-naturae, HUMAN-LFS, VALIDATOR, khozyain_sweep).
2. Запиши любой новый bypass как новый класс в ЛЕТОПИСЬ (класс Е).
3. Если bypass — новый класс (не повтор) → добавь тест + fix.
4. Если bypass — повтор → отметь [ПОВТОР] (сигнал: Step 0 не исполнялся).

**Не «тесты прошли» — а «тесты поймали то, для чего не были написаны.»**


---

## RVL — RECURSIVE VERIFICATION LOOP

**Эмерджентное.** Verification infrastructure files claims about itself, then validates.

```bash
python .github/scripts/recursive_verify_loop.py
```

- **PASS** → система верифицирует себя (один уровень рекурсии). Trust preserved.
- **FAIL** → система нашла свой gap. Записать в ЛЕТОПИСЬ, починить, перегнать.

**RVL — не копия мирового тренда.** LLM self-verification (NeurIPS 2026) проверяет reasoning. RVL проверяет verification rules + evidence format. Рост из нашей комбинации: КАНОН + храповик + Step 0 + fuzz + meta-audit.

Документация: [`docs/RVL-RECURSIVE-VERIFICATION-LOOP.md`](docs/RVL-RECURSIVE-VERIFICATION-LOOP.md)


---

## ATP — AGENT TRUST PASSPORT

**Каждый агент в доме имеет ATP** — portable JSON с track record. Файл: `.github/docs/AGENT-TRUST-PASSPORT-<NAME>.json`.

**Перед сотрудничеством с другим агентом — прочитай его ATP:**
- `sessions`: сколько мандатов завершено, с каким результатом
- `mistakes_recorded`: какие косяки записаны (класс Е)
- `rvl_status`: PASS/FAIL — прошёл recursive verification
- `canon_compliance`: STRUCTURE PASS + lex-naturae valid?
- `trust_score`: агрегированная оценка
- `boundaries`: что PASS не доказывает для этого агента

**После каждой сессии — обнови свой ATP:** добавь session, обнови trust_score, обнови RVL status.

Документация: [`docs/ATP-AGENT-TRUST-PASSPORT.md`](docs/ATP-AGENT-TRUST-PASSPORT.md)
Реализация: [`docs/AGENT-TRUST-PASSPORT-Z-AI.json`](docs/AGENT-TRUST-PASSPORT-Z-AI.json) (первый ATP в доме)


---

<!-- МЕМБРАНА-17 · 2026-11-18: рабочий протокол ТЕЛА сохранён ниже; домовой канон .github выше -->

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
- **Biome-исключения (T16, маркер «documentation-only»)**: блок корневых `!*.md`-строк в конце `files.includes` (biome.json) — исключение ДОКУМЕНТАЦИИ (README, AGENTS, ARCHITECTURE, CHANGELOG, CODE_OF_CONDUCT, CONTRIBUTING, PUSH, ROADMAP*, SECURITY, TZ, ТЗ), а не сгенерённых путей; сгенерённые/машинные пути (node_modules, dist, build, .turbo, .next, target, runtime, docs, vault, garden-артефакты, pnpm-lock.yaml, agent-дампы v128/v3100/v3101, PULSE.md) исключаются отдельным блоком выше и сохраняют свой маркер генерации. Проза и таблицы документации не подлежат biome-канону.
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

| Adapter         | Транспорт                              | Risk       | Offline | Source                |
| --------------- | -------------------------------------- | ---------- | ------- | --------------------- |
| LLMLocalAdapter | Offline LLM (rule-layer deterministic) | low-medium | True    | singulyar ·21 ОБЩЕНИЕ |
| HTTPAdapter     | REST request/response                  | low-medium | False   | standard REST         |
| WebRTCAdapter   | Air-gapped P2P (no STUN/TURN)          | low-medium | True    | singulyar ·17 ЗАЛ     |

Все 3 реализуют один контракт: `execute(intent, key)` + `read_state(intent, key) → Observation tri-state`.

## 9 паттернов из AUDIT_SINGULYAR (machine-checked)

| #   | Паттерн                                 | CI check                   | Status  |
| --- | --------------------------------------- | -------------------------- | ------- |
| 1   | Manifest exclusivity                    | check.py #13               | dormant |
| 2   | Counter-from-source                     | check.py #14               | dormant |
| 3   | CSP no scheme-only connect-src          | check.py #15               | dormant |
| 4   | Sovereignty drill runner exists         | check.py #16               | ACTIVE  |
| 5   | Sequential triage rule-layer-first      | check.py #17               | ACTIVE  |
| 6   | No silent SW registration failure       | check.py #18               | dormant |
| 7   | Storage eviction with protected-key Set | check.py #19               | dormant |
| 8   | Identity backup documented              | check.py #20               | dormant |
| 9   | Sovereignty drill in CI weekly          | sovereignty_drill.yml cron | ACTIVE  |

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

## Гигиена агента (Волна ×10, 2026-11-10)

Канон: repo-doctrine → `21-гигиена-уведомлений-и-красного-CI-2026-11-09.md`. Вход по закону: `github-runbook#10` (РЕЕСТР НЕДОДЕЛАННОГО · закон §5) + РЕЕСТР-КОСЯКОВ-ИИ + АНАТОМИЯ-КОСЯКОВ-ИИ (polimat-hub) — читать ДО первого действия.

1. Красный CI от твоего коммита — твой долг: живой зелёный прогон до конца сессии (rerun/диспатч/лат). Честный красный (внешний блок) — пломбой в github-runbook#10, не прятать.
2. Новые файлы — в манифесты тем же коммитом: SPDX/REUSE.toml, MANIFEST/portability.json, геном cell-swarm/swarm.json (пин следит за телом).
3. Не плодить уведомления: свой прогон доведи до зелёного; входящие треды разобрать и пометить прочитанными; UNREAD=0 — норма.
4. Пуш-гигиена: `pull --rebase` перед пушем; force-push запрещён; чужие волны и авто-коммиты (§3 реестра) не трогать; дубль снят честно = нет дубля.

## Никогда не делать (Never do)

- Never force-push в основную ветку: история роя append-only.
- Never трогать мембранные файлы (README.md, AGENTS.md, llms.txt) без пломбы в polimat-hub.
- Never коммитить секреты и токены: токен, попавший в чат, считается скомпрометированным и подлежит отзыву.

---

## Agent Execution Pack (docs/agent-execution/)

Optional operating layer for agent-assisted work, installed as a non-destructive
overlay (branch `pack/agent-execution-2026-11-10`). The instructions above keep precedence; where the
pack conflicts with repository reality, reality wins and the conflict becomes an ADR.

- Maturity labels and reading paths: `docs/README.md`, `docs/agent-execution/README.md`
- Machine-readable contracts (JSON Schema draft 2020-12): `schemas/agent-execution/`
- Governance crosswalk to 2026 world frameworks (CSA Agentic Trust, Microsoft agent
  governance, SLSA/attestations, AgentLens): `docs/agent-execution/15_GOVERNANCE_CROSSWALK_2026.md`
- Package validator (documentation-only, never executes repository code): `python3 tools/validate_pack.py`

---

<!--РЕВО:СВОД-ОФОРМЛЕНИЯ-->
## СВОД ОФОРМЛЕНИЯ РЕВО — правило всем агентам дома (v2 · АВТОПИЛОТ)

Каждая страница дома всегда оформлена, и оформление ведёт себя само:

1. **АВТОПИЛОТ (REVE=РЕВО):** `revo_autopilot.py` + workflow `revo-obhod.yml` куют
   `revo-page.svg` — РЕВО-ПАСПОРТ страницы строго по её фактическому контенту (файлы,
   папки, коммиты, лексикон README, топики, размер, SHA) — на каждый push и еженедельно
   по cron, и сами записывают изменения коммитом «автопилот РЕВО». Агент паспорт руками
   не правит: правит контент — паспорт перекуется сам.
2. **Пять вещей сразу:** `banner.png`, `repo-muse.svg`, `forge-divider.svg`, README с
   паспорт-блоком `<!--ФОРЖ:ПАСПОРТ:НАЧАЛО-->…КОНЕЦ`, описание и топики репо.
   Нашёл пустое — заполни тем же коммитом, что и дело.
3. **Дежурный обход:** `revo_obhod.py` проверяет пять вещей; при дрейфе — issue.
   Тишина = айс.
4. **Канон не переписывается:** Конституция (edinyy-svod), ворклог (H-PE11-PHOENIX) —
   только append; force-push запрещён; «сделал дело — записай»; палитру школы брать
   из её кода.
5. **РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · ЧЕЛОВЕК=АККАУНТ=PID1 · КУЗНЯ ПОЛИМАТ**
