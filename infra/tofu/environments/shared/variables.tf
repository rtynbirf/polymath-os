# infra/tofu/environments/shared/variables.tf

variable "aws_region" {
  type        = string
  default     = "eu-central-1"
  description = "AWS region for tfstate bucket + DynamoDB lock table. Pinned (ADR-0008 philosophy)."
}

variable "tfstate_bucket" {
  type        = string
  default     = "polymath-os-tfstate"
  description = "Globally unique S3 bucket name. Must be free in entire S3 namespace."
}

variable "tfstate_lock_table" {
  type        = string
  default     = "polymath-os-tfstate-lock"
  description = "DynamoDB table name for tfstate locking."
}

variable "github_org" {
  type        = string
  default     = "USER"
  description = "GitHub org/owner of the repo. Used in OIDC trust condition."
}

variable "github_repo" {
  type        = string
  default     = "polymath-os"
  description = "GitHub repo name. Used in OIDC trust condition."
}
