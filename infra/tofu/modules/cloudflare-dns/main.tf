# infra/tofu/modules/cloudflare-dns/main.tf
#
# Module: управляет DNS-записями в Cloudflare (Tier 2 per ADR-0002).
# Создаёт A/AAAA/CNAME/MX records из переменной `records` (list of objects).
#
# Reusable: НЕТ environment-specific values внутри модуля.
# Замена (per Sovereignty Registry): bind9 self-hosted / Bunny CDN.
# Offline fallback: /etc/hosts (manual).
#
# Per ADR-0002 §Tier 2: Cloudflare — rented service. Если уйдёт — модуль
# заменяется на hetznerdns equivalent; только `source` провайдера меняется.

terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

# Zone lookup по домену apex. Не передаём zone_id в модуль — передаём domain,
# это лучше для reuse: caller не обязан знать Cloudflare internals.
data "cloudflare_zones" "this" {
  filter {
    name   = var.domain
    status = "active"
    paused = false
  }
}

locals {
  zone_id = data.cloudflare_zones.this.zones[0].id
}

# Universal record creator: один ресурс `cloudflare_record` создаёт
# A / AAAA / CNAME / MX в зависимости от атрибута `type` в var.records.
# Это уменьшает дублирование (DRY) против отдельных resource per type.
resource "cloudflare_record" "this" {
  for_each = { for r in var.records : r.name => r }

  zone_id = local.zone_id
  name    = each.value.name
  type    = each.value.type
  value   = each.value.value
  ttl     = each.value.ttl
  proxied = each.value.proxied

  # MX records требуют priority.
  priority = each.value.type == "MX" ? each.value.priority : null

  # AAAA records — IPv6.
  # A — IPv4.
  # CNAME — hostname (string).
  # MX — hostname (string) + priority.

  lifecycle {
    # Не удалять запись автоматически при changes из web UI — flag для safety.
    # Если запись modified externally — OpenTofu вернёт её обратно.
    prevent_destroy = false # personal env — allow destroy via explicit `tofu destroy`
  }
}
