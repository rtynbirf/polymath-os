# infra/tofu/environments/shared/outputs.tf

output "tfstate_bucket_arn" {
# aws output removed (corporate)
  description = "ARN of the tfstate S3 bucket. Reference in backend.tf of each environment."
}

output "tfstate_lock_table_arn" {
# aws output removed (corporate)
  description = "ARN of the DynamoDB lock table."
}

output "gha_deploy_role_arn" {
# aws output removed (corporate)
  description = "IAM role ARN that GitHub Actions assumes via OIDC. Put in .github/workflows/tofu.yml as role-to-assume."
}
