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
- **Token hygiene (v0.6):** `scripts/check_token_hygiene.py` — additional
  scan beyond gitleaks, catches plaintext GitHub PATs (`github_pat_`,
  `ghp_`, `gho_`, etc.) and env-var literal assignments in shell scripts.
  Added as 23rd `make verify` claim.

## Token hygiene — GitHub PAT best practices

**Background:** in the polymath-os v3.6.0 release session (2026-10-17),
a hardcoded `github_pat_...` token was embedded inline in a bash command.
GitHub's secret scanner auto-detected and revoked the token within minutes.
This section documents the lessons learned.

### NEVER do this:

```bash
# ❌ FORBIDDEN — token is in plaintext in bash history + session logs
GH_TOKEN='github_pat_PLACEHOLDER_EXAMPLE' \
  git push origin main

# ❌ FORBIDDEN — token persists in .git/config (anyone with read access can extract)
git remote set-url origin https://rtynbirf:github_pat_xxx@github.com/rtynbirf/polymath-os.git
```

### ALWAYS do this:

```bash
# ✓ Token passed via env var (not inline in command string)
export GH_TOKEN='github_pat_xxx'   # set once in shell session
git push origin main               # uses remote URL with no token

# ✓ If you must use token in remote URL (one-shot), reset afterwards:
git remote set-url origin "https://rtynbirf:${GH_TOKEN}@github.com/rtynbirf/polymath-os.git"
git push origin main
git remote set-url origin "https://github.com/rtynbirf/polymath-os.git"  # CLEAN

# ✓ Or use git credential helper (preferred for repeated use):
echo "https://rtynbirf:${GH_TOKEN}@github.com" | git credential approve
git push origin main  # credential helper injects auth transparently

# ✓ Or use `gh` CLI (separate auth flow, no token in git config):
gh auth login  # browser-based, no token in shell
git push origin main
```

### Why this matters

GitHub's secret scanner continuously scans:
- Public git repos (commits, blobs, history)
- GitHub Issues, PRs, Discussions
- GitHub Actions logs
- Other public GitHub surfaces

If a PAT appears in plaintext in any of these, GitHub auto-revokes it
within minutes (often <5 min). This is a security feature, but it means
any leaked token becomes immediately unusable.

For polymath-os specifically:
- `scripts/check_token_hygiene.py` is added to `make verify` (claim #23)
- It scans all `.py`, `.sh`, `.js`, `.yml`, `.md` files for known token patterns
- Threshold: 50+ chars after `github_pat_` prefix (avoids false positives on
  documentation examples like `github_pat_...` placeholder)
- Pre-commit hook: gitleaks (already configured in `.pre-commit-config.yaml`)
  catches staged files BEFORE they're committed
- CI: gitleaks action (Step 13 of `ci.yml`) scans all tracked files

### If a token IS leaked

1. **REVOKE IMMEDIATELY** at https://github.com/settings/tokens
   (click the token → Revoke)
2. **Audit access logs** at https://github.com/settings/security-log
   (look for unauthorized access in the leak window)
3. **Rotate any dependent credentials** (e.g. if the PAT was used in CI
   workflows, update those workflows to use a new PAT or OIDC)
4. **Document the incident** in this file (add a new section below with
   date, scope, root cause, mitigation)

### Token formats reference

| Prefix | Type | Total length |
|--------|------|--------------|
| `github_pat_` | Fine-grained PAT | ~93 chars |
| `ghp_` | Classic PAT (user) | 40 chars |
| `gho_` | OAuth token | 40 chars |
| `ghu_` | User-to-server | 40 chars |
| `ghs_` | Server-to-server | 40 chars |
| `ghr_` | Refresh token | 80 chars |

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
