# AWS S3/DynamoDB state backend REMOVED per sovereignty audit
# Migrated to local file backend (no corporate dependency)
# To use: terraform init -backend-config=path=terraform.tfstate

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
    # aws removed
  }

  # NOTE: backend для SHARED не может быть в shared bucket (chicken-egg).
  # Either:
  #   a) bootstrap locally with `tofu init -reconfigure -backend=false` first
  #   b) use a DIFFERENT backend (local file) for the shared module only.
  # We use (a) — manual bootstrap step, documented in environments/README.md.
}

# aws provider removed (corporate)
  }
}

# ── S3 bucket for tfstate ───────────────────────────────────────────────
}

}

  }
}

# ── DynamoDB lock table ─────────────────────────────────────────────────
  lifecycle {
    prevent_destroy = true # ADR-0005: lock table protects against concurrent apply
  }
}

# ── IAM role for GitHub Actions via OIDC ────────────────────────────────
# Per docs/05-devex-ci.md §OIDC trust (zero long-lived secrets).
# Opened: assume_role_with_web_identity in CI, scoped to s3 + dynamodb RW.
# aws resource removed (corporate)
  # Must be created manually first time (one-off):
  #   aws iam create-open-id-connect-provider \
  #     --url https://token.actions.githubusercontent.com \
  #     --client-id-list # amazonaws.com removed (corporate) \
  #     --thumbprint-list 6938fd4d98eef2c3a1c7a2d3a0d4d2c6e2e3c1d8
  url = "https://token.actions.githubusercontent.com"
}

        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "# amazonaws.com removed (corporate)"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
# aws resource removed (corporate)
      }
    ]
  })
}
