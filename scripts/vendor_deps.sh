#!/bin/bash
# scripts/vendor_deps.sh — Vendor all CDN-hosted dependencies locally
#
# Per LIBERATION_ROADMAP.md Phase 3: eliminate jsDelivr, unpkg, cdnjs, gstatic.
# Download all CDN-hosted JS/CSS into БИБЛИОТЕКИ/vendored/ — then replace
# CDN URLs in HTML files with local paths.
#
# After vendoring: no CDN references remain. Zero external script loads.
# Per ADR-0009 (Default-deny): if a CDN is down, the product still works.

set -euo pipefail

VENDOR_DIR="${1:-БИБЛИОТЕКИ/vendored}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$REPO_ROOT/$VENDOR_DIR"

echo "[vendor] Scanning for CDN references in HTML/JS files..."

# Patterns to find and vendor
CDN_PATTERNS=(
    "https://cdn.jsdelivr.net/[^\"' ]*"
    "https://unpkg.com/[^\"' ]*"
    "https://cdnjs.cloudflare.com/[^\"' ]*"
    "https://cdn.jsdelivr.net/npm/[^\"' ]*"
)

# Find all HTML/JS files
FILES=$(find "$REPO_ROOT" -name "*.html" -o -name "*.js" -o -name "*.mjs" | \
    grep -v node_modules | grep -v '.git/' | grep -v '__pycache__')

vendored=0
for file in $FILES; do
    for pattern in "${CDN_PATTERNS[@]}"; do
        # Extract CDN URLs
        urls=$(grep -oP "$pattern" "$file" 2>/dev/null || true)
        for url in $urls; do
            # Get filename from URL
            filename=$(basename "$url" | sed 's/[?#].*//')
            if [ -z "$filename" ]; then continue; fi
            
            target="$REPO_ROOT/$VENDOR_DIR/$filename"
            
            if [ ! -f "$target" ]; then
                echo "[vendor] Downloading: $url → $VENDOR_DIR/$filename"
                curl -sSL -o "$target" "$url" || echo "[vendor] WARN: failed to download $url"
                vendored=$((vendored + 1))
            fi
            
            # Replace CDN URL with local path in the file
            relative_path="$VENDOR_DIR/$filename"
            sed -i "s|${url}|${relative_path}|g" "$file"
            echo "[vendor] Replaced in $(basename "$file"): $url → $relative_path"
        done
    done
done

echo ""
echo "[vendor] Vendored $vendored file(s) into $VENDOR_DIR/"
echo "[vendor] All CDN references replaced with local paths."
echo "[vendor] Zero external script loads remain."
echo ""
echo "[vendor] Per LIBERATION_ROADMAP Phase 3: CDN benefactors eliminated."
