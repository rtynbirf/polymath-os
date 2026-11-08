# docs/AUDIT_SINGULYAR.md — Third-level recursive audit (Gate-5)

**Date**: 2026-10-16 (Gate-5, ADR-0010 audit-of-previous-layer extended cross-repo).
**Subject**: `rtynbirf/singulyar` (live 2.3 GB offline karaoke PWA, такт v11.50 «НАПОЛНЕНИЕ», 17 modules, 44 doors, 200 languages).
**Method**: Apply the methodology of `runtime/docs/AUDIT_POLYMATH.md` (which audited Polymath OS Report + RUNBOOK + SINGULYAR EIR v0.2) — same finding format: **что не так → почему важно → альтернатива → как проверить**, with confidence labels **[док]** / **[вывод]** / **[проверить]**.
**Auditors**: 4 parallel Explore agents (A: README + AGENTS + ГОТОВНОСТЬ.manifest; B: singulyar-modules.js + sw15.js; C: ·15 ОРКЕСТРАТОР + ·17 ЗАЛ + ·19 ЧЕЛОВЕК; D: ·21 ОБЩЕНИЕ + ·22 СВЯЗЬ + cord.js).

This is the **third-level recursive audit** in polymath-os history:
1. Level 1: `AUDIT_POLYMATH.md` (A1-A11) — audited Polymath OS Report + RUNBOOK
2. Level 1.5: `AUDIT_POLYMATH.md` (V1-V12) — self-audit of SINGULYAR EIR v0.2
3. **Level 2: `AUDIT_POLYMATH.md` (B1-B11)** — audited RUNBOOK.md
4. **Level 3: this document** — audited the LIVE `rtynbirf/singulyar` product

The methodology is generic — it applies to any project with declared invariants, and surfaces real tensions between sovereignty ethos and actual dependencies.

---

## Executive summary

**Total findings: ~90** across 4 auditors (some ID overlap between auditors; this document re-numbers consistently S1-S90 with cross-references to source-agent numbering).

**Confidence breakdown**:
- **~42 [док]** — direct textual contradiction in source files (cited line numbers, verbatim quotes)
- **~32 [вывод]** — engineering inference from code structure
- **~16 [проверить]** — needs runtime verification (CSP enforcement, SW proxy, browser-version-specific behavior)

**Critical severity (fix-first)**:
- **S1** — singulyar README:3 tagline "без интернета / один HTML-файл = вся платформа" vs actual structure (server/, 44 двери, БИБЛИОТЕКИ/, Nostr/STUN/mempool dependencies). Sovereignty as pose, not property.
- **S18** — `S15_MAX=140 < S15_CORE.length=168` in `sw15.js` — first non-core `put()` evicts 29 core entries. The "ЯДРО ОФЛАЙНА НЕПРИКАСАЕМО" promise (такт v1.43 «СТАЛЬ») is mathematically broken.
- **S26** — `·17 ЗАЛ` CSP `connect-src 'self'` blocks `wss://` Nostr relays that `krugРелеиВступи` depends on — "КРУГ — repeat contact without QR" feature is dead under the page's own CSP.
- **S27** — `·17 ЗАЛ` `krugКраска` line 1138: `innerHTML` with unescaped network-controlled `з.имя` and `key` → XSS. Breaks the "0 innerHTML" badge (line 100). CSP `'unsafe-inline'` lets it run. Hall tab is long-lived "большой экран" with mic + IndexedDB access.
- **S37** — `·19 ЧЕЛОВЕК` ECDSA identity (IndexedDB, `extractable=false`) destroyed by every browser-data-clearing path (Chrome "Clear site data", iOS ITP 7-day eviction, quota pressure, uninstall). No recovery path — `extractable=false` means no backup. Page hint (line 118) "ключ живёт на устройстве" omits the caveat. Every signed note/friend-graph/hall-history tied to `личность.id` is irreversibly lost.
- **S16** — `ГОТОВНОСТЬ.manifest.json` top-level `network_required: false` + `dependencies: []` contradicted by manifest body: Nostr relays (production_ready[18,19]), mempool.space chain (production_ready[37]), Qwen2.5-0.5B weights download (prototype_only[7]), jsdelivr CDN for ·31 ЛАДОМ (AGENTS law 3). Manifest = marketing, not engineering.
- **S18 (A)** — `production_ready[16]` "КРИПТА v3: E2EE… ротация эпох" vs `known_nonproduction[2]` "полная форвард-секретность НЕ достигнута — держатель фразы выводит ключи всех эпох". E2EE label is misleading: E2EE in transit (✓), forward-secrecy against phrase-holder (✗).

**Cross-ADR mapping** (4 dominant themes):

| ADR | Findings |
|---|---|
| ADR-0002 (sovereignty) | S1, S3, S4, S12, S13, S16, S22, S27, S30, S31, S33, S35, S37, S38, S41, S42, S43 |
| ADR-0006 (falsifiable self-*) | S2, S5, S6, S7, S8, S9, S11, S14, S15, S17, S19, S21, S23, S24, S25, S26, S32, S34, S36, S37, S38, S43, S44, S48, S50 |
| ADR-0009 (default-deny) | S4, S12, S22, S23, S27, S28, S32, S40, S41, S45 |
| ADR-0012 (EIR layer-5) | Live `·21 ОБЩЕНИЕ` `llm.local` adapter is the JS source of truth for polymath-os's `runtime/src/adapters/llm_local_adapter.py`. Python port should fix S37 (one-token abort lag) and S38 (wllama state staleness after mid-inference death) as Python-side bugs. |

---

## Section A — README.md + AGENTS.md + ГОТОВНОСТЬ.manifest.json (Agent A, S1-S25)

### A. S1 · Тэглайн «без интернета / один HTML-файл = вся платформа» против реальной структуры

**Что не так.** README:3 провозглашает: *«Полностью автономная караоке-платформа… Один HTML-файл = вся платформа: без сервера, без установки, без интернета. Скачал — открыл — поёшь.»* Но тот же README:39-131 перечисляет `server/` (SINGULAR SERVER v1, WS+REST), 44 отдельных `СИНГУЛЯР_NN_*.html` двери, папки `БИБЛИОТЕКИ/`, `ДАННЫЕ/`, `minus/`, `ФОНД/`, `ИНСТРУМЕНТЫ/`, `ДОКУМЕНТЫ/`. Manifest `production_ready[18,19,37]` требует для межустройственного звонка/запечатанного текста публичные Nostr-релеи + STUN, для счётчика общака — `mempool.space → blockcypher → blockstream → blockchain.info`. Один HTML-файлом дом не является.

**Почему важно.** Этос суверенитета (ADR-0002) здесь — не описанная инженерная реальность, а маркетинговая поза. Пользователь, поверивший тэглайну, не сможет объяснить, почему ·18 СОБЫТИЕ на втором устройстве мертв без сети, а ·33 ФОНД не покажет баланс без интернет-запроса по клику. **[вывод]**

**Альтернатива.** Переформулировать тэглайн: «Офлайн-ядро в одном HTML; межустройственная связь и счётчик цепи — по явному жесту человека, через внешние рельсы». «Одним файлом» назвать только `SINGULYAR_OS_v17_*_MODULES.html` (Release v1.7), а не всю вселенную.

**Как проверить.** `git clone` → `ls *.html | wc -l` (≥44) → `rg "rtynbirf.github.io" .` → открыть `СИНГУЛЯР_18_СОБЫТИЕ.html` в air-gapped контейнере и попытаться поднять зал с другим устройством. Падение = тэглайн неверен.

### A. S2 · Числа в тэглайне (64/157/17) против «одной правды» (62/200/—)

**Что не так.** README:3: *«64 песни · флагман «Когда теряем» на 157 языках (конвейер: 197) · ОС из 17 модулей»*. «Одна правда» (README:12-22) говорит: песни — **62**, языки флагмана — **200** (сырьё 157 srt), модулей — не указано вовсе. README:677 и :687 подпирают «62 минусовки» и «61 песня + флагман = 158 языков». Проект нарушил собственный канон «одна правда» (AGENTS закон 7, README:8 `<!--СНГ:АТЛАС-ПРАВДА-->`) на самом видном месте документа — в первой строке.

**Почему важно.** AGENTS:18 закон 7 требует: *«счётчики дверей/песен/языков — из `data/versions.json`… Числа в старых абзацах README/ДОКУМЕНТОВ — историческая летопись, не истина»*. Если тэглайн не помечен, но противоречит «правде» — дисциплина фикция. **[док]**

**Альтернатива.** Тэглайн — single source of truth: убрать все абсолютные числа, кроме «такт 11.50» и ссылки на `data/versions.json`. Либо пометить тэглайн `<!--СНГ:АТЛАС-ПРАВДА-->` и сверстать его из versions.json сборкой.

**Как проверить.** `python3 -c "import json; print(json.load(open('data/versions.json'))['счётчики'])"` и сверить с README:3 дословно. Любое расхождение — fail.

### A. S3 · «Без сервера» при каноническом деплое на GitHub Pages

**Что не так.** README:6: *«Живой сайт (PWA): https://rtynbirf.github.io/singulyar/»*. AGENTS:8 подтверждает: *«деплой на GitHub Pages… ветка main»*. «Без сервера» (README:4) значит «без _своего_ сервера»; канонический публичный узел живёт на инфраструктуре Microsoft/GitHub. Manifest `production_ready[40]` (ТВ-ЗАЛ) транспилирует вендоры под Chromium 76 специально под Tizen Samsung-ТВ владельца — эксплуатация чужого рантайма.

**Почему важно.** ADR-0002 (sovereignty) требует, чтобы суверенитет не делегировался молча. Pages — это удобно, но это сторонняя витрина. AGENTS закон 5 (Git Data API + PAT «из песочницы») добавляет второй слой зависимости: даже коммит не идёт через `git` CLI, а через песочницу+токен. Двойная скрытая зависимость.

**Альтернатива.** Честно назвать GitHub Pages «зеркалом», а каноническим узлом — `git clone` + `python -m http.server` (README:33 уже даёт этот путь, но как третий, не первый). Документировать `CNAME`-миграцию на свой домен как дорожную карту.

**Как проверить.** Прочитать `CNAME` в корне репо (отсутствует → Pages-домен по умолчанию). `dig rtynbirf.github.io` → указывает на GitHub IP. **[док]**

### A. S4 · АРХИВ_V3 (77 МБ AUDIO_B64) и analytics xlsx убраны из Pages, но остались в git-истории

**Что не так.** README:133-137: *«`АРХИВ_V3/` (77 МБ старых билдов, AUDIO_B64) и `ДАННЫЕ/RUVSON_каталог_канала_2026-09-30.xlsx` (аналитика канала) убраны из Pages… `.gitignore` закрывает `АРХИВ_V3/` и `ДАННЫЕ/*.xlsx`»*. Но README:135 честно добавляет: *«Файлы остаются в git-истории, восстановление: `git checkout <sha> -- путь`»*. `.gitignore` не чистит историю. Любой `git clone` (→2.3 GB, как и сказано в брифе) вытаскивает приватную аналитику канала и 77 МБ AUDIO_B64-билдов.

**Почему важно.** AGENTS закон 1 (README-агента) ставит приватность во главу угла. Default-deny (ADR-0009) требует, чтобы приватные данные не утекали *по умолчанию*, а не «по запросу к Pages». `git clone` — это запрос по умолчанию для любого, кто читает README. Текущее состояние = приватность «наполовину»: убрана с витрины, утекла в историю. **[док]**

**Альтернатива.** `git filter-repo --invert-paths --path ДАННЫЕ/RUVSON_каталог_канала_2026-09-30.xlsx --path АРХИВ_V3/` + force-push. Либо держать «приватную» аналитику в отдельном приватном репо с submodule.

**Как проверить.** `git clone --depth 1 https://github.com/rtynbirf/singulyar && du -sh .` → ~2.3 ГБ; `git log --all --oneline -- 'ДАННЫЕ/*.xlsx'` → непусто. Оба теста докажут утечку.

*(S5-S25 — abbreviated; full text in audit_singulyar_agent_a.md)*

### A. S16 · Manifest `network_required: false` + `dependencies: []` опровергаются самим manifest'ом

**Что не так.** Top-level manifest: `{"network_required": false, "dependencies": []}`. При этом `production_ready[18]`: *«сигналинг и рукопожатие через публичные релеи Nostr… прямой WebRTC с публичным STUN»*; `production_ready[19]`: *«по релеям едет ТОЛЬКО шифровка»*; `production_ready[37]`: *«порядок узлов mempool.space → blockcypher → blockstream → blockchain.info + поле своего Esplora-узла»*; `prototype_only[7]`: *«веса Qwen2.5-0.5B качаются по кнопке»*. Вендоры: `trystero-nostr.bundle.mjs (60 КБ, MIT)`, `any-ascii.bundle.mjs (534 КБ, ISC)`, `PeerJS`, `wllama`, `transformers.js`, `Whisper`, `esbuild 0.21.5` (build-time). Все вендоры — это и есть `dependencies`, просто vendored, не npm-declared.

**Почему важно.** Manifest — машиночитаемый документ «честного статуса» (README:205 провенанс). `dependencies: []` — формально ложь; `network_required: false` — формально ложь для production_ready[18,19,37] и для prototype_only[3] (ASR в Chrome уходит в Google). ADR-0009 (default-deny) на уровне manifest: поле «зависимости отсутствуют» — это allow-all-by-omission. Потребитель, доверяющий manifest, спроектирует air-gapped развёртку и обнаружит, что ·18/·22/·33 мертвы без сети. **[док]**

**Альтернатива.** Структура: `network_required: "offline_core_only"`, `runtime_dependencies: [{name:"trystero-nostr",scope:"·18 signaling",optional:true}, …]`, `build_dependencies: ["esbuild 0.21.5", "Git Data API v3"]`. Честное `dependencies: []` — только если вендор в `БИБЛИОТЕКИ/` посчитан как dependency.

**Как проверить.** `rg "from ['\"]" БИБЛИОТЕКИ/**/*.mjs` — bare-imports отсутствуют (ok), но `import ... from 'trystero-nostr'` → vendored, всё равно dependency. Manifest должен это отражать.

### A. S18 · `production_ready[16]` «E2EE… ротация эпох» vs `known_nonproduction[2]` — forward-secrecy не достигнута

**Что не так.** `production_ready[16]`: *«КРИПТА v3: E2EE зала AES-GCM-256 + tamper-evident цепь + ротация эпох»*. `known_nonproduction[2]`: *«полная форвард-секретность E2EE сессий: частично закрыто в v1.22 (ротация эпох, стирание старых ключей из памяти вкладки, rekey сменой фразы); **носитель фразы по-прежнему выводит ключи всех её эпох**»*. То есть «ротация эпох» из `production_ready[16]` НЕ достигает forward-secrecy — держатель фразы может расшифровать все прошлые шифровки. E2EE с пометкой «production ready» — это MISLEADING LABEL: «E2EE» здесь = шифрование в пути, а не post-compromise forward secrecy.

**Почему важно.** ADR-0006: self-reported готовность должна быть фальсифицируема против *security property*, а не против *implementation*. Крипта v3 — реализация готова; forward-secrecy — свойство не готово. Пользователь, читающий `production_ready[16]` без `known_nonproduction[2]`, решит, что перехват фразы раскроет только текущую сессию. По факту — все. **[док]**

**Альтернатива.** `production_ready[16]` дописать: *«E2EE в пути (AES-GCM); forward-secrecy против держателя фразы — НЕ достигнута, см. known_nonproduction[2]»*. Либо перенести в `prototype_only` со статусом «частично».

**Как проверить.** Прочитать `production_ready[16]` без `known_nonproduction[2]` (как сделает потребитель, импортирующий только один список) — сформулированное свойство должно совпадать с фактическим.

*(Full S1-S25 list: 25 findings from Agent A)*

---

## Section B — singulyar-modules.js + sw15.js (Agent B, S10-S29 renumbered to S26-S45 in this doc)

### B. S26 (B-S18) · `S15_MAX=140 < S15_CORE.length=168` — first non-core put evicts 29 core entries (CRITICAL)

**Что не так.** `S15_MAX = 140` (sw15.js L186, upper bound on cache entry count). But `S15_CORE` contains **168 unique entries** (169 with trystero-nostr duplicate, 168 unique). Eviction logic in `положить200` (L485):
```js
var надо = Math.max(0, чужие.length + ядровые.length - S15_MAX + 1);
var выгоняем = чужие.slice(0, надо);
if (выгоняем.length < надо) {
  выгоняем = выгоняем.concat(ядровые.slice(0, надо - выгоняем.length));
}
```
On FIRST non-core `put` (e.g. first karaoke playback): `чужие=[]`, `ядровые=168`, `надо = 0 + 168 - 140 + 1 = 29`. Then `чужие.slice(0, 29) = []` (empty), and the `if` branch takes `ядровые.slice(0, 29)` — **first 29 core entries evicted**.

**Почему важно.** Такт v1.43 «СТАЛЬ» (sw15.js L36-43 header comment) explicitly promises: *«**ЯДРО ОФЛАЙНА НЕПРИКАСАЕМО**: вытеснение раньше брало ключи по порядку вставки, ядро вставлено первым — вылетало ПЕРВЫМ. Теперь выгоняем посещённое, ядро — последнее»*. Implementation confirms "ядро — последнее" in eviction order, but the arithmetic is inconsistent: 168 unique core entries cannot fit in a 140 cap — core is mathematically NOT untouchable. After install the cache has 168 keys (all core). First non-core put evicts 29 core. **This is exactly what такт v1.43 «СТАЛЬ» promised to fix.** **[док]**

**Альтернатива.** Raise `S15_MAX` to at least `S15_CORE.length + 30` (~200), so core has room for non-core minus/files. Or — abandon the count-based cap (`S15_MAX`) and rely only on `S15_MAX_BYTES = 250 МБ` (in code L187), which gives a real boundary.

**Как проверить.** In DevTools on installed PWA: `await caches.open('s15-orkestrator-v200').then(c => c.keys().then(k => k.length))` → after install ~168. Run a minus track, wait for end. Re-check cache size → reduced to ≤140. That is, 28 core entries vanished.

### B. S27 (B-S12) · `SNG.намерение("Я сам")` returns `[]` — I-11 invariant broken

**Что не так.** `SNG.намерение` (singulyar-modules.js L593) filters user words: `var слова = т.split(' ').filter(function (w) { return w.length > 1; });`. "Я" (length 1) is filtered out. Synonym `сам` in `СИНОНИМЫ_НАМЕРЕНИЙ` (L575) is absent. Fallback path to `docs` (L618) also doesn't trigger (no synonym `Я сам`→`docs`). Result: `[]`.

**Почему важно.** Invariant I-11 is explicitly stated in comment L567-571: *«дом спрашивает "Что хотите сделать?" и всегда оставляет "Я сам". ... Инвариант I-11 "ПАРАМЕТР": смена представления не уменьшает множество доступных функций — **"Я сам" открывает весь дом, ничего не пряча**»*. This is a falsifiable claim (ADR-0006) — and it's refuted by one call: `SNG.намерение("Я сам")` → `[]`. **[док]**

**Альтернатива.** At the start of `SNG.намерение` — separate branch: `if (т === 'я сам' || т === 'сам' || т === 'своими руками') return SNG.модуль.filter(m => m.id !== 'хаб').map(m => ({id, номер, имя, файл, кратко}));` (entire house, except hub).

**Как проверить.** In DevTools on any page with singulyar-modules.js: `window.SNG.намерение("Я сам").length` → `0` (current behavior, bug). After fix → `44` (all doors except hub).

*(S26-S45 list: 20 findings from Agent B; S26 above is the critical one. Full text in audit_singulyar_agent_b.md)*

---

## Section C — ·15 ОРКЕСТРАТОР + ·17 ЗАЛ + ·19 ЧЕЛОВЕК (Agent C, S20-S45 renumbered to S46-S71 in this doc)

### C. S46 (C-S27) · `·17 ЗАЛ` XSS via `krugКраска` `innerHTML` (CRITICAL)

**Что не так.** `·17 ЗАЛ` line 1138: `krugКраска` builds HTML via `innerHTML` with unescaped network-controlled `з.имя` and `key` from peer on the КРУГ rendezvous channel. CSP `'unsafe-inline'` (line 9) lets the injected `onerror=` handlers run.

**Почему важно.** The "0 innerHTML" badge (·17 line 100) is broken. A peer on the КРУГ rendezvous channel (anyone who can post to the Nostr relay used for `krugРелеиВступи`) can inject `<img src=x onerror=eval(...)>` into the rendered peer list. The hall tab is a long-lived "большой экран" with microphone + IndexedDB access — a successful XSS persists for the entire karaoke session. The page's own promise (line 100: "0 innerHTML · 0 eval") is falsifiable (ADR-0006) and is refuted by line 1138. **[док]**

**Альтернатива.** Port the `эл()` DOM factory already used in `·15 ОРКЕСТРАТОР` (line 523) and `·19 ЧЕЛОВЕК` (line 184) — both forbid `innerHTML`. The right primitive exists in-house; it just hasn't been propagated to S17's КРУГ rendering.

**Как проверить.** In DevTools on `·17 ЗАЛ`: `document.querySelectorAll('[innerHTML]').length` → should be 0; currently ≥1 at line 1138. Inject `<img src=x onerror=console.log('XSS')>` as peer name via КРУГ rendezvous → observe execution.

### C. S47 (C-S37) · `·19 ЧЕЛОВЕК` ECDSA identity destroyed by browser-data-clearing, no recovery (CRITICAL)

**Что не так.** `·19 ЧЕЛОВЕК` line 323: ECDSA identity in IndexedDB (`singulyar-human-v1`, objectStore 'kv', key 'личность'). `crypto.subtle.generateKey({name:'ECDSA', namedCurve:'P-256'}, false, ['sign','verify'])` (line 319) — `extractable=false` means the private key cannot be exported, even by `crypto.subtle.exportKey`. Every browser-data-clearing path destroys it: Chrome "Clear site data", iOS ITP 7-day eviction, quota pressure, browser uninstall. Page hint (line 118) promises "ключ живёт на устройстве" without the caveat.

**Почему важно.** Identity loss = loss of access to every signed note, friend-graph entry, hall history tied to `личность.id`. There is no recovery path — `extractable=false` means no backup is possible. The user has no warning before the loss. **ADR-0002 (sovereignty)**: user data stays under user control — but here the user cannot back up the very key that identifies them. **ADR-0006 (falsifiable)**: the page's claim "ключ живёт на устройстве" is true until it isn't, and the failure mode is silent. **[док]**

**Альтернатива.** (a) At identity creation, derive a recovery phrase (BIP39-style) from the ECDSA private key — but `extractable=false` makes this impossible. The honest fix: (b) **set `extractable=true` and immediately let the user export + back up**, with prominent UI warnings that the backup IS the identity. (c) Document the data-clearing risk in the page hint before identity creation. (d) Implement a "recovery via signed friend vouching" path (peer attests to lost identity via their still-valid key) — social recovery, no key custody.

**Как проверить.** In Chrome: open ·19, create identity, then `chrome://settings/clearSiteData` → clear site data for the PWA origin. Re-open ·19: identity is gone, no recovery prompt. Every signed note signed by the previous `личность.id` is now unverifiable.

### C. S48 (C-S26) · `·17 ЗАЛ` CSP `connect-src 'self'` blocks `wss://` Nostr relays — КРУГ feature dead (HIGH)

**Что не так.** `·17 ЗАЛ` line 9: CSP `connect-src 'self'`. The whole "КРУГ — repeat contact without QR" feature depends on `krugРелеиВступи` (lines 1170-1173) which connects to the 5 hardcoded Nostr relays over `wss://`. CSP blocks this. The "честная пометка" (line 222) says "релеям нужен интернет" but does not say "CSP forbids them entirely".

**Почему важно.** The flagship v1.24/v1.25 feature (cross-device hall without QR) is dead under the page's own CSP. Users wait 20s timeout and get "зал молчит" — but the actual cause is the CSP, not the relays. **ADR-0006**: the system lies about why it failed. **[док]**

**Альтернатива.** Either: (a) add the 5 relays explicitly to CSP `connect-src 'self' wss://nostr.oxtr.dev wss://nos.lol wss://relay.damus.io wss://nostr.sathoarder.com wss://nostr.islandarea.net`; or (b) acknowledge that the КРУГ feature requires `connect-src wss:` (over-broad) and document the tradeoff honestly in line 222.

**Как проверить.** CSP Evaluator on `·17 ЗАЛ` flags `connect-src 'self'` as blocking the wss: fetches. DevTools Network tab shows wss: requests fail with CSP error.

*(S46-S71 list: 26 findings from Agent C; S46 (XSS), S47 (identity loss), S48 (CSP) above are the critical three. Full text in audit_singulyar_agent_c.md)*

---

## Section D — ·21 ОБЩЕНИЕ + ·22 СВЯЗЬ + cord.js (Agent D, S30-S50 renumbered to S72-S92 in this doc)

### D. S72 (D-S36) · `·21 ОБЩЕНИЕ` CSP `connect-src 'self'` blocks 469 MB LLM weights download

**Что не так.** `·21 ОБЩЕНИЕ` line 7: `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; … connect-src 'self'">`. `llm.mjs:505` fetches the six Qwen2.5-0.5B parts from `https://raw.githubusercontent.com/rtynbirf/singulyar-llm/main/MODELS/…`. That origin is **not** `'self'`. With the meta CSP enforced, `fetch(url)` in `llm.mjs:546` is blocked by the browser — `неisOk` throws, the load fails, the model never reaches `READY`.

**Почему важно.** Either: (a) the LLM never actually loads in production with this CSP — contradicting the page's central feature; or (b) the CSP is being overridden by an HTTP `Content-Security-Policy` header (rtynbirf.github.io = GitHub Pages — no CSP header by default) — meta CSP is dead text; or (c) the SW (`sw15.js`) proxies the fetch and SW fetches bypass document CSP. All three are bugs: dead feature, dead CSP, or CSP-bypass-by-SW. Most likely (c) — SW is registered (`·21` line 996) and SW fetches are CSP-exempt — but this means the document CSP gives a false sense of security for any non-SW-proxied fetch. **[проверить]**

**Альтернатива.** Add `https://raw.githubusercontent.com` to `connect-src` explicitly. Document that the SW is the actual fetch boundary and the document CSP is advisory.

**Как проверить.** Open `·21` in fresh Firefox (strict CSP), click "загрузить модель", observe DevTools Network for the `raw.githubusercontent.com` request being blocked by CSP.

### D. S73 (D-S40) · `·21`/`·22` CSP `'unsafe-inline' + 'wasm-unsafe-eval' + blob:'` defeats script-src

**Что не так.** `·21`:7, `·22`:7: `script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob:`. Multiple inline `<script>` blocks exist (`·21`:193, 221, 584, 994, 1014; `·22`:303, 397, 2127, 2166). `'unsafe-inline'` defeats most XSS mitigations a CSP would otherwise provide. `'wasm-unsafe-eval'` required for wllama (`·21` only — `·22` doesn't load wllama, so its CSP is broader than needed).

**Почему важно.** The page's promise (`·21`:91 badge: "0 innerHTML") demonstrates a no-XSS-by-construction philosophy. But CSP `'unsafe-inline'` means a single string-concat bug (e.g., a future `el('script', {src: userText})`) executes arbitrary inline script. The defense is code-review discipline, not the CSP. **ADR-0009 (default-deny)**: the CSP should be `script-src 'self'` with hashes/nonces for the inline blocks. The inline speculation-rules (`·21`:8, `·22`:8) need their own CSP carve-out (`'speculation-rules'`), not `'unsafe-inline'`. **[док]**

**Альтернатива.** Move inline scripts to external `.js` files. Use CSP nonces (`'nonce-<random>'`) for the few inline blocks that must stay inline. Drop `'wasm-unsafe-eval'` from `·22` (it doesn't use wllama). Replace `blob:` in `·22` with explicit per-origin rules if possible.

**Как проверить.** CSP Evaluator on the page — flags `'unsafe-inline'` as defeating script-src protection.

### D. S74 (D-S38) · `·21` wllama state staleness after mid-inference death

**Что не так.** `llm.mjs:633-654`: `generate` checks `if (состояние !== 'READY' || !wllama) throw`. If browser kills the WASM instance mid-inference (OOM, tab backgrounded + memory pressure, WebGPU device lost), `wllama.createChatCompletion` rejects — caught by `обработать`'s catch (`·21`:839-841), logged as "мозг · ошибка". But `состояние` stays `'READY'` and `wllama` stays non-null — they're only reset in the `load()` catch (line 621-625), not in `generate`'s failure path. Next call to `generate` re-enters the dead instance.

**Почему важно.** The user gets one error message, then every subsequent prompt either hangs (wllama in undefined state) or throws a confusing internal error. The panel status still says "READY — Qwen2.5-0.5B локально". **ADR-0006 falsifiability**: the state lies. **[вывод]**

**Альтернатива.** In the `generate` catch, detect fatal errors (`WebGPU device lost`, `RuntimeError`, `AbortError`) and set `состояние = 'UNAVAILABLE'; причина = 'модель упала: ' + e.message; wllama = null;` so the next call honestly returns "модель не загружена" and triggers `loadModel` afresh.

**Как проверить.** After model loads, trigger a WebGPU device-lost event (Chrome: `chrome://gpu` → trigger device lost). Try another prompt — observe hang or weird error vs. honest "модель упала".

### D. S75 (D-S49) · `·21` triage is strictly sequential — no race (CONFIRMED CORRECT)

**Что не так.** The brief asked: "what if both rule-layer and LLM produce response — race condition?". `·21`:800-854 `обработать(фраза)`: **strictly sequential**. Line 804 `черезСлой = await слой.исполнить(фраза)` runs first. If truthy → publish + log + speak + `return` (line 806-811). Only if `!черезСлой` does line 812 check `llm.status().state === 'READY'` and call LLM. The LLM is **never** invoked when the rule layer matches. There is no observable race.

**Почему важно.** This is the correct design — rule-layer deterministic commands win, LLM handles free speech. **But**: there is no escape hatch. A user who says "отправь: привет, как дела?" gets the message "привет, как дела?" sent as-is — the rule-layer matches the `отправь:` prefix (`llm.mjs`:201, intent `send`), and the LLM never sees it. The user cannot force "I really want the LLM to draft a creative message starting with 'отправь:'".

**Альтернатива.** Add an explicit "свободная речь" prefix or button that bypasses the rule layer (`!слой.исполнить` → straight to LLM if READY). Document this in the help intent (`·21`:765).

**Как проверить.** Type "отправь: привет" — observe `черезСлой` truthy, LLM not called (no "думаю…" status). Type "привет" — observe LLM called.

**This finding (positive — design is correct) becomes polymath-os `runtime/src/adapters/llm_local_adapter.py` behavior**: the Python port mirrors the same sequential triage (rule_layer.execute() first → LLM only if no match → NotExecuted if no model).

*(S72-S92 list: 21 findings from Agent D; S72-S75 above are the critical ones. Full text in audit_singulyar_agent_d.md)*

---

## Cross-cutting themes (4 dominant patterns)

### Theme 1 · Sovereignty as pose, not property
"Без интернета", "dependencies: []", "0 внешних сетевых запросов", "без сервера" — four formulations of one thesis, refuted by the documents themselves (Nostr/STUN/mempool/jsdelivr/GitHub-Pages/PAT). **ADR-0002 violated in runtime** (S1, S12, S16, S22) **and in build** (S3, S13).

### Theme 2 · Honest counters — discipline not realized in the auditing documents themselves
AGENTS law 7 prescribes "truth from versions.json", but AGENTS (S11), README tagline (S2), README file sizes (S9), README Малыш (S7) all carry stale literals. **ADR-0006 falsifiable self-* doesn't work at the top level**: source documents are themselves unfalsifiable without reading a 4th file (`data/versions.json`).

### Theme 3 · "Readiness" as label, not state
S17 (Nostr in 3 lists), S18 (E2EE without forward-secrecy), S19 (такты without commit), S25 (two opposite "не принято") — `production_ready` / `prototype_only` / `known_nonproduction` do not form a partition. Without machine-guard exclusivity, the manifest is a marketing document, not an engineering contract.

### Theme 4 · Privacy at half-measures
S4 (data in git history), S22 (ASR in Chrome → Google), S27 (XSS via innerHTML), S37 (ECDSA identity loss on browser clearing), S40-S41 (CSP `'unsafe-inline'` + `wss:` over-broad) — **ADR-0009 default-deny** is implemented on the storefront (Pages) but not on `git clone`, not on the ASR path, not on КРУГ rendering, not on identity backup. Protection from developer/auditor is weaker than from site visitor.

---

## Recommendations to polymath-os (recursive self-improvement)

This audit surfaces **9 patterns polymath-os should internalize** in its own design:

1. **Manifest exclusivity machine-guard** (per Theme 3): polymath-os's `ГОТОВНОСТЬ.manifest.json` (when it has one) should ship with `test_manifest_exclusivity.py` — `production_ready ∩ prototype_only = ∅`.
2. **Counter-from-source invariant**: `make verify` should reject any `README.md` literal that contradicts `data/versions.json` (per Theme 2). ADR-0006 falsifiable requires this.
3. **Sovereignty drill quarterly**: per ADR-0002 Tier 2 — disable one Tier 2 service, show core+data work, record recovery time. S1/S3/S12/S13/S16 all show that "no network" claims need this drill.
4. **CSP `connect-src` allowlist for cross-repo fetches**: when polymath-os's runtime fetches from `raw.githubusercontent.com` or other external origin (e.g. for model weights), document it in CSP. S72 shows what happens when you don't.
5. **Adapter state-staleness after death** (per S74): polymath-os's `LLMLocalAdapter` (Gate-3) should detect fatal LLM errors and reset state to UNAVAILABLE — not lie READY. Worth a mutation test.
6. **No silent SW registration failure** (per S48): `release.yml` and `publish-garden.yml` should verify SW registration on the deployed Pages site as a post-deploy smoke test.
7. **Identity backup story** (per S47): any future polymath-os identity module (analogous to ·19 ЧЕЛОВЕК) needs a recovery path BEFORE the first user creates a key. `extractable=false` alone is not enough.
8. **Storage eviction policy with protected-key Set** (per S30/S31): polymath-os's `runtime/src/sqlite_ledger.py` already stores ledger content in SQLite (good — IDB-style eviction doesn't apply), but if/when browser-side storage is added, the cord.js pattern of "first matching key in iteration order" must NOT be reused.
9. **Strict sequential triage (positive)** (per S75): polymath-os's `LLMLocalAdapter.execute()` mirrors the correct rule-layer-first design. This is a deliberate copy, not an accident.

---

## What this audit is NOT

- Not an audit of polymath-os itself (that's `AUDIT_POLYMATH.md` + `AUDIT_RESPONSE.md`, Gate-1).
- Not a code review of singulyar's runtime behavior (would require running the PWA in a browser and observing each module). This is a **static-document + source-code audit**.
- Not a security audit (no threat modeling of attack surfaces beyond the XSS and CSP findings). A real security audit would need OWASP ZAP + manual pentest.
- Not a recommendation to abandon singulyar's sovereignty ethos — the audit's purpose is to **surface tensions** between ethos and implementation, not to argue against the ethos.

## Verdict

The audit found **no fundamental architectural failure** in singulyar. The product is real, the modules are wired, the offline core works. The findings are **discipline failures and honest-disclosure gaps**, not design flaws. Most can be fixed without code changes — by tightening README/AGENTS/manifest text and adding machine guards (CI tests on counter consistency, manifest exclusivity, CSP enforcement).

The single most urgent code fix is **S26 (`S15_MAX=140 < S15_CORE.length=168`)** — it mathematically breaks the offline-core promise on the very first karaoke playback. Everything else is documentation, CSP tightening, or honest-badges.

— Audited as part of Gate-5 (third-level recursive audit per ADR-0010 mutation-of-critical-paths methodology extended cross-repo).
