# infra/tofu/versions.tf — OpenTofu + required providers
#
# OpenTofu 1.6+ — drop-in совместим с Terraform 1.6+ syntax.
# BSL lock-in Terraform avoided per ADR-0002 §Tier 1 (sovereign core):
#   OpenTofu — Linux Foundation, MPL-2.0, без ограничений BSL.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
        # Hetzner Cloud (servers + firewalls)
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.0"
    }

    # Hetzner DNS (separate API from Cloud)
    hetznerdns = {
      source  = "timohirt/hetznerdns"
      version = "~> 2.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }

    external = {
      source  = "hashicorp/external"
      version = "~> 2.0"
    }

    # kubernetes + helm providers — for Helm releases on k3s
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }

    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}
