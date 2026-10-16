# infra/tofu/providers.tf — provider blocks
#
# Сами providers не содержат кредов — берут их из root variables,
# которые приходят из SOPS-decrypted environments/<env>/secrets.sops.yaml.
# Per ADR-0002 §Tier 2: Cloudflare / Hetzner — rented services, replaceable.
# Per ADR-0011: container-runtime-agnostic.

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

provider "hcloud" {
  token = var.hetzner_token
}

provider "hetznerdns" {
  api_token = var.hetzner_dns_token
}

provider "kubernetes" {
  # Локальный k3s — у себя на VPS. kubeconfig подставляется через env.
  host                   = var.k8s_host
  client_certificate     = var.k8s_client_cert
  client_key             = var.k8s_client_key
  cluster_ca_certificate = var.k8s_cluster_ca_cert
}

provider "helm" {
  kubernetes {
    host                   = var.k8s_host
    client_certificate     = var.k8s_client_cert
    client_key             = var.k8s_client_key
    cluster_ca_certificate = var.k8s_cluster_ca_cert
  }
}
