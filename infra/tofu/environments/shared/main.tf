# infra/tofu/environments/shared/main.tf
#
# Shared infrastructure — инвариантная часть для ВСЕХ environments.
# Это S3 backend bucket + DynamoDB lock table. Создаётся ОДИН раз за аккаунт,
# до того как создать personal/staging/prod environments (chicken-egg).
#
# Per ADR-0005 (separate rollback targets): if you destroy this,
# ALL environments' state is lost. Use `prevent_destroy = true` lifecycle.
# Per ADR-0002 §Tier 2: AWS S3 + DynamoDB — rented services, replaceable
# (MinIO self-hosted + etcd distributed lock as alternative).

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: backend для SHARED не может быть в shared bucket (chicken-egg).
  # Either:
  #   a) bootstrap locally with `tofu init -reconfigure -backend=false` first
  #   b) use a DIFFERENT backend (local file) for the shared module only.
  # We use (a) — manual bootstrap step, documented in environments/README.md.
}

provider "aws" {
  region = var.aws_region

  # OIDC trust for GitHub Actions — short-lived creds, no static keys.
  # Locally: use ~/.aws/credentials or `aws sso login`.
  default_tags {
    tags = {
      managed-by = "opentofu"
      env        = "shared"
      repo       = "polymath-os"
    }
  }
}

# ── S3 bucket for tfstate ───────────────────────────────────────────────
resource "aws_s3_bucket" "tfstate" {
  bucket = var.tfstate_bucket

  # ADR-0005: prevent destroy — state is critical, never auto-delete.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"   # required for tfstate rollback (ADR-0005 §RPO)
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls     = true
  restrict_public_buckets = true
}

# ── DynamoDB lock table ─────────────────────────────────────────────────
resource "aws_dynamodb_table" "tfstate_lock" {
  name         = var.tfstate_lock_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true   # ADR-0005: lock table protects against concurrent apply
  }
}

# ── IAM role for GitHub Actions via OIDC ────────────────────────────────
# Per docs/05-devex-ci.md §OIDC trust (zero long-lived secrets).
# Opened: assume_role_with_web_identity in CI, scoped to s3 + dynamodb RW.
data "aws_iam_openid_connect_provider" "github" {
  # Must be created manually first time (one-off):
  #   aws iam create-open-id-connect-provider \
  #     --url https://token.actions.githubusercontent.com \
  #     --client-id-list sts.amazonaws.com \
  #     --thumbprint-list 6938fd4d98eef2c3a1c7a2d3a0d4d2c6e2e3c1d8
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "gha_deploy" {
  name = "polymath-gha-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "gha_deploy" {
  name = "polymath-gha-deploy-policy"
  role = aws_iam_role.gha_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.tfstate.arn,
          "${aws_s3_bucket.tfstate.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.tfstate_lock.arn
      }
    ]
  })
}
