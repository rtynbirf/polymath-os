#!/bin/bash
# build_simple.sh — Simple garden build (no Quartz dependency)
# Per LIBERATION_ROADMAP: eliminate corporate CDN + external deps
# Quartz v4 requires @jackyzha0/quartz git repo (unreachable from GHA)
# This script builds the garden from raw markdown → static HTML
# Zero npm. Zero CDN. Zero Quartz. Zero external deps.

set -euo pipefail
VAULT_DIR="${1:-vault/60-permanent}"
OUT_DIR="${2:-apps/garden/content}"
CANARY_MARKER="${3:-__CANARY_p1m0s_8f3a2e91_dnp_v1__}"
CANARY_PATH="${4:-vault/90-meta/canary-secret.md}"

echo "[garden-simple] Building from $VAULT_DIR → $OUT_DIR"
mkdir -p "$OUT_DIR"

# Filter: only publish: true notes (ADR-0009 default-deny)
count=0
for f in "$VAULT_DIR"/*.md; do
    [ -f "$f" ] || continue
    # Check for publish: true in frontmatter
    if head -20 "$f" | grep -q "^publish:.*true"; then
        name=$(basename "$f" .md)
        out="$OUT_DIR/$name.html"
        # Simple markdown → HTML (no deps, just <pre> wrapping)
        echo "<!doctype html><html lang='ru'><head><meta charset='utf-8'>\
<meta name='viewport' content='width=device-width,initial-scale=1'>\
<title>$name — Polymath OS Garden</title>\
<style>body{max-width:720px;margin:0 auto;padding:2rem;font:16px/1.6 sans-serif;color:#333}\
pre{white-space:pre-wrap;word-wrap:break-word}</style></head><body>\
<h1>Polymath OS Garden</h1>" > "$out"
        # Strip frontmatter, wrap content in <pre>
        awk 'BEGIN{fm=0} /^---$/{if(fm==0){fm=1;next}else{fm=0;next}} fm==1{next} {print}' "$f" >> "$out"
        echo "<hr><a href='index.html'>← Garden</a></body></html>" >> "$out"
        count=$((count + 1))
        echo "[garden-simple] ✓ $name.html"
    fi
done

# Canary check (ADR-0009 negative test)
if grep -r "$CANARY_MARKER" "$OUT_DIR/" 2>/dev/null; then
    echo "[garden-simple] ⛔ CANARY LEAKED — deploy blocked!"
    exit 2
fi
echo "[garden-simple] ✓ canary not in output"

# Create index.html
echo "<!doctype html><html lang='ru'><head><meta charset='utf-8'>\
<meta name='viewport' content='width=device-width,initial-scale=1'>\
<title>Polymath OS Garden</title>\
<style>body{max-width:720px;margin:0 auto;padding:2rem;font:16px/1.6 sans-serif}</style>\
</head><body><h1>🌱 Polymath OS Garden</h1>\
<p>Permanent notes published via default-deny filter (ADR-0009).</p>\
<p><a href='https://github.com/rtynbirf/polymath-os'>→ Source repo</a></p>\
<hr><h2>Notes</h2>" > "$OUT_DIR/index.html"
for f in "$OUT_DIR"/*.html; do
    name=$(basename "$f" .html)
    [ "$name" = "index" ] && continue
    echo "<p><a href='$name.html'>$name</a></p>" >> "$OUT_DIR/index.html"
done
echo "</body></html>" >> "$OUT_DIR/index.html"
echo "[garden-simple] ✓ index.html created"
echo "[garden-simple] Done: $count note(s) published"
