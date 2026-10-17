# infra/tofu/outputs.tf — root-level output contract
#
# Эти outputs — ОБРАЗЕЦ контракта «что окружение должно произвести».
# Фактические значения возвращаются из environments/<env>/outputs.tf,
# который ссылается на module blocks в environments/<env>/main.tf.
#
# Корень `infra/tofu/` не runnable напрямую: module blocks живут в
# environments/<env>/. Запуск: `cd environments/personal && tofu apply`.
# См. environments/README.md §How to use.
#
# Здесь — только outputs, не требующие module-block на верхнем уровне.

output "cluster_endpoint" {
  value       = var.k8s_host
  description = "k8s API server endpoint (k3s self-hosted)."
}

# Остальные outputs см. в environments/<env>/outputs.tf:
#   - dns_records       ← module.cloudflare_dns.fqdns
#   - vault_address     ← module.vault.service_address
#   - unleash_address   ← module.unleash.dashboard_url
#   - vault_init_required ← module.vault.init_required
