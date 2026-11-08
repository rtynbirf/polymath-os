# infra/tofu/modules/unleash/outputs.tf

output "service_address" {
  value       = local.service_address
  description = "Cluster-local Unleash API URL. Used by SDKs inside k8s."
}

output "dashboard_url" {
  value       = local.dashboard_url
  description = "External dashboard URL. For personal env: use `kubectl port-forward -n unleash svc/unleash 4242:4242`."
}

output "namespace" {
  value       = kubernetes_namespace.this.metadata[0].name
  description = "Kubernetes namespace where Unleash lives."
}
