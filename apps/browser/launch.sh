#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINES_FILE="$SCRIPT_DIR/engines.txt"
BROWSER_SHELL="$SCRIPT_DIR/index.html"
ELECTRON_DIR="$SCRIPT_DIR/electron"

# ──────────────────────────────────────────────────────────────────────
# Mode dispatch. `launch.sh electron` → Electron desktop wrapper for
# decree-portal.html (real SQLite decrees via Node bridge). Anything else
# (or no arg) → default sovereign-browser behaviour below.
# ──────────────────────────────────────────────────────────────────────
if [ "$1" = "electron" ]; then
    echo "🌱 MODE: Electron desktop wrapper (decree-portal.html → real SQLite)"
    if [ ! -d "$ELECTRON_DIR" ]; then
        echo "  ✗ $ELECTRON_DIR missing — did the clone include apps/browser/electron/?"
        exit 1
    fi
    if ! command -v npm &>/dev/null; then
        echo "  ✗ npm not on PATH — install Node.js >= 20 first"
        exit 1
    fi
    if command -v electron &>/dev/null; then
        echo "  → electron detected on PATH (will be used by npm start)"
    else
        echo "  → electron not on PATH; npm install will fetch it (~200MB one-time)"
    fi
    echo "  → installing deps (silent)…"
    (cd "$ELECTRON_DIR" && npm install --silent) || {
        echo "  ✗ npm install failed"
        exit 1
    }
    echo "  → launching Electron app…"
    cd "$ELECTRON_DIR" && npm start
    exit 0
fi

# Default mode: sovereign browser shell (NetSurf / Servo / Ladybird / xdg-open).
echo "🌱 MODE: sovereign browser shell (use 'launch.sh electron' for desktop wrapper)"
[ ! -f "$ENGINES_FILE" ] && xdg-open "$BROWSER_SHELL" 2>/dev/null && exit 0
while IFS= read -r line; do
    line=$(echo "$line" | sed 's/#.*//' | xargs)
    [ -z "$line" ] && continue
    if command -v "$line" &>/dev/null || [ -x "$line" ]; then
        echo "🌱 $line"; "$line" "$BROWSER_SHELL"; exit 0
    fi
done < "$ENGINES_FILE"
echo "No sovereign engine. Install NetSurf/Servo/Ladybird."
xdg-open "$BROWSER_SHELL" 2>/dev/null
