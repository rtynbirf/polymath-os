# infra/tofu/environments/personal/backend.tf
#
# S3 backend for the personal environment. Concrete bucket/table values
# come from `tofu init -backend-config=backend.tfvars` (which is SOPS-encrypted).
# Until then, run `tofu init -backend=false` for local validate.

terraform {
  backend "s3" {
    bucket         = "polymath-os-tfstate" # placeholders — replace from shared/ outputs
    key            = "environments/personal.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "polymath-os-tfstate-lock"
    encrypt        = true

    # OIDC role assumed at runtime via AWS SDK — see GitHub workflow.
  }
}
