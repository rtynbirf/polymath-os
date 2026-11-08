# infra/tofu/environments/personal/providers.tf
#
# Provider blocks for the personal environment root module.
# Per docs/05-devex-ci.md §OIDC trust: no static creds in code.
# Per ADR-0002 §Tier 2: providers rented, replaceable.

provider "hcloud" {
  token = var.hetzner_token
}

provider "kubernetes" {
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
