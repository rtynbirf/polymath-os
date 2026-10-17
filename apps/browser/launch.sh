#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINES_FILE="$SCRIPT_DIR/engines.txt"
BROWSER_SHELL="$SCRIPT_DIR/index.html"
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
