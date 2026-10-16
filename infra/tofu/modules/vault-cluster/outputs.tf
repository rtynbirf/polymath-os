# infra/tofu/modules/vault-cluster/outputs.tf

output "service_address" {
  value       = "https://${data.kubernetes_service.vault.metadata[0].name}.${data.kubernetes_service.vault.metadata[0].namespace}.svc.cluster.local:8200"
  description = "Cluster-local Vault API address. Reachable from inside k8s only (per ADR-0009 default-deny)."
}

output "init_required" {
  value       = local.init_required
  description = "True when Vault release is not yet Deployed (needs operator init+unseal). Falsifiable: matches `vault status | grep Initialized`."
}

output "namespace" {
  value       = kubernetes_namespace.this.metadata[0].name
  description = "Kubernetes namespace where Vault lives."
}
