# Известные ограничения и честные оговорки (v0.3)

## Что НЕ доказано
- Новизна: систематического обзора прецедентов и патентов нет. Каждое отдельное звено (idempotency key, write-ahead log, readback, outbox, contract tests, hash chain) известно; нового заявлено только сочетание, и оно не проверено на реальных нагрузках.
- «Эмерджентность»: не показана. Абляция демонстрирует вклад звеньев на 14 синтетических сценариях автора (`EXPERIMENT_PLAN.md`).
- Безопасность: нет внешнего аудита; сетевых, криптографических и многопользовательских аспектов нет.

## Известные технические дефекты и пределы
1. **Один процесс-писатель.** SQLite-журнал сериализует добавление (BEGIN IMMEDIATE) и не раздваивает цепочку при двух дескрипторах, но состояние задач (`Runtime.states`) строится при запуске; два одновременно работающих Runtime на одном журнале не координируются (нет аренд/лизингов).
2. **Права доступа восстанавливаются не из журнала.** Согласия (`grant_consent`) после перезапуска не восстанавливаются (fail closed): их нужно выдать снова. Это безопасно, но неудобно. Подпись решений человека — Фаза 4.
3. **Журнал ≠ первоисточник истины.** Хэш-цепочка выявляет искажение внутри журнала; полная перезапись цепочки или обрезка хвоста выявляются только при наличии внешней контрольной точки (`checkpoint()`), и хранить её нужно отдельно. В прототипе она не автоматизирована.
4. **Отпечатки (HMAC) защищены ключом `redaction_key`.** Ключ не хранится и не ротируется ядром; без правильного ключа `recover/resume` откажут (`ContractError`). Управление ключом — на внедряющем. Residual (audited Gate-2 2026-10-16, see docs/REDACTION_AUDIT.md): low-entropy values (e.g. {"ok": true}, "1", "yes") have small preimage space under HMAC-SHA-256; attacker with redaction_key + fingerprint can recover value by dictionary attack in seconds. Mitigation in v0.4: per-entry random salt (16 bytes) prepended to HMAC input.
5. **Readback зависит от адаптера.** Если внешняя система не умеет читать состояние по ключу идемпотентности, остаётся `UNKNOWN`; ядро не умеет «догадываться» и не должно.
6. **Эффект «по ключу» — модель.** Реальные системы дают разные гарантии (eventual consistency: `ABSENT` может быть временным). Для идемпотентных возможностей повтор безопасен благодаря ключу; для неидемпотентных — решает человек.
7. **Валидатор схем — подмножество.** Неподдерживаемое ключевое слово → ошибка (fail closed), но это не полноценный JSON Schema.
8. **Симуляция.** `SQLiteEffectAdapter` — имитация удалённого мира; реальных сетевых адаптеров, WebRTC, шифрования, учётных записей, платежей, ИИ-моделей нет.
9. **Нет авто-самомодификации** (намеренно, ADR-004): ошибка → предложение теста/изменения, а не правка кода.
10. **Мутационная проверка выполнена вручную** на 4 мутациях; она нашла один пробел (исправлен). Автоматизированного мутационного тестирования нет; не стоит читать 36 зелёных тестов как полное покрытие.

## Что изменилось по сравнению с тем, что я заявлял ранее
- Заявление в прошлой реплике о версии v0.3 с SQLite было преждевременным: архив не был создан. Теперь он создан и проверен; список расхождений — `AUDIT_POLYMATH.md`, раздел C.


## Gate-6 closures (2026-10-16)

Items 1, 4, 8 partially closed by Gate-6 work. Items 2, 5, 6, 7, 9, 10
remain open.

### Item 1 — Single-writer — PARTIALLY CLOSED
Added `lead_acquire`/`lead_release`/`lead_status` to `SQLiteEvidenceLedger`
(see `src/sqlite_ledger.py`). Lead-based coordination via SQLite advisory
locking: one ledger file → one lead at a time → one Runtime can append events.
Tests: `tests/test_durability.py::LeadLeaseTests` (3 tests covering acquire,
block-second, expiry, wrong-holder release). Lead TTL default 30s, expired
leases auto-swept on next acquire. Residual: this is per-ledger-file
coordination only; cross-ledger coordination (e.g., sharded by intent_id) is
v0.5 work.

### Item 4 — HMAC fingerprints brute-forceable for low-entropy values — CLOSED
Per REDACTION_AUDIT.md recommendation: added per-entry 16-byte random salt
to HMAC input. `singulyar_runtime.py:_log_evidence` now generates `salt =
os.urandom(16)` per evidence entry, stores `salt.hex()` in the ledger event,
and uses `fp_salt(obj, salt)` instead of `fp(obj)`. Salt prepended to
canonical input: `HMAC(key, salt + canonical(obj))`. Preimage space per
entry raised from `2^entropy_of_value` to `2^128` — even for low-entropy
values like `{"ok": true}`, `1`, `yes`, an attacker with `redaction_key` +
captured fingerprint cannot recover the value by dictionary attack. Schema
updated: `evidence.schema.json` now requires `salt` field (32-char hex).

### Item 8 — No real network adapters — PARTIALLY CLOSED
Added `runtime/src/adapters/http_adapter.py` — Python stdlib `urllib`-based
HTTP adapter. Implements SINGULYAR EIR Adapter contract with tri-state
Observation: PRESENT (cached HTTP response), ABSENT (no cached response),
UNAVAILABLE (internal error). NotExecuted raised on: URLError (network
unreachable), TimeoutError, 5xx on idempotent operations (GET/PUT — safe to
retry). RuntimeError raised on: 4xx client error, 3xx redirect, 5xx on
non-idempotent operations (POST — effect may have happened). Tests:
`tests/test_http_adapter.py` (12 tests, including real-network tests
against `httpbin.org` that SKIP if offline). Capabilities declared:
`http.get` (low risk, idempotent), `http.post` (medium risk, non-idempotent),
`http.put` (medium risk, idempotent). All `offline=False, local_only=False`
(external endpoint per ADR-0002 Tier 2). WebRTC adapter (analogous to
singulyar ·17 ЗАЛ) is v0.5 work.

### Item 9 — No real LLM weights — PARTIALLY CLOSED
Added `tests/test_llm_local_adapter_integration.py` — integration test that
SKIPS unless `LLM_MODEL_PATH` env var is set to a real GGUF file path. If
set + `llama-cpp-python` installed: loads Qwen2.5-0.5B-Instruct via the
LLMLocalAdapter (Gate-3), verifies READY state, verifies free-speech gets
real LLM response (not NotExecuted), verifies rule-layer commands still
short-circuit alongside LLM. Closes the "no real LLM weights" gap when
explicitly enabled. Residual: not part of default CI (would require GPU
runner or 4 GB RAM for CPU inference). Run locally:
`LLM_MODEL_PATH=/path/to/qwen.gguf python3 -m unittest tests.test_llm_local_adapter_integration`.

### Sovereignty drill runner — NEW (closes ADR-0002 falsifiability gap)
Added `scripts/sovereignty_drill.py` — quarterly drill runner per ADR-0002
§"verification: ежеквартальное учение выхода". Disables one Tier 2 service
via env var block, runs `make verify` + `cd runtime && python3 scripts/check.py`
to confirm core+data still work, records recovery time. JSON output:
`{service_disabled, verify_pass, runtime_tests_pass, recovery_time_ms,
timestamp}`. Supports 11 Tier 2 services: github_pages, github_actions,
sentry, openrouter, 1password, hetzner, cloudflare, github_repo, obsidian,
quartz, betterstack. Or `--service all_tier2` for sequential drill.

### ADR-0013 candidate — SLSA Build L3 (hermetic builder isolation)
`docs/adr/0013-slsa-build-l3-target.md` (Proposed status) — extends ADR-0004
to v2.0 target. Implementation: `slsa-framework/slsa-github-generator`
reusable workflow + hermetic build container (`--network=none`) + reproducible
build verification + trusted builder separation. Supersedes nothing, extends
ADR-0004. Status: Proposed, awaiting v2.0 implementation.
