# infra/ — Polymath OS Layer 4 (Infra)

> Инфраструктурный под-проект: OpenTofu + Docker Compose + observability stack.
> Отдельный flake (`infra/flake.nix`) — dev-shell с инфра-инструментами.

## Структура

```
infra/
├── flake.nix                          # отдельный dev-shell: opentofu, terragrunt, k8s, DNS
├── compose.observability.yaml         # Grafana LGTM + Glitchtip + Prometheus + OTel collector
├── compose.unleash.yaml               # Unleash feature flags (self-hosted)
├── scripts/
│   └── bootstrap-observability.sh     # bring up observability on a clean VPS
├── tofu/                              # OpenTofu (Terraform fork, BSL-safe)
│   ├── versions.tf                     # required_version >= 1.6.0, required_providers
│   ├── backend.tf                      # S3 backend + DynamoDB lock (placeholder creds)
│   ├── providers.tf                    # cloudflare, hcloud, hetznerdns, kubernetes, helm
│   ├── variables.tf                    # root variables (env, domain, tokens — sensitive)
│   ├── outputs.tf                      # cluster_endpoint, dns_records, vault_address, unleash_address
│   ├── modules/                        # reusable modules (no env-specific values)
│   │   ├── cloudflare-dns/              # A/AAAA/CNAME/MX records
│   │   ├── hetzner-server/              # VPS + firewall
│   │   ├── vault-cluster/               # HashiCorp Vault via Helm
│   │   └── unleash/                     # Unleash feature flags via Helm
│   └── environments/
│       ├── personal/                   # personal env composition + SOPS secrets
│       │   ├── main.tf
│       │   ├── .sops.yaml               # age recipient
│       │   └── secrets.sops.yaml        # encrypted (committed)
│       ├── shared/                      # bootstrap: S3 bucket + DynamoDB + IAM OIDC
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── README.md                   # how to tofu init/plan/apply per env
└── README.md                           # ← this file
```

## How to `tofu plan` locally

```bash
# 1. Enter infra dev-shell
nix develop ./infra      # provides opentofu, terragrunt, helm, kubectl, k9s, jq, sops, age

# 2. Bootstrap SOPS age identity (one-off per machine)
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt

# 3. Decrypt secrets (to /tmp — never next to source)
cd infra/tofu/environments/personal
sops -d secrets.sops.yaml > /tmp/secrets.yaml

# 4. Configure backend (skip until shared/ is bootstrapped)
tofu init -backend=false

# 5. Format check + validate
tofu fmt -recursive
tofu validate

# 6. Plan
tofu plan -var-file=/tmp/secrets.yaml -out=tfplan
#   → review plan carefully (especially +/- resources)
tofu show tfplan   # human-readable plan

# 7. Clean up
shred -u /tmp/secrets.yaml
rm -f tfplan
```

## How `apply` happens — CI only

| Event | Action | By whom |
|---|---|---|
| PR touching `infra/tofu/` | `tofu fmt -check` + `tofu validate` + `tofu plan` | automated (no creds needed for fmt/validate; OIDC for plan) |
| Push to `main` | **nothing** — apply is never automatic | — |
| Manual dispatch with approval | `tofu apply` on chosen environment | human + CODEOWNERS |

Workflows: `.github/workflows/tofu.yml`. OIDC trust → AWS role assumed
short-lived (no static `AWS_ACCESS_KEY_ID`). Per ADR-0005: `tofu apply`
on `prod` requires 2 approvals (CODEOWNERS + extra).

## Sovereignty map (per ADR-0002)

Каждый компонент инфры — в Sovereignty Registry. Здесь — та часть, что
используется в `infra/`.

### Tier 1 — sovereign core (offline-able)

| Component | Format | Replacement |
|---|---|---|
| OpenTofu | HCL | Terraform (drop-in) |
| SOPS + age | X25519 + ChaCha20-Poly1305 | GPG (fallback) |
| `git` history | git objects | itself |
| Module source files | HCL text | — |

### Tier 2 — rented services (replaceable by contract)

| Service | Capability | Replacement | Offline fallback |
|---|---|---|---|
| Cloudflare | DNS / CDN | bind9 (self-host) / Bunny CDN | `/etc/hosts` |
| Hetzner | VPS (k3s host) | OVH / Scaleway / mini-PC | local bare metal |
| AWS S3 (tfstate) | state storage | MinIO (self-host) | local file backend |
| AWS DynamoDB (lock) | distributed lock | etcd / Consul KV | local lock file |
| HashiCorp Vault (Helm) | secrets + dynamic creds | Vaultwarden / SOPS+age | age-encrypted files in git |
| Unleash (Helm) | feature flags | git-ops feature branches | long-lived branches (worse) |
| Grafana LGTM | observability | Promtail+Jaeger+Mimir separate | structured logs to stdout |
| Glitchtip | error tracking | Sentry (SaaS, Tier 2) | structured logs in Loki |
| 1Password (CLI) | bootstrap-time secret fetch | Vaultwarden | manual key transfer |
| GitHub Actions (OIDC) | CI for `tofu apply` | Woodpecker CI / Forgejo | `tofu apply` from laptop |

### Tier 3 — lock-in (none in `infra/`)

Никаких закрытых форматов в `infra/`. HCL, YAML, JSON — всё plaintext.
`secrets.sops.yaml` — encrypted at rest, but decryptable offline with age
identity (Tier 1 sovereign).

## Quarterly drill (per ADR-0002 §Sovereignty metric)

| Drill | How | Expected |
|---|---|---|
| Cloudflare offline | change NS records to Hetzner DNS, wait for TTL | DNS resolves within 4× TTL |
| AWS S3 offline | `tofu init -reconfigure -backend=local` | tfstate reads from local file |
| Hetzner offline | k3s на local bare metal | cluster up in ≤30 min |
| 1Password offline | age identity from encrypted backup | secrets decrypt |

Records of each drill — in `docs/runbook/RUNBOOK.md` (per-env RPO/RTO).

## Anti-patterns (per `docs/05-devex-ci.md`)

- Long-lived `AWS_ACCESS_KEY_ID` в GitHub Actions secrets → use OIDC
- `tofu apply` triggered by `git push` to `main` → manual dispatch only
- `prevent_destroy = false` на tfstate bucket → ADR-0005 violation
- Plain `.tfvars` with secrets → SOPS only
- Hard-coded AMI / image IDs → use SSM parameter lookup
- Modules inlined in `main.tf` → `modules/` subdirectory
- Cross-repo `source = "github.com/..."` → relative path
- Output of `sensitive = true` variable without `sensitive = true` on output
- `docker compose down -v` without explicit ⛔ confirmation in runbook

## LFS-рекомендации

См. `ROADMAP.md` Фаза 1 + Фаза 2. Резюме для `infra/`:

1. flake.nix + direnv → reproducible infra shell (Nixpkgs 24.05)
2. SOPS+age → secrets in git, decryptable offline (Tier 1)
3. OpenTofu (MPL, BSL-safe) → no Terraform BSL lock-in
4. self-host observability → no Sentry/datadog SaaS
5. `bootstrap-observability.sh` → one-command bring-up on clean VPS

## Референсы

- OpenTofu: https://opentofu.org
- Terragrunt: https://terragrunt.gruntwork.io
- SOPS: https://github.com/getsops/sops
- age: https://github.com/FiloSottile/age
- HashiCorp Vault Helm chart: https://github.com/hashicorp/vault-helm
- Unleash: https://www.getunleash.io
- Grafana LGTM: https://grafana.com/solutions/observability/
- Glitchtip: https://glitchtip.com
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
