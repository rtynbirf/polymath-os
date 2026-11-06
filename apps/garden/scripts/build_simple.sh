#!/bin/bash
# build_simple.sh — Simple garden build (no Quartz dependency).
#
# Since the Windows-fix round (2026-11-06) this script is a thin wrapper:
# the canonical zero-dep logic lives in build_simple.mjs (Node, stdlib only)
# so that `pnpm -r run build` works on every OS — Windows has no bash, but
# every pnpm/turbo environment has node. Argv contract unchanged:
#   build_simple.sh [vault_dir] [out_dir] [canary_marker] [canary_path]
# publish-garden.yml keeps calling this path (per ТЗ canary contract).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "$SCRIPT_DIR/build_simple.mjs" "$@"
