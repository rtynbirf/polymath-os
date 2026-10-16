# infra/tofu/modules/unleash/main.tf
#
# Module: деплоит Unleash feature flags через Helm на k3s.
# Per ADR-0002 §Tier 2: Unleash self-hosted — Apache-2.0 (server).
# Per ROADMAP §trunk-based: feature flags вместо long-lived branches.
#
# Reusable: НЕТ environment-specific values внутри модуля.
# Замена: git-ops feature branches (offline fallback, Tier 1).

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
  }
}

resource "kubernetes_namespace" "this" {
  metadata {
    name = var.namespace
    labels = {
      managed-by = "opentofu"
      module     = "unleash"
    }
  }
}

# ── Unleash Helm release ────────────────────────────────────────────────
# Chart: https://github.com/Unleash/unleash (helm chart from unleashed)
# Personal env: single replica, embedded postgres. For prod: external RDS.
resource "helm_release" "unleash" {
  name       = "unleash"
  repository = "https://docs.getunleash.io/docs/main/deploy/getting-started/operator/install-on-kubernetes"
  chart      = "unleash"
  version    = var.helm_chart_version
  namespace  = kubernetes_namespace.this.metadata[0].name
  create_namespace = false

  set {
    name  = "replicaCount"
    value = tostring(var.replicas)
  }

  set {
    name  = "service.type"
    value = "ClusterIP"   # ADR-0009 default-deny — expose via ingress module
  }
}

data "kubernetes_service" "unleash" {
  metadata {
    name      = "unleash"
    namespace = kubernetes_namespace.this.metadata[0].name
  }
}

locals {
  # Cluster-local service address for SDKs inside k8s.
  service_address = "http://${data.kubernetes_service.unleash.metadata[0].name}.${data.kubernetes_service.unleash.metadata[0].namespace}.svc.cluster.local:4242"

  # Externally-reachable dashboard URL via ingress (assumes nginx-ingress
  # with hostname "unleash.<domain>"). For personal env: port-forward suffices.
  dashboard_url = "https://unleash.${var.ingress_domain}"
}
