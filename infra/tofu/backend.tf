# infra/tofu/backend.tf — S3 backend with DynamoDB lock
#
# State lives in S3; DynamoDB table provides distributed lock.
# Concrete values (bucket, table, region, key prefix) come from
# environment-specific variables — see environments/<env>/backend.tfvars.
#
# Per ADR-0002 §Tier 1 (sovereign core): SOPS+age encrypts the real
# access credentials; the file `secrets.sops.yaml` is committed (encrypted),
# the age identity is NOT in git (root .gitignore: age-identity.txt).
#
# Per ADR-0011 (container runtime): nothing here assumes a specific runtime.

terraform {
  backend "s3" {
    # Все значения — placeholders. Реальные подставляются через backend config
    # `tofu init -backend-config=environments/<env>/backend.tfvars`.
    # См. environments/README.md §How to use.

    bucket         = "polymath-os-tfstate-PLACEHOLDER"
    key            = "tofu/PLACEHOLDER.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "polymath-os-tfstate-lock-PLACEHOLDER"
    encrypt        = true

    # OIDC role для GitHub Actions — short-lived, без long-lived access keys.
    # Локально используем static creds из SOPS-decrypted env (1Password CLI).
  }
}
