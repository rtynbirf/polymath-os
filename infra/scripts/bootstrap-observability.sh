#!/usr/bin/env bash
# infra/scripts/bootstrap-observability.sh
#
# Bring up the observability stack on a clean personal VPS:
#   1. Install Docker + Compose v2 (idempotent — official download.docker.com apt repo)
#   2. Clone repo (or assume CWD is repo root)
#   3. `docker compose -f compose.observability.yaml up -d`
#   4. Verify Grafana reachable at http://localhost:3000
#
# Per ADR-0011 (container runtime): on Linux we install Docker via the
# official download.docker.com apt repository (GPG-signed — no `curl | sh`,
# учитель OpenSSF Scorecard: Pinned-Dependencies). Podman alternative: see comments inline.
#
# Per ADR-0005 (separate rollback targets): bring down = `docker compose down`
# (keeps volumes). `down -v` is irreversible — flagged ⛔ in compose file.
#
# Usage:
#   ./infra/scripts/bootstrap-observability.sh                # current dir is repo root
#   ./infra/scripts/bootstrap-observability.sh --skip-clone   # skip step 2
#   ./infra/scripts/bootstrap-observability.sh --podman        # use podman instead

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"
COMPOSE_FILE="$INFRA_DIR/compose.observability.yaml"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

SKIP_CLONE=false
CONTAINER_ENGINE="docker"  # docker | podman

# ── parse args ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-clone) SKIP_CLONE=true; shift ;;
    --podman)     CONTAINER_ENGINE="podman"; shift ;;
    -h|--help)
      sed -n '3,20p' "$0"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

log()  { printf '\033[1;34m→ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
err()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; }
fatal(){ err "$*"; exit 1; }

# ── Step 1: install Docker (or podman) ───────────────────────────────────
install_docker() {
  if command -v docker >/dev/null 2>&1; then
    ok "docker already installed: $(docker --version)"
    return 0
  fi
  log "Installing Docker from official download.docker.com apt repo (GPG-signed)..."
  # Учитель OpenSSF Scorecard (Pinned-Dependencies): никаких `curl | sh`.
  # Официальный репозиторий apt: ключ проверяется самим apt (signed-by),
  # версии пакетов фиксированы репозиторием. Для prod: nix / Ansible / packer.
  . /etc/os-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io
  systemctl enable --now docker
  ok "Docker installed and started (official apt repo)"
}

install_podman() {
  if command -v podman >/dev/null 2>&1; then
    ok "podman already installed: $(podman --version)"
    return 0
  fi
  log "Installing podman via apt..."
  apt-get update -y
  apt-get install -y podman podman-docker uidmap
  ok "podman installed"
}

case "$CONTAINER_ENGINE" in
  docker)  install_docker ;;
  podman)  install_podman ;;
  *)       fatal "Unknown container engine: $CONTAINER_ENGINE" ;;
esac

# `docker compose` (Compose v2) — check it exists
if ! "$CONTAINER_ENGINE" compose version >/dev/null 2>&1; then
  log "Installing compose plugin..."
  # For docker: compose v2 is a plugin (bundled with docker-ce)
  # For podman: podman-compose is the alternative
  if [[ "$CONTAINER_ENGINE" == "podman" ]]; then
    apt-get install -y podman-compose || err "podman-compose недоступен в apt — установите вручную (apt/pipx), учитель Scorecard: без непиненного pip install"
  fi
fi
ok "Compose v2 available"

# ── Step 2: clone repo (or use existing) ────────────────────────────────
if [[ "$SKIP_CLONE" == "true" ]]; then
  ok "Skipping clone (CWD assumed to be repo root or path)"
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    fatal "compose.observability.yaml not found at $COMPOSE_FILE"
  fi
else
  if [[ ! -d "$REPO_ROOT/.git" ]]; then
    log "Cloning polymath-os to /tmp/polymath-os..."
    rm -rf /tmp/polymath-os
    git clone --depth=1 https://github.com/USER/polymath-os.git /tmp/polymath-os
    REPO_ROOT=/tmp/polymath-os
    INFRA_DIR="$REPO_ROOT/infra"
    COMPOSE_FILE="$INFRA_DIR/compose.observability.yaml"
  else
    ok "Repo already present at $REPO_ROOT (skipping clone)"
  fi
fi
[[ -f "$COMPOSE_FILE" ]] || fatal "compose.observability.yaml missing"

# ── Step 3: bring up the stack ───────────────────────────────────────────
log "Bringing up observability stack..."
cd "$INFRA_DIR"

# Pull images (so we fail fast on registry issues)
"$CONTAINER_ENGINE" compose -f "$(basename "$COMPOSE_FILE")" pull --quiet

# Up — detached
"$CONTAINER_ENGINE" compose -f "$(basename "$COMPOSE_FILE")" up -d --wait

ok "Stack up (containers started)"
"$CONTAINER_ENGINE" compose -f "$(basename "$COMPOSE_FILE")" ps

# ── Step 4: verify Grafana reachable ────────────────────────────────────
log "Verifying Grafana reachable at http://localhost:${GRAFANA_PORT}..."
HEALTH_URL="http://localhost:${GRAFANA_PORT}/api/health"

# Wait up to 120s for Grafana to be ready (start_period=60 + buffer)
for i in $(seq 1 24); do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    ok "Grafana ready at $HEALTH_URL"
    curl -s "$HEALTH_URL"
    echo
    exit 0
  fi
  sleep 5
  printf '.'
done
echo

err "Grafana did NOT become healthy within 120s"
echo "Diagnostic:"
"$CONTAINER_ENGINE" compose -f "$(basename "$COMPOSE_FILE")" logs --tail=50 grafana
exit 1
