# infra/tofu/modules/hetzner-server/outputs.tf

output "ipv4" {
  value       = hcloud_server.this.ipv4_address
  description = "Public IPv4 address of the server."
}

output "ipv6" {
  value       = hcloud_server.this.ipv6_address
  description = "Public IPv6 address (slash-64) of the server."
}

output "server_id" {
  value       = hcloud_server.this.id
  description = "Hetzner server numeric ID. Useful for upstream/dependent resources (volumes, networks)."
}

output "firewall_id" {
  value       = hcloud_firewall.this.id
  description = "ID of the firewall attached to this server."
}
