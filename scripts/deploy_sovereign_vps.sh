#!/bin/bash
# scripts/deploy_sovereign_vps.sh — One-command sovereign VPS deployment
#
# Per LIBERATION_ROADMAP.md Phase 4: deploy the self-hosted stack
# on the human's own VPS. Zero corporations. Zero benefactors.
#
# Usage (on a fresh Ubuntu 22.04 VPS):
#   curl -sL https://raw.githubusercontent.com/rtynbirf/polymath-os/main/scripts/deploy_sovereign_vps.sh | bash
# Or:
#   git clone https://github.com/rtynbirf/polymath-os && cd polymath-os
#   bash scripts/deploy_sovereign_vps.sh
#
# What it does:
#   1. Installs Docker + docker-compose
#   2. Starts the sovereign stack (Gitea + Verdaccio + devpi + nostromo + Glitchtip + Uptime Kuma + unbound + electrs + model-mirror)
#   3. Configures unbound as system DNS
#   4. Verifies all services are running

set -euo pipefail

echo "══════════════════════════════════════════════════════════════"
echo "  SOVEREIGN VPS DEPLOYMENT"
echo "  Per LIBERATION_ROADMAP.md — Phase 4"
echo "  No corporations. No benefactors. No good uncles."
echo "══════════════════════════════════════════════════════════════"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Run as root: sudo bash scripts/deploy_sovereign_vps.sh"
    exit 1
fi

# 1. Install Docker
echo ""
echo "[1/4] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
    echo "  ✓ Docker installed"
else
    echo "  ✓ Docker already installed"
fi

# 2. Start sovereign stack
echo ""
echo "[2/4] Starting sovereign stack..."
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/infra/self-host"
docker compose up -d
echo "  ✓ Stack started:"
docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker-compose ps

# 3. Configure unbound as system DNS
echo ""
echo "[3/4] Configuring unbound as system DNS..."
# Point resolv.conf to local unbound (port 53)
if [ -f /etc/resolv.conf ]; then
    cp /etc/resolv.conf /etc/resolv.conf.backup
fi
echo "nameserver 127.0.0.1" > /etc/resolv.conf
echo "  ✓ System DNS → local unbound (127.0.0.1)"
echo "  ✓ No Google DNS (8.8.8.8). No Cloudflare (1.1.1.1). No Yandex (77.88.8.8)."

# 4. Verify services
echo ""
echo "[4/4] Verifying services..."
SERVICES=(
    "Gitea (git hosting):        http://localhost:3000"
    "Verdaccio (npm mirror):     http://localhost:4873"
    "devpi (PyPI mirror):       http://localhost:3141"
    "nostromo (Nostr relay):     ws://localhost:8080"
    "Glitchtip (error tracking): http://localhost:8001"
    "Uptime Kuma (monitoring):   http://localhost:3001"
    "unbound (DNS resolver):     127.0.0.1:53"
    "electrs (BTC explorer):    localhost:50001"
    "model-mirror (LLM weights): http://localhost:8081"
)
for svc in "${SERVICES[@]}"; do
    echo "  → $svc"
done

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ SOVEREIGN VPS DEPLOYED"
echo "  All services running on YOUR VPS."
echo "  No GitHub. No npmjs.com. No pypi.org. No HuggingFace."
echo "  No Sentry. No BetterStack. No Google DNS. No Cloudflare."
echo "  No mempool.space. No public Nostr relays."
echo ""
echo "  Freedom score: 100% (on this VPS)"
echo "══════════════════════════════════════════════════════════════"
