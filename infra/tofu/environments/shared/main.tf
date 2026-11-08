# AWS S3/DynamoDB state backend REMOVED per sovereignty audit
# Migrated to local file backend (no corporate dependency)
# To use: terraform init -backend-config=path=terraform.tfstate

# infra/tofu/environments/shared/main.tf
#
# Shared infrastructure — инвариантная часть для ВСЕХ environments.
# Исторически здесь жили: S3 bucket под tfstate, DynamoDB lock table,
# IAM role для GitHub Actions (OIDC) — всё aws, вырезано по sovereignty
# audit (де-AWS-операция оборвалась в 0767fe1 на полуслове).
#
# Per ADR-0005 (separate rollback targets): if you destroy this,
# ALL environments' state is lost. Use `prevent_destroy = true` lifecycle.
# Per ADR-0002 §Tier 2: AWS S3 + DynamoDB — rented services, replaceable
# (MinIO self-hosted + etcd distributed lock as alternative).

# 2026-11-05, рой: дочищено — обрывки aws-ресурсов сняты; содержательный
# замысел файла: локальный backend без корпоративной зависимости.
# Дооперационный вид — история git (коммиты до 0767fe1).
# Замысел замены (локальный state-сервер / MinIO / etcd) — за владельцем.

terraform {
  # required_providers: aws removed (corporate) — корпоративных провайдеров нет.

  # NOTE: backend для SHARED не может быть в общем bucket'е (chicken-egg).
  # Either:
  #   a) bootstrap locally with `tofu init -reconfigure -backend=false` first
  #   b) use a DIFFERENT backend (local file) for the shared module only.
  # We use (a) — manual bootstrap step, documented in environments/README.md.
}
