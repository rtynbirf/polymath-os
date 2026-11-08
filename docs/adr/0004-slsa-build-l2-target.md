# ADR-0004: SLSA Build Level 2 как цель v1.0, Level 3 только с доказанной изоляцией сборщика

**Date:** 2026-10-16
**Status:** Accepted
**Deciders:** @USER
**Audit:** A3 (SLSA Level 2+ vs Level 3)

## Context

Отчёт Polymath OS содержал противоречие:
- Критерии приёмки: «SLSA Level 2+»
- Паттерны: «Level 3 при правильной настройке»

Эти заявления совместимы только при доказательстве изоляции сборщика. По спецификации SLSA:
- **Build L2** = подписанное происхождение от хостируемой платформы
- **Build L3** = платформа препятствует подделке происхождения самой сборкой (hermetic build, no network, isolated builder)

GitHub Actions с hosted runners по умолчанию — L2. L3 требует либо self-hosted isolated runner, либо доверенную платформу с доказанной изоляцией.

## Decision

### Целевой уровень для v1.0.0 — **Build L2**

- Cosign keyless signing (OIDC) на каждый container image
- SLSA provenance через `slsa-framework/slsa-github-generator`
- CycloneDX SBOM attestation (`cosign attest --predicate sbom.json --type cyclonedx`)
- Verify в deploy-шаге (`cosign verify` + `cosign verify-attestation`) — без signature не деплоится

### Level 3 — только после доказанной изоляции сборщика

Не писать «Level 2+». L3 — это **отдельная задача** с собственными критериями:

- Self-hosted isolated runner (или доказуемо изолированная платформа)
- Hermetic build (no network access during build)
- Reproducible build (byte-identical artifact from same source)
- Доверенный корень доверия (не GitHub OIDC только)

L3 будет рассмотрен в roadmap после v1.0.0 — отдельная фаза или ADR-0013.

## Consequences

- **Positive:**
  - Заявления об SLSA становятся честными: L2 — факт, L3 — explicit future goal
  - Регуляторы (EU CRA, NIST SSDF) требуют L2 — это выполнено
  - L3 не «объявлен» раньше времени, что создало бы false confidence
- **Negative:**
  - L3 остаётся будущей работой — может never happen
  - Enterprise-клиенты с требованием L3 — не закрыты v1.0
- **Neutral:**
  - SBOM по-прежнему генерируется на каждый release (CycloneDX)
  - `cosign verify` + `cosign verify-attestation` в deploy — blocking

## Alternatives Considered

### «SLSA Level 2+» как в оригинальном отчёте
Отвергнуто: нечестное заявление, создаёт impression что L3 уже есть, когда его нет.

### L3 сразу как цель v1.0
Отвергнуто: требует self-hosted isolated runner + reproducible build — это значительная инфраструктурная работа, не помещается в 90 дней.

## Verification

- `cosign verify` + `cosign verify-attestation` на deploy-шаге — **blocking** (без signature не деплоится)
- Отрицательный тест: артефакт без attestation должен **не деплоиться** (CI fail)
- SBOM (CycloneDX) — artifact, загружаемый через `actions/upload-artifact`

## References

- Audit: `runtime/docs/AUDIT_POLYMATH.md` §A3
- SLSA Framework: https://slsa.dev
- slsa-github-generator: https://github.com/slsa-framework/slsa-github-generator
- cosign: https://github.com/sigstore/cosign
