# infra/tofu/modules/vault-cluster/variables.tf

variable "namespace" {
  type        = string
  description = "Kubernetes namespace where Vault chart will be installed."
  default     = "vault"
}

variable "replicas" {
  type        = number
  description = "Number of Vault server replicas. 1 = standalone dev mode. 3 = HA with Raft."
  default     = 1
}

variable "storage" {
  type        = string
  description = "PVC size for Vault integrated storage (Raft). Default: 10Gi for personal env."
  default     = "10Gi"
}

variable "storage_class" {
  type        = string
  description = "StorageClass for Vault PVC. On k3s: 'local-path' (default)."
  default     = "local-path"
}

variable "dev_mode" {
  type        = bool
  description = "If true — run in dev mode (no unseal needed, in-memory storage). ONLY personal env."
  default     = true
}

variable "helm_chart_version" {
  type        = string
  description = "HashiCorp Vault Helm chart version. Pinned per ADR-0008 (MCP version-pin, applied here for infra)."
  default     = "0.27.0"
}

variable "resources_memory_request" {
  type        = string
  description = "Memory request for Vault pods."
  default     = "256Mi"
}

variable "resources_cpu_request" {
  type        = string
  description = "CPU request for Vault pods."
  default     = "100m"
}
