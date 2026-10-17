# infra/tofu/modules/cloudflare-dns/outputs.tf

output "fqdns" {
  value = [
    for r in cloudflare_record.this :
    r.type == "MX" ? "${r.priority} ${r.hostname}" : r.hostname
  ]
  description = "Fully-qualified hostnames of created records (with priority for MX)."
}

output "zone_id" {
  value       = local.zone_id
  description = "Cloudflare zone_id of var.domain. Useful for upstream modules / API calls."
}
