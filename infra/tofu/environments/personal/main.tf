# infra/tofu/environments/personal/main.tf
#
# Personal environment — composition of modules.
# Все значения либо берём из SOPS-decrypted secrets.sops.yaml (sensitive),
# либо из environment-specific overrides (non-sensitive).
#
# Per ADR-0009 (default-deny): services expose no public ingress by default.
# Per ADR-0005 (separate rollback targets): IaC apply is `destroy`-able.

terraform {
  required_version = ">= 1.6.0"
  # backend block is in backend.tf (one per env)
}

# Pull in the shared root configuration. NOTE: in OpenTofu, each directory
# is its own root module. We COPY versions/providers/variables here OR symlink.
# For portability (no symlinks on Windows), the practical pattern is to
# use terragrunt. But for one environment, we keep self-contained files
# and re-declare module blocks below.

locals {
  domain = "polymath.example.com"
}

,
    {
      name     = "@"
      type     = "AAAA"
      value    = module.hetzner_vps.ipv6
      ttl      = 1
      proxied  = false
      priority = null
    },
    {
      name     = "vault"
      type     = "CNAME"
      value    = local.domain
      ttl      = 1
      proxied  = false
      priority = null
    },
    {
      name     = "unleash"
      type     = "CNAME"
      value    = local.domain
      ttl      = 1
      proxied  = false
      priority = null
    },
    {
      name     = "grafana"
      type     = "CNAME"
      value    = local.domain
      ttl      = 1
      proxied  = false
      priority = null
    },
  ]
}

# ── Hetzner VPS (single for personal env) ────────────────────────────────
module "hetzner_vps" {
  source = "../../modules/hetzner-server"

  name        = "polymath-personal-1"
  server_type = "cpx21" # 3 vCPU / 4 GB / 80 GB — runs k3s + LGTM + Unleash
  image       = "debian-12"
  location    = "nbg1"

  ssh_keys = [
    {
      name = "polymath-1"
      # Real public keys come from secrets.sops.yaml via a separate local value
      # (placeholder here — see README.md §Bootstrap).
      public_key = var.ssh_public_key_primary
    }
  ]

  # Personal env: SSH open to world (avoid lockout). For prod: restrict.
  ssh_source_ips = ["0.0.0.0/0", "::/0"]

  labels = {
    environment = "personal"
    role        = "k3s-node"
  }
}

# ── Vault via Helm (k3s already running on the VPS) ──────────────────────
module "vault" {
  source = "../../modules/vault-cluster"

  namespace = var.vault_namespace
  replicas  = 1 # personal: standalone dev mode
  storage   = "10Gi"
  dev_mode  = true # ADR-0009: no external access; dev mode fine
}

# ── Unleash via Helm ────────────────────────────────────────────────────
module "unleash" {
  source = "../../modules/unleash"

  namespace      = var.unleash_namespace
  replicas       = 1
  ingress_domain = local.domain
}
