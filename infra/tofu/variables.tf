# infra/tofu/variables.tf — root variables
#
# Все sensitive значения — marked sensitive = true.
# Никаких default-кредов. Реальные значения приходят через SOPS-decrypted
# secrets.sops.yaml (1Password CLI / age identity).
# Локально: `sops -d environments/personal/secrets.sops.yaml > /tmp/secrets.yaml`
# и потом `tofu apply -var-file=/tmp/secrets.yaml`.

# ── Environment identity ────────────────────────────────────────────────
variable "environment" {
  type        = string
  description = "Environment name (personal | staging | prod). Routes to separate tfstate key + module composition."
  validation {
    condition     = contains(["personal", "staging", "prod"], var.environment)
    error_message = "environment must be one of: personal, staging, prod."
  }
}

variable "domain" {
  type        = string
  description = "Root apex domain managed by Cloudflare (e.g. polymath.example.com). DNS records prefixed per service."
}

# ── Cloudflare (Tier 2: rented, replaceable — bind9 fallback per ADR-0002) ──
variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token with Zone:DNS:Edit permission on the target zone."
  sensitive   = true
}

# ── Hetzner (Tier 2: rented, replaceable — OVH/Scaleway/mini-PC fallback) ──
variable "hetzner_token" {
  type        = string
  description = "Hetzner Cloud API token. P1: rotate quarterly per Sovereignty Registry drill."
  sensitive   = true
}

variable "hetzner_dns_token" {
  type        = string
  description = "Hetzner DNS API token (separate from Cloud API). Used only if Cloudflare is replaced."
  sensitive   = true
}

# ── Kubernetes (k3s self-hosted) ────────────────────────────────────────
variable "k8s_host" {
  type        = string
  description = "k3s API server URL (https://host:6443). For local k3s on the same VPS, https://127.0.0.1:6443."
  default     = "https://127.0.0.1:6443"
}

variable "k8s_client_cert" {
  type        = string
  description = "PEM-encoded client certificate for k8s API."
  sensitive   = true
  default     = ""
}

variable "k8s_client_key" {
  type        = string
  description = "PEM-encoded client key for k8s API."
  sensitive   = true
  default     = ""
}

variable "k8s_cluster_ca_cert" {
  type        = string
  description = "PEM-encoded cluster CA certificate for k8s API."
  sensitive   = true
  default     = ""
}

# ── Module-level tuning (non-sensitive defaults) ────────────────────────
variable "vault_namespace" {
  type        = string
  description = "Kubernetes namespace for HashiCorp Vault (or Infisical self-hosted)."
  default     = "vault"
}

variable "vault_replicas" {
  type        = number
  description = "Number of Vault pods. For personal env: 1. For prod: 3 (HA)."
  default     = 1
}

variable "unleash_namespace" {
  type        = string
  description = "Kubernetes namespace for Unleash feature flag service."
  default     = "unleash"
}

variable "unleash_replicas" {
  type        = number
  description = "Number of Unleash replicas."
  default     = 1
}
