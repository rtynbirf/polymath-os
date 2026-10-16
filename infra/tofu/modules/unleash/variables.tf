# infra/tofu/modules/unleash/variables.tf

variable "namespace" {
  type        = string
  description = "Kubernetes namespace for Unleash."
  default     = "unleash"
}

variable "replicas" {
  type        = number
  description = "Number of Unleash replicas. 1 for personal. 2+ for prod."
  default     = 1
}

variable "helm_chart_version" {
  type        = string
  description = "Unleash Helm chart version. Pinned per ADR-0008 (version-pin philosophy, applied here for infra)."
  default     = "5.0.0"
}

variable "ingress_domain" {
  type        = string
  description = "External domain for Unleash dashboard. Ingress must be set up separately. For personal: port-forward."
  default     = "polymath.local"
}
