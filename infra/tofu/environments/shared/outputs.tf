# infra/tofu/environments/shared/outputs.tf

output "tfstate_bucket_arn" {
  value       = aws_s3_bucket.tfstate.arn
  description = "ARN of the tfstate S3 bucket. Reference in backend.tf of each environment."
}

output "tfstate_lock_table_arn" {
  value       = aws_dynamodb_table.tfstate_lock.arn
  description = "ARN of the DynamoDB lock table."
}

output "gha_deploy_role_arn" {
  value       = aws_iam_role.gha_deploy.arn
  description = "IAM role ARN that GitHub Actions assumes via OIDC. Put in .github/workflows/tofu.yml as role-to-assume."
}
