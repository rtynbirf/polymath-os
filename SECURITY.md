# Security Policy — Polymath OS

## Supported Versions

| Version | Supported |
|---------|----------|
| latest `main` + tagged releases | ✅ |
| anything older | ❌ |

## Reporting a Vulnerability

**НЕ открывай public issue для security vulnerability.**

Репорт через:
1. GitHub Security Advisories (Private): `https://github.com/USER/polymath-os/security/advisories/new`
2. Или email на `<security@example.com>` с PGP-encrypted payload

**Response time:** ≤72 часа на подтверждение получения. ≤7 дней — первоначальная оценка.

## Disclosure Policy

- **Coordinated disclosure:** после fix + release — публичный advisory с CVE.
- **Credit:** по желанию репортера.

## Hardening (built-in)

- **Secrets:** SOPS + age (private key НЕ в git), Doppler/1Password CI/CD injection, OIDC trust (no long-lived PATs).
- **SBOM:** CycloneDX на каждый release (artifact).
- **SLSA:** Level 2+ provenance на каждый контейнер.
- **Signing:** cosign keyless (OIDC) для всех container images.
- **SAST:** Semgrep + CodeQL в CI.
- **Container scan:** Trivy на images + filesystem.
- **Secret scan:** gitleaks в pre-commit + CI.

## Audit checklist

Раз в квартал (см. `docs/01-principles.md`):
- [ ] Все production releases имеют SBOM + cosign signature
- [ ] Все IAM роли используют OIDC trust (no long-lived keys)
- [ ] Все MCP-серверы имеют documented scope (least privilege)
- [ ] Все агенты имеют golden dataset в promptfoo
- [ ] Все services инструментированы OTel SDK
- [ ] `make destroy` откатывает IaC ≤5 минут
- [ ] Rollback проходит ≤60 секунд

## Contacts

- Security advisories: GitHub (private)
- PGP fingerprint: `<fill-in-on-init>`
