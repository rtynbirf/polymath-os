# infra/tofu/environments/personal/outputs.tf
#
# Personal environment outputs. Per ADR-0009 (default-deny publish):
# no sensitive values exposed. Only addresses + flags.

output "cluster_endpoint" {
  value       = var.k8s_host
  description = "k3s API server endpoint."
}

output "dns_records" {
  value       = module.cloudflare_dns.fqdns
  description = "Fully-qualified DNS records created by the cloudflare-dns module."
}

output "vault_address" {
  value       = module.vault.service_address
  description = "Vault service address (cluster-local)."
}

output "unleash_address" {
  value       = module.unleash.dashboard_url
  description = "Unleash admin dashboard URL."
}

output "vault_init_required" {
  value       = module.vault.init_required
  description = "True if Vault release is fresh (needs operator init + unseal)."
}

output "hetzner_ipv4" {
  value       = module.hetzner_vps.ipv4
  description = "Public IPv4 of the personal VPS."
}

output "hetzner_ipv6" {
  value       = module.hetzner_vps.ipv6
  description = "Public IPv6 of the personal VPS."
}
