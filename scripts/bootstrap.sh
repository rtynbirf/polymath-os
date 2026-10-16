#!/usr/bin/env bash
# scripts/bootstrap.sh — Polymath OS one-command setup
#
# Запускается на чистой машине (macOS или Linux). После выполнения:
#   - установлен Nix (Determinate Systems installer, рекомендуемый с 2024)
#   - установлены direnv + nix-direnv (через `nix profile install`)
#   - установлен chezmoi (для dotfiles, см. ADR-0006 self-bootstrap)
#   - dev-shell собран через `nix develop --command true` (первый прогон — минуты)
#   - зависимости pnpm установлены (`pnpm install`)
#   - `make verify` выполнен (open-source contract, см. README.md)
#
# Idempotent: повторный запуск пропускает уже установленное.
# Error handling: `set -euo pipefail` + trap ERR с указанием строки.
#
# См.:
#   - flake.nix — список инструментов Tier 1+2
#   - docs/05-devex-ci.md — Layer 4 детали
#   - docs/adr/0002-sovereignty-registry.md — Tier 1+2 + offline fallbacks
#   - docs/adr/0006-falsifiable-self-properties.md — self-bootstrap witness

set -euo pipefail

# ── Logging helpers ────────────────────────────────────────────────────────
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
RESET=$'\033[0m'

log()   { echo "${GREEN}[bootstrap]${RESET} $*"; }
info()  { echo "${BLUE}[bootstrap]${RESET} $*"; }
warn()  { echo "${YELLOW}[bootstrap]${RESET} $*" >&2; }
fail()  { echo "${RED}[bootstrap ERROR]${RESET} $*" >&2; exit 1; }

# Trap any error and report the failing line. Useful for debugging on a
# new machine where stack traces aren't immediately visible.
err_trap() {
  local exit_code=$?
  local line_no=$1
  echo "${RED}[bootstrap ERROR]${RESET} Line ${line_no}: command failed with exit ${exit_code}." >&2
  echo "  Check logs above. If Nix just installed, open a NEW shell and re-run." >&2
}
trap 'err_trap ${LINENO}' ERR

# ── Repo root detection (works from any CWD) ───────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
log "Working in: $REPO_ROOT"

# ── Platform detection ─────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      fail "Unsupported OS: $OS (only macOS and Linux supported)" ;;
esac
case "$ARCH" in
  x86_64|arm64|aarch64) : ;;
  *) fail "Unsupported architecture: $ARCH" ;;
esac
log "Detected: $PLATFORM / $ARCH"

# ── Helper: ensure a command is in PATH ─────────────────────────────────────
have() { command -v "$1" >/dev/null 2>&1; }

# ── 1. Install Nix (Determinate Systems installer, 2024+) ─────────────────
# Modern multi-user installer. Replaces the legacy `curl https://nixos.org/nix/install`.
# See: https://github.com/DeterminateSystems/nix-installer
if have nix; then
  log "Nix already installed: $(nix --version 2>&1 | head -n1)"
else
  log "Installing Nix via Determinate Systems installer (no-confirm)..."
  # Need curl/wget. Try curl first, fallback to wget.
  if have curl; then
    curl -fsSL https://install.determinate.systems/nix | sh -s -- install --no-confirm
  elif have wget; then
    wget -qO- https://install.determinate.systems/nix | sh -s -- install --no-confirm
  else
    fail "Need curl or wget to download Nix installer. Install one and re-run."
  fi

  # Source Nix profile so `nix` is in PATH for the rest of this script.
  # The Determinate Systems installer writes to /nix/var/nix/profiles/default/
  # on Linux, and /nix/var/determinate-nix/profiles/default/ on newer versions.
  NIX_PROFILE_PATHS=(
    "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
    "/nix/var/determinate-nix/profiles/default/etc/profile.d/nix-daemon.sh"
    "$HOME/.nix-profile/etc/profile.d/nix.sh"
  )
  for profile in "${NIX_PROFILE_PATHS[@]}"; do
    if [ -f "$profile" ]; then
      # shellcheck disable=SC1090
      . "$profile"
      log "Sourced Nix profile: $profile"
      break
    fi
  done

  have nix || fail "Nix installed but 'nix' not in PATH. Open a NEW shell and re-run bootstrap."
fi

# ── 2. Install direnv + nix-direnv (if missing) ───────────────────────────
# direnv needs to be on the SYSTEM PATH (outside nix develop) because it
# triggers `use flake` from .envrc when you `cd` into the repo, BEFORE
# the nix dev-shell is active.
if have direnv; then
  log "direnv already installed: $(direnv --version 2>&1 | head -n1)"
else
  log "Installing direnv + nix-direnv via 'nix profile install'..."
  nix profile install nixpkgs#direnv nixpkgs#nix-direnv
  warn "Add 'eval \"\$(direnv hook bash)\"' (or zsh/fish) to your shell rc."
  warn "See: https://direnv.net/docs/hook.html"
fi

# ── 3. Install chezmoi (if missing) ────────────────────────────────────────
# Used for dotfiles (ADR-0006 self-bootstrap). `chezmoi init --apply <repo>`
# on a new machine. Sovereignty Registry Tier 2 replacement target.
if have chezmoi; then
  log "chezmoi already installed: $(chezmoi --version 2>&1 | head -n1)"
else
  log "Installing chezmoi via 'nix profile install'..."
  nix profile install nixpkgs#chezmoi
fi

# ── 4. Build dev-shell via `nix develop --command true` ────────────────────
# First run downloads+builds all devShell inputs (can take 5-30 minutes
# depending on network/CPU). Subsequent runs hit the nix store cache.
# This populates /nix/store with everything from flake.nix buildInputs.
log "Building dev-shell (first run may take minutes)..."
nix develop --command true
log "dev-shell ready. Run 'nix develop' or 'direnv allow' to enter it."

# ── 5. pnpm install ─────────────────────────────────────────────────────────
# pnpm comes from the nix dev-shell. To use it here (without entering
# the shell), invoke through `nix develop --command`.
if have pnpm; then
  log "pnpm in PATH. Installing dependencies (frozen-lockfile, fallback to install)..."
  pnpm install --frozen-lockfile || pnpm install
elif have nix; then
  log "pnpm not in PATH, running through nix develop..."
  nix develop --command pnpm install --frozen-lockfile || \
    nix develop --command pnpm install
else
  warn "Neither pnpm nor nix available. Skipping pnpm install. Run 'nix develop' first."
fi

# ── 6. make verify (the open-source contract) ──────────────────────────────
# Run inside nix develop so Python 3.11 (from flake.nix) is used, not the
# system Python (which may be missing on a truly clean macOS).
log "Running 'make verify' (12 verifiable claims, see README.md)..."
if have make; then
  if have nix; then
    nix develop --command make verify
  else
    make verify
  fi
else
  warn "make not available. Run 'nix develop --command make verify' manually."
fi

# ── Done. Next steps. ───────────────────────────────────────────────────────
echo ""
echo "${GREEN}════════════════════════════════════════════════════════════${RESET}"
echo "${GREEN}  ✓ Polymath OS bootstrap complete.${RESET}"
echo "${GREEN}════════════════════════════════════════════════════════════${RESET}"
echo ""
echo "  Next steps:"
echo "    1. Add direnv hook to your shell rc (~/.bashrc or ~/.zshrc):"
echo "         eval \"\$(direnv hook bash)\"   # or zsh"
echo "    2. cd into repo and allow direnv (one-time):"
echo "         cd $REPO_ROOT && direnv allow"
echo "    3. Develop:"
echo "         make dev        # tilt up (hot-reload)"
echo "         make ci-local   # act reproduces CI locally"
echo ""
echo "  Dotfiles: chezmoi init --apply <your-dotfiles-repo>"
echo ""
