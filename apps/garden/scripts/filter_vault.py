#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter vault/60-permanent/ → apps/garden/content/, keeping ONLY notes with
`publish: true` in YAML frontmatter. Used by .github/workflows/publish-garden.yml.

ADR-0009 default-deny: a note without `publish: true` does NOT get copied.
The filter is structural: it cannot leak a note the author never opted in.

Usage:
    python3 apps/garden/scripts/filter_vault.py \
        --vault vault/60-permanent \
        --out apps/garden/content \
        [--canary-marker __CANARY__do_not_publish__] \
        [--canary-path vault/90-meta/canary-secret.md]

Exit codes:
    0 — OK, filtered subset written to --out, no canary leak detected.
    1 — frontmatter parse error in a candidate note.
    2 — canary marker found in output (default-deny violated — DEPLOY MUST BLOCK).
    3 — I/O error (read/write).

Dependencies: Python 3.10+ standard library only (yaml parsed by hand —
no PyYAML dependency, keeps the filter sovereign per ADR-0002).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
KEY_VALUE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*?)\s*$")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Minimal YAML-subset parser for `key: value` frontmatter (no nesting).
    Returns (dict, body). If no frontmatter, returns ({}, text).

    NB: handles inline `# comment` after a value (YAML rule: `#` starts a
    comment only when at start of line or preceded by whitespace). Does NOT
    handle `#` inside quoted strings — but for a default-deny filter where
    we control the templates, this is acceptable.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        kv = KEY_VALUE_RE.match(line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2)
        # Strip inline YAML comment: `#` at start or after whitespace.
        for i, c in enumerate(val):
            if c == "#" and (i == 0 or val[i - 1].isspace()):
                val = val[:i].rstrip()
                break
        # strip surrounding quotes if present
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
    body = text[m.end():]
    return fm, body


def note_is_published(fm: dict[str, str]) -> bool:
    """ADR-0009: only explicit `publish: true` (string "true") is published.
    Anything else (false, missing, "yes"...) — private.
    """
    return fm.get("publish", "").lower() == "true"


def iter_vault_notes(vault_dir: Path) -> list[Path]:
    """All markdown files under vault_dir (recursive)."""
    return sorted(p for p in vault_dir.rglob("*.md") if p.is_file())


def copy_note(src: Path, vault_root: Path, out_root: Path) -> Path:
    """Copy src → out_root preserving relative-to-vault-root path."""
    rel = src.relative_to(vault_root)
    dst = out_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def check_canary(out_root: Path, marker: str) -> list[Path]:
    """Walk out_root, return list of files containing the canary marker."""
    leaked: list[Path] = []
    for p in out_root.rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if marker in text:
            leaked.append(p)
    return leaked


def main() -> int:
    ap = argparse.ArgumentParser(description="ADR-0009 default-deny vault filter")
    ap.add_argument("--vault", required=True, type=Path,
                    help="Source vault dir (e.g. vault/60-permanent)")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output dir (e.g. apps/garden/content)")
    ap.add_argument("--canary-marker", default="__CANARY__do_not_publish__",
                    help="String that must NEVER appear in --out")
    ap.add_argument("--canary-path", type=Path, default=None,
                    help="Path of the canary note in --vault (not required, "
                         "but logged for visibility)")
    args = ap.parse_args()

    vault: Path = args.vault.resolve()
    out: Path = args.out.resolve()

    if not vault.is_dir():
        print(f"ERROR: vault dir does not exist: {vault}", file=sys.stderr)
        return 3

    # Clean output
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    included: list[str] = []
    excluded: list[str] = []
    errors: list[str] = []

    for note in iter_vault_notes(vault):
        try:
            text = note.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(f"{note}: read error {e}")
            continue
        fm, _ = parse_frontmatter(text)
        if note_is_published(fm):
            dst = copy_note(note, vault, out)
            included.append(str(dst.relative_to(out)))
        else:
            excluded.append(str(note.relative_to(vault)))

    print(f"Filtered vault: {vault}")
    print(f"  → output: {out}")
    print(f"  → included ({len(included)}):")
    for n in included:
        print(f"      ✓ {n}")
    print(f"  → excluded ({len(excluded)}):")
    for n in excluded:
        print(f"      ✗ {n}")
    if args.canary_path:
        cp = args.canary_path.resolve()
        print(f"  → canary note: {cp} ({'EXCLUDED' if cp in [n.resolve() for n in [vault / x for x in excluded]] else 'not found'})")

    if errors:
        print("ERRORS (frontmatter / I/O):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    # Negative test: canary marker must NOT appear anywhere in --out.
    leaked = check_canary(out, args.canary_marker)
    if leaked:
        print()
        print("⛔ CANARY LEAK DETECTED — default-deny violated!", file=sys.stderr)
        print(f"  marker `{args.canary_marker}` found in:", file=sys.stderr)
        for p in leaked:
            print(f"    {p}", file=sys.stderr)
        print("Deploy MUST be blocked.", file=sys.stderr)
        return 2

    print()
    print("✓ default-deny check passed — canary not in output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
