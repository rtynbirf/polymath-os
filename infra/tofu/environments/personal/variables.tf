# infra/tofu/environments/personal/variables.tf
#
# Environment-specific variable declarations.
# Real values come from SOPS-decrypted secrets.sops.yaml (via -var-file).
# Personal env inherits the same variable CONTRACT as root tofu/variables.tf,
# but each environment is its own runnable root module → must re-declare.

variable "environment" {
  type    = string
  default = "personal"
}

variable "domain" {
  type    = string
  default = "polymath.example.com"
}

# ── Sensitive — come from secrets.sops.yaml ─────────────────────────────
variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

variable "hetzner_token" {
  type      = string
  sensitive = true
}

variable "hetzner_dns_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "ssh_public_key_primary" {
  type      = string
  sensitive = true
  description = "SSH public key for VPS root access. Pasted from ~/.ssh/id_ed25519.pub."
}

# ── k8s creds (generated on first k3s install on the VPS) ───────────────
variable "k8s_host" {
  type    = string
  default = "https://127.0.0.1:6443"
}

variable "k8s_client_cert" {
  type      = string
  sensitive = true
  default   = ""
}

variable "k8s_client_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "k8s_cluster_ca_cert" {
  type      = string
  sensitive = true
  default   = ""
}

# ── Module tuning ───────────────────────────────────────────────────────
variable "vault_namespace" {
  type    = string
  default = "vault"
}

variable "vault_replicas" {
  type    = number
  default = 1
}

variable "unleash_namespace" {
  type    = string
  default = "unleash"
}

variable "unleash_replicas" {
  type    = number
  default = 1
}
