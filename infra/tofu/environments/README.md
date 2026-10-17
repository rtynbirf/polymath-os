# infra/tofu/environments/ — per-environment OpenTofu roots

> Каждый environment — отдельный runnable root для `tofu init/plan/apply`.
> Модули общие (`../modules/*`), но state, variables, secrets — изолированы.

## Структура

```
environments/
├── personal/         # личная, одна VPS, dev mode
│   ├── main.tf       # composition of modules
│   ├── .sops.yaml    # SOPS config (age recipient)
│   └── secrets.sops.yaml  # SOPS-encrypted secrets (committed)
├── staging/          # (to be added) — multi-replica, prod-like
├── prod/             # (to be added) — HA, restricted SSH
└── shared/           # bootstrap-only: S3 + DynamoDB + OIDC IAM role
```

## Bootstrap sequence (one-off per AWS account)

1. **Создать shared-инфру вручную** (chicken-egg):

   ```bash
   cd infra/tofu/environments/shared
   tofu init -backend=false   # пока бэкенда нет — используем local
   tofu plan
   tofu apply                  # создаёт S3 + DynamoDB + IAM role
   ```

2. **Записать outputs в backend.tf**:

   ```bash
   tofu output -json > /tmp/shared-outputs.json
   # дальше — вручную скопировать bucket/table names в environments/<env>/backend.tf
   ```

3. **Создать age identity** (Tier 1 sovereign crypto per ADR-0002):

   ```bash
   age-keygen -o ~/.config/sops/age/keys.txt
   cat ~/.config/sops/age/keys.txt | head -1   # public key — в .sops.yaml
   chmod 600 ~/.config/sops/age/keys.txt
   ```

   (Production: тот же ключ — в 1Password item `polymath-infra-age-identity`.)

4. **Обновить `.sops.yaml`** в environment — заменить placeholder age key.

5. **Зашифровать секреты**:

   ```bash
   sops environments/personal/secrets.sops.yaml
   # editor opens → fill in real values → save → file is re-encrypted
   ```

## How to use (per environment)

```bash
cd infra/tofu/environments/personal

# 1. Decrypt secrets to temp file (NEVER commit decrypted)
sops -d secrets.sops.yaml > /tmp/secrets.yaml

# 2. Configure backend (after shared is bootstrapped)
tofu init -backend-config=secrets.sops.yaml 2>/dev/null || tofu init -backend=false

# 3. Format check
tofu fmt -recursive

# 4. Plan
tofu plan -var-file=/tmp/secrets.yaml -out=tfplan
#   → review plan, especially +/- resources

# 5. Clean up secrets
shred -u /tmp/secrets.yaml

# 6. Apply — ТОЛЬКО через CI (см. .github/workflows/tofu.yml)
#    Локально: только если ты не в prod env
```

## PR review checklist (for human reviewer)

- [ ] `tofu fmt -check -recursive` green
- [ ] `tofu validate` green
- [ ] `tofu plan` reviewable in PR comments (CI artefact)
- [ ] No `prevent_destroy` removed from production resources
- [ ] No new `sensitive` outputs leaked to plain text
- [ ] No `force = true` on resources that hold state (DBs, volumes, tfstate)
- [ ] Module `source` paths are relative (no cross-repo references)
- [ ] Variables are typed (no `any` on public inputs)

## CI rules (per `.github/workflows/tofu.yml`)

| Event | Action |
|---|---|
| PR touching `infra/tofu/` | `tofu fmt -check` + `tofu validate` + `tofu plan` (OIDC trust, no static creds) |
| Push to `main` | **Nothing** — apply is manual dispatch |
| Manual dispatch with approval | `tofu apply` on chosen env |
| Manual dispatch on `prod` env | Requires 2 approvals (CODEOWNERS + extra) |

Per ADR-0005 (separate rollback targets): `tofu destroy` on prod env
requires same manual dispatch + approval chain. No emergency bypass.

## Sovereignty map (per ADR-0002)

| Component | Tier | Replacement |
|---|---|---|
| OpenTofu | Tier 1 (OSS, MPL) | Terraform fork — drop-in |
| SOPS + age | Tier 1 (sovereign core) | GPG fallback (no network) |
| Cloudflare DNS | Tier 2 | bind9 self-host / Bunny CDN |
| Hetzner Cloud | Tier 2 | OVH / Scaleway / mini-PC |
| AWS S3 (tfstate) | Tier 2 | MinIO self-hosted |
| AWS DynamoDB (lock) | Tier 2 | etcd / Consul KV |
| HashiCorp Vault (Helm) | Tier 2 | Vaultwarden / SOPS+age offline |
| Unleash | Tier 2 | Git-ops feature branches (no SaaS) |

## Anti-patterns

- Long-lived access keys в GitHub Actions secrets (use OIDC)
- `tofu apply` из `git push` (no approval gate)
- `force_destroy = true` на tfstate bucket (ADR-0005 violation)
- Plain `.tfvars` with secrets (always SOPS)
- Hard-coded AMI IDs (use SSM parameter lookup)
- Module inlined in `main.tf` (always `modules/` subdirectory)
- Output of `sensitive = true` variable without `sensitive = true` on output
