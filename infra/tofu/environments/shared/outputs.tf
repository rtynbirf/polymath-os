# infra/tofu/environments/shared/outputs.tf
#
# 2026-11-05, рой: outputs tfstate_bucket_arn, tfstate_lock_table_arn,
# gha_deploy_role_arn сняты вместе с aws-ресурсами (де-AWS-операция,
# оборвавшаяся в 0767fe1) — их value ссылался на вырезанные ресурсы.
# Возврат или замена (локальные эквиваленты) — по замыслу владельца;
# дооперационный вид — история git.
