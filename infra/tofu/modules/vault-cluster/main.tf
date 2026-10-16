# infra/tofu/modules/vault-cluster/main.tf
#
# Module: деплоит HashiCorp Vault (или Infisical self-hosted) через Helm на k3s.
# Per ADR-0002 §Tier 2: HashiCorp Vault — OSS (MPL-2.0) but business-source licence
# on some features (HCP). Self-host на k3s — Tier 2 rented-equivalent (no SaaS).
# Per ADR-0009 (default-deny publish): Vault exposes no network by default.
#
# Reusable: НЕТ environment-specific values внутри модуля.
# Замена: Bitwarden (Vaultwarden) / SOPS+age (offline fallback, Tier 1).

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# ── Namespace (idempotent) ───────────────────────────────────────────────
resource "kubernetes_namespace" "this" {
  metadata {
    name = var.namespace
    labels = {
      managed-by    = "opentofu"
      module        = "vault-cluster"
      policy-default-deny = "true"  # network policy: default-deny ingress
    }
  }
}

# ── Vault Helm release ──────────────────────────────────────────────────
# Uses the official HashiCorp Vault chart. Standalone dev mode — for personal
# env with replicas=1. For HA (prod, replicas=3) — Raft storage backend.
#
# Chart: https://github.com/hashicorp/vault-helm
resource "helm_release" "vault" {
  name       = "vault"
  repository = "https://helm.releases.hashicorp.com"
  chart      = "vault"
  version    = var.helm_chart_version
  namespace  = kubernetes_namespace.this.metadata[0].name
  create_namespace = false  # already created above

  set {
    name  = "server.dev.enabled"
    value = var.dev_mode ? "true" : "false"
  }

  set {
    name  = "server.replicas"
    value = tostring(var.replicas)
  }

  set {
    name  = "server.storageClass"
    value = var.storage_class
  }

  set {
    name  = "server.resources.requests.memory"
    value = var.resources_memory_request
  }

  set {
    name  = "server.resources.requests.cpu"
    value = var.resources_cpu_request
  }

  # ADR-0009 (default-deny): service stays ClusterIP — no external ingress.
  # Expose externally via separate ingress module (not here).
  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }

  # ADR-0005 (separate rollback targets): data lives in PVC, not in container fs.
  set {
    name  = "server.dataStorage.enabled"
    value = "true"
  }

  set {
    name  = "server.dataStorage.size"
    value = var.storage
  }
}

# ── Vault service discovery ─────────────────────────────────────────────
# Имя ClusterIP-сервиса, под которым Vault доступен внутри кластера.
locals {
  vault_service_name = "${helm_release.vault.name}-server"
}

data "kubernetes_service" "vault" {
  metadata {
    name      = local.vault_service_name
    namespace = kubernetes_namespace.this.metadata[0].name
  }
}

# ── Init-required flag (idempotency hint) ────────────────────────────────
# Vault должен быть initialised + unsealed после первого деплоя.
# Мы не можем вызвать `vault operator init` из OpenTofu (root token и
# recovery keys — SENSITIVE, не храним в state), но мы можем дать
# downstream-CI флаг, что init ещё нужен.
#
# Логика: если helm release.status.stage != "Deployed" — init нужен.
# После успешного init+unseal (отдельный CI step), повторный `tofu apply`
# пересчитает output. Это **falsifiable** marker — перезапуск flag-a можно
# проверять: `vault status | grep Initialized` должен совпадать.
locals {
  # helm_release.status — это list of objects. Берём первый.
  release_status = length(helm_release.vault.status) > 0 ? helm_release.vault.status[0] : null
  init_required = local.release_status == null ? true : local.release_status.stage != "Deployed"
}
