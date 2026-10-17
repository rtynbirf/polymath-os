# infra/tofu/modules/hetzner-server/main.tf
#
# Module: создаёт Hetzner Cloud server с firewall (Tier 2 per ADR-0002).
# Замена: OVH / Scaleway / self-host on mini-PC. Offline fallback: local bare metal.
#
# Reusable: НЕТ environment-specific values внутри модуля.
# Per ADR-0002 §Tier 2 — VPS rented, replaceable by contract.

terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.0"
    }
  }
}

# ── SSH key upload (idempotent) ──────────────────────────────────────────
# SSH public keys передаются в модуль. Hetzner их зарегистрирует,
# затем сервер создастся с этими ключами на root.
resource "hcloud_ssh_key" "this" {
  for_each   = { for k in var.ssh_keys : k.name => k }
  name       = each.value.name
  public_key = each.value.public_key
}

# ── Firewall (default-deny inbound, allow 22/80/443 + ICMP) ───────────────
# Per ADR-0009 (default-deny philosophy — adapted for network here).
resource "hcloud_firewall" "this" {
  name = "fw-${var.name}"
  labels = merge(var.labels, {
    managed-by = "opentofu"
    module     = "hetzner-server"
  })

  # SSH — restricted to specified source IPs.
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_source_ips
  }

  # HTTP(S) — open to world.
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # ICMP (for ping / MTU discovery) — open to world.
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# ── Server itself ────────────────────────────────────────────────────────
resource "hcloud_server" "this" {
  name         = var.name
  server_type  = var.server_type
  image        = var.image
  location     = var.location
  ssh_keys     = [for k in hcloud_ssh_key.this : k.id]
  firewall_ids = [hcloud_firewall.this.id]
  labels = merge(var.labels, {
    managed-by  = "opentofu"
    module      = "hetzner-server"
    environment = var.labels.environment != "" ? var.labels.environment : "personal"
  })

  # ADR-0005 (separate rollback targets): server replacement on image change
  # is allowed — но state модуля (data) lives in volumes/DB, не на root disk.
  # Backup/restore — separate concern (RPO/RTO target per ADR-0005).
  # public_net block omitted — hcloud 1.70+ assigns ipv4+ipv6 by default;
  # use outputs.ipv4 (hcloud_server.this.ipv4_address) and .ipv6 to read.
}
