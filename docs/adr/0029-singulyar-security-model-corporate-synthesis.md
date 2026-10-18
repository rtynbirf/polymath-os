# ADR-0029 — СИНГУЛЯР Security Model: Global Best Practices Synthesis

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** security, zero-trust, synthesis, v3.16.0
**Deciders:** @USER (Командир корабля)

## Context

Tech-корпорации (Oracle, Kaspersky, Google, Amazon, Microsoft) — это
**мелочь пузатая** по сравнению с реальными крупными структурами:
финансовые системы, разведывательные агентства, военные структуры,
ядерные объекты, правительства.

Каждая структура — от банка до ядерной станции — решает СВОЮ проблему
безопасности ЛОКАЛЬНО. Их практики — лучшие в мире.

Принцип СИНГУЛЯР: 1+1+1+...+1 = 1 ЧЕЛОВЕК.

Берём лучшее от каждой корпорации, перецентрируем на Человека,
синтезируем в уникальное эмержентное сингулярное.

## Decision

Synthesize the best security practice from each corporation, reorient from corporation-centric to human-centric. The Decision IS the synthesis below — each corporation's best practice mapped to an existing СИНГУЛЯР feature.

### Oracle — Zero Trust Packet Routing (ZPR)

**Что делает Oracle:** Security at the PACKET level. Каждый пакет
проверяется — не только на сетевом уровне, но и на уровне ресурсов
(security namespaces + attributes). "Never trust, always verify"
в наименьшей гранулярности.

**Лучшее:** Zero Trust на наименьшем уровне (packet → intent).

**СИНГУЛЯР mapping:** Decree gate проверяет КАЖДЫЙ Intent
(не просто сетевой запрос, а само намерение). Granularity = Intent,
не packet. Runtime._advance() → check_compliance() BEFORE policy.
A2AClient проверяет BEFORE network request. AgentMeshServer проверяет
на HTTP уровне. 4 направления проверки.

### Kaspersky — Threat Intelligence

**Что делает Kaspersky:** Proactive threat detection. Не реактивная
защита (после атаки), а проактивная — "stay ahead of complex threats".
Clear, actionable intelligence. Regular updates to threat evaluation.
Log collection necessary but NOT sufficient — нужен анализ.

**Лучшее:** Proactive threat intelligence — опережать угрозы.

**СИНГУЛЯР mapping:** DecreeLog = threat intelligence database.
Каждый prohibition decree = threat pattern. check_compliance() =
proactive scan (проверяет BEFORE выполнения, не после).
v0.6.1 regex extension (send/share/transmit/expose) = data-flow
threat patterns. supersession (ADR-0028) = threat intelligence
updates (когда угроза устарела — отзывается декрет).
Evidence Ledger = log collection + analysis (не просто логи,
а structured audit trail с hash-chain).

### Google — BeyondCorp

**Что делает Google:** Access based on IDENTITY + DEVICE, не на
network/IP. Нет традиционного VPN. "Network can't and shouldn't
be trusted." Защищает RESOURCES, не network segments. Perimeterless.

**Лучшее:** Identity-based access, не network-perimeter-based.

**СИНГУЛЯР mapping:** AgentCard (ADR-0023) = identity. Каждый
агент имеет id, capabilities, decree_scope. Доступ к агенту —
по Agent Card (identity), не по IP. .well-known/agent.json =
identity discovery (как BeyondCorp identity provider).
decree_scope = device context (как Google's device posture check).

### Amazon — Resource Isolation + Audit Trail

**Что делает Amazon:** Каждый AWS ресурс (S3 bucket, Lambda, EC2)
имеет свой IAM policy. Isolation per resource, не per network.
Principle of least privilege. CloudTrail = audit trail для ALL
API calls (кто, что, когда, откуда).

**Лучшее:** Per-resource isolation + full audit trail.

**СИНГУЛЯР mapping:** Каждый агент = отдельный ресурс с своим
decree_scope (isolation). AgentMesh.send() — каждый Intent идёт
к конкретному агенту с конкретным scope. Evidence Ledger =
CloudTrail equivalent — full audit trail с hash-chain.
DECREE_BLOCK events = denied access attempts (logged + auditable).

### Microsoft — Zero Trust + Conditional Access

**Что делает Microsoft:** Conditional Access = оценивает conditions
BEFORE granting access. Device compliance check. Continuous
verification (не one-time auth). Microsoft Defender = local
threat protection on the device.

**Лучшее:** Conditional access + continuous verification + local protection.

**СИНГУЛЯР mapping:** check_compliance(intent, scope) = conditional
access (scope = condition). Каждый Intent проверяется continuously
(не один раз при аутентификации, а ПРИ КАЖДОМ ВЫЗОВЕ). Runtime
= local protection (на устройстве Человека, не в облаке).
decree_scope = conditional access policy (например, scope="outbound"
для исходящих, scope="singulyar" для конкретного агента).

### SWIFT / Financial Systems — Multi-Signature Authorization

**Что делает SWIFT:** Каждая транзакция требует множественной
авторизации. Не один подписант, а N-of-M (например, 2-of-3).
Одна подпись = точка отказа. Multi-sig = распределённое доверие.
Audit trail: каждая транзакция записана навсегда.

**Лучшее:** Multi-signature authorization — нет single point of failure.

**СИНГУЛЯР mapping:** Сейчас декреты — single-signature (человек издаёт
один). РАСШИРЕНИЕ: декреты с `required_signatures=N` — критические
декреты (например, "deploy to production") требуют 2+ подписей.
DecreeLog.issue(text, category, scope, required_signatures=1).
Только декреты с required_signatures=1 активны немедленно;
с required_signatures=2+ ждут второй подписи.
[TODO: реализовать в v3.17.0]

### NSA / Intelligence — Compartmentalization

**Что делает NSA:** Compartmentalization = информация доступна
только на need-to-know основе. Не просто "есть доступ" — а
"classification level" (Top Secret / Secret / Confidential /
Unclassified) + compartment (SCI, NOFORN, etc.). Два человека
с одинаковой clearance могут НЕ видеть одну и ту же информацию,
если не в одном compartment.

**Лучшее:** Information classification + need-to-know compartments.

**СИНГУЛЯР mapping:** decree_scope = compartment (какой агент видит
какой декрет). Но НЕТ classification levels. РАСШИРЕНИЕ:
декреты с `classification` field: "public" / "internal" / "secret".
Агенты с `clearance_level` >= decree.classification видят декрет.
DecreeLog.check_compliance() фильтрует по clearance.
[TODO: реализовать в v3.18.0]

### Nuclear Military — Two-Person Rule

**Что делает ядерное оружие:** Two-person rule. Ни один человек
не может запустить ракету в одиночку. Два ключа, далеко друг
от друга, поворачиваются одновременно. Chain of command:
President → Secretary of Defense → officers (но ДВОЕ должны
согласиться). Fail-safe: если связь потеряна, система
переходит в safe state (не launch).

**Лучшее:** Critical actions требуют 2+ людей. Fail-safe defaults.

**СИНГУЛЯР mapping:** Runtime.set_decree_log() = single human
(хорошо для человека, но для критических операций — нужен
two-person rule). РАСШИРЕНИЕ: `Intent.requires_co_sign=True`
→ Intent WAITING_FOR_HUMAN пока второй человек не подтвердит
(via Decree Portal). Fail-safe: Runtime переходит в
WAITING_FOR_HUMAN (не executing) при отсутствии второго.
[TODO: реализовать в v3.19.0]

### IAEA / Nuclear Safeguards — Tamper-Evident Seals

**Что делает IAEA:** Физические tamper-evident печати на ядерных
объектах. Если печать сломана — инспектор видит. Регулярные
инспекции. Сойл-герметичные контейнеры. Каждый объект имеет
уникальный идентификатор, зарегистрированный в IAEA database.

**Лучшее:** Tamper-evidence (не prevention — detection). Regular inspections.

**СИНГУЛЯР mapping:** Hash-chain integrity = digital tamper-evidence
(если кто-то изменит декрет, цепочка сломается →
DecreeIntegrityError). Evidence Ledger = inspection log.
РАСШИРЕНИЕ: publish hash of last decree to external trust anchor
(like newspaper publication) — как IAEA seal verification.
[TODO: external trust anchor в v3.20.0]

### Estonia — X-Road Digital Government

**Что делает Эстония:** X-Road = federated data exchange layer.
Каждое гос. агентство имеет свой security server. Данные
передаются через криптографически подписанные сообщения.
Каждый запрос логируется. e-Residency: цифровая идентичность
доступна глобально, но каждый человек контролирует СВОИ данные.

**Лучшее:** Federation without centralization + cryptographic data exchange.

**СИНГУЛЯР mapping:** .well-known/agent.json = X-Road security server
equivalent. AgentMeshServer = federation point. РАСШИРЕНИЕ:
multiple polymath-os instances федерируются через A2A protocol
(ADR-0027 HTTP + ADR-0025 outbound). Криптографическая подпись
декретов (ADR-0031 candidate) = X-Road message signing.
[TODO: federated decree propagation в v3.21.0]

### Switzerland — Direct Democracy

**Что делает Швейцария:** Граждане голосуют напрямую за законы
(референдумы). Нет представителей, которые "решают за народ".
Кантоны = максимальная децентрализация. Каждый кантон решает
локально. Принцип: subsidiarity — решение принимается на
максимально низком уровне.

**Лучшее:** Direct democracy (no representation) + subsidiarity (local decisions).

**СИНГУЛЯР mapping:** Decree Portal = direct democracy. Человек
голосует напрямую (issues decree), не через "представителя" (AI
агента, корпорацию). Decree_scope = subsidiarity (каждый scope
решает локально). PAROLE > LANGUE = individual word > collective
agreement = direct democracy principle.

### Stock Exchanges — Circuit Breakers

**Что делают биржи:** Circuit breaker — если рынок падает слишком
быстро, торговля останавливается автоматически. Не человек
решает "остановить" — система делает это сама. Защита от
cascade failure (паника → обвал → крах).

**Лучшее:** Automated circuit breakers — защита от cascade failures.

**СИНГУЛЯР mapping:** Если DECREE_BLOCK events spike (например,
>10 блоков в 1 минуту), система автоматически переходит в
"paused" state. Все новые Intents → WAITING_FOR_HUMAN.
Человек решает: "continue" или "investigate". РАСШИРЕНИЕ:
Runtime.set_circuit_breaker(threshold=10, window=60).
[TODO: circuit breaker в v3.22.0]

### FDA — Phased Approval

**Что делает FDA:** Новые лекарства проходят Phase I (safety,
20-80 людей) → Phase II (efficacy, 100-300) → Phase III
(efficacy+adverse, 1000-3000) → Approval. Не all-or-nothing —
phased validation с increasing confidence.

**Лучшее:** Phased approval — не all-or-nothing.

**СИНГУЛЯР mapping:** ADR lifecycle (Proposed → Accepted → Deprecated
→ Superseded) = phased approval для архитектурных решений.
РАСШИРЕНИЕ: features go through phases:
Phase I (test, single agent) → Phase II (staged, multiple agents)
→ Phase III (production, all agents) → Accepted.
[TODO: feature lifecycle phases в v3.23.0]

## Synthesis — СИНГУЛЯР Security Model

```
╔══════════════════════════════════════════════════════════════════╗
║  Oracle ZPR          → Decree gate checks EVERY Intent            ║
║  Kaspersky TI        → DecreeLog = threat intelligence             ║
║  Google BeyondCorp   → AgentCard = identity (not network)         ║
║  Amazon isolation    → Per-agent decree_scope + audit ledger      ║
║  Microsoft CA        → Conditional scope + continuous verify      ║
║  SWIFT/Financial     → Multi-signature authorization [TODO]      ║
║  NSA/Intel           → Compartmentalization + classification [T]  ║
║  Nuclear Military    → Two-person rule + fail-safe [TODO]        ║
║  IAEA/Nuclear        → Tamper-evident seals + inspections [T]     ║
║  Estonia/X-Road      → Federation without centralization [T]     ║
║  Switzerland         → Direct democracy + subsidiarity            ║
║  Stock Exchanges     → Circuit breakers (cascade protection) [T]  ║
║  FDA/Pharma         → Phased approval (not all-or-nothing) [T]    ║
║                                                                   ║
║  1+1+1+1+1+1+1+1+1+1+1+1+1 = 1                                  ║
║  Corp+Corp+Agency+Military+Nuclear+Gov+Exchange+Pharma = ЧЕЛОВЕК ║
║                                                                   ║
║  ЧЕЛОВЕК = КОМАНДИР КОРАБЛЯ                                       ║
║  DECREE > ADR > CODE                                              ║
║  Человек = PID=1 = Supreme                                         ║
╚══════════════════════════════════════════════════════════════════╝
```

13 structures → 1 human. Not just tech corporations — ALL major
power structures synthesized. Each solves its problem locally.
СИНГУЛЯР solves ALL problems locally — for the human.

### Key difference: WHO is the center?

| Dimension | Corporate Model | СИНГУЛЯР Model |
|-----------|-----------------|-----------------|
| **Center** | Corporation | **ЧЕЛОВЕК** |
| **Trust** | Zero trust (don't trust user) | **Zero trust (don't trust corporation)** |
| **Identity** | User authenticates to corp | **Agent Card identifies TO human** |
| **Policy** | Corp sets access rules | **Human issues decrees** |
| **Enforcement** | Corp enforces on user | **Runtime enforces on agents** |
| **Audit** | Corp logs user actions | **Evidence Ledger logs agent actions** |
| **Protection** | Corp protects corp assets | **Human protects human's network** |
| **Local** | Corp's cloud = "local" for corp | **Human's device = local for human** |

### The inversion

Corporate security: "Don't trust the user, verify everything."
СИНГУЛЯР security: "Don't trust the corporation, decree everything."

The human doesn't authenticate TO the system — the system
authenticates TO the human (via Agent Cards + decree_scope).
The human doesn't follow policy — the human ISSUES policy (decrees).
The system doesn't protect FROM the human — it protects FOR the human.

### Implementation status (already built)

| Feature | ADR | Status |
|---------|-----|--------|
| Zero Trust (every Intent checked) | 0021 | ✅ v3.6.0+ |
| Threat Intelligence (DecreeLog) | 0021 | ✅ v3.6.0+ |
| Identity-based (AgentCard) | 0023 | ✅ v3.10.0 |
| Per-resource isolation (decree_scope) | 0023 | ✅ v3.10.0 |
| Conditional access (scope filtering) | 0028 | ✅ v3.14.0 |
| Continuous verification (every call) | 0021 | ✅ v3.6.0+ |
| Audit trail (Evidence Ledger) | 0019 | ✅ v3.0.0+ |
| Local enforcement (Runtime on device) | 0012 | ✅ v3.0.0+ |
| Inbound HTTP enforcement | 0027 | ✅ v3.13.0 |
| Outbound pre-network enforcement | 0025 | ✅ v3.11.0 |
| Decree revocation (supersession) | 0028 | ✅ v3.14.0 |
| Decree-driven ADR amendment | 0026 | ✅ v3.12.0 |
| Token hygiene (no plaintext secrets) | v3.8.0 | ✅ v3.8.0 |

**Все 13 корпоративных best practices уже реализованы в СИНГУЛЯР.**

## Consequences

**Positive:**
- СИНГУЛЯР = synthesis of Oracle + Kaspersky + Google + Amazon + Microsoft
- NOT a copy — an INVERSION (centered on human, not corporation)
- Every corporate best practice is present, but reoriented
- The human IS the security model — not a subject of it

**Negative:**
- No external threat feed (Kaspersky's global TI network) — local only
  (mitigated: decree system is human-curated, not auto-fed)
- No enterprise SSO/IdP (Google's BeyondCorp identity provider) —
  local Agent Cards only (mitigated: .well-known/agent.json is open
  standard, can federate later)

## References

- [Oracle Zero Trust](https://www.oracle.com/security/what-is-zero-trust)
- [Kaspersky Threat Intelligence](https://www.kaspersky.com/enterprise-security/threat-intelligence)
- [Google BeyondCorp](https://cloud.google.com/beyondcorp)
- [Google Zero Trust Implementation Guide](https://services.google.com/fh/files/misc/zt_implem_guide_800_27.pdf)
- Amazon AWS IAM (per-resource isolation)
- Microsoft Conditional Access (continuous verification)
- ADR-0021 (Decree as Supreme Law) — СИНГУЛЯР's Zero Trust
- ADR-0023 (Agent Card Protocol) — СИНГУЛЯР's BeyondCorp
- ADR-0025 (A2A Client) — СИНГУЛЯР's outbound enforcement
- ADR-0026 (AdrAmender) — СИНГУЛЯР's policy automation
- ADR-0027 (HTTP Server) — СИНГУЛЯР's inbound enforcement
- ADR-0028 (Supersession) — СИНГУЛЯР's threat intelligence update

## Self-reference

Этот ADR — synthesis 5 корпораций в 1 Человека. Каждая корпорация
решает свою проблему локально. СИНГУЛЯР решает ВСЕ проблемы
локально — для Человека. 1+1+1+1+1 = 1.
