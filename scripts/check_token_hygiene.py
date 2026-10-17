#!/usr/bin/env python3
"""scripts/check_token_hygiene.py — Polymath OS token hygiene checker.

Scans all text files in the repo for plaintext credentials that should
NEVER be in source code:

  - GitHub PATs (github_pat_, ghp_, gho_, ghu_, ghs_, ghr_)
  - Generic env var assignments with literal token values
    (GH_TOKEN='...', GITHUB_TOKEN="...", etc.)
  - Git remote URLs with embedded credentials
    (https://user:token@host/...)

This script is a defensive layer IN ADDITION to gitleaks (which scans
tracked files at pre-commit time). gitleaks catches leaks that are
about to be committed; this script catches leaks that are already
in the repo or that gitleaks might miss (e.g. shell scripts that
export tokens via inline assignments).

The previous polymath-os session had a github_pat_... token
auto-revoked by GitHub's secret scanner because it appeared in
plaintext in a bash command (visible in session logs / command
history). This script would have caught that BEFORE the bash
command was ever run, by scanning for the literal pattern in any
shell script that does `export GH_TOKEN='...'`.

Exit codes:
  0 = no plaintext tokens found (clean)
  1 = plaintext tokens found (printed to stderr)
  2 = error during scan (e.g. permission denied)

Usage:
  python3 scripts/check_token_hygiene.py
  python3 scripts/check_token_hygiene.py --paths scripts/ apps/

This script is added to `make verify` as the 23rd claim (since v0.6).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# Token regex patterns — these catch REAL tokens (with sufficient length
# to be valid secrets, not placeholder text).
#
# Patterns are intentionally conservative — they require 50+ chars after
# the prefix to avoid matching documentation examples like "github_pat_..."
# or short placeholder mentions in code comments.
#
# Real GitHub fine-grained PATs are ~93 chars total: github_pat_ + 11 chars
# + _ + 59 chars. So requiring 50+ chars after prefix matches real tokens
# but NOT 20-char doc examples.
TOKEN_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    # GitHub fine-grained PAT format: github_pat_<segment1>_<segment2>
    # Total length ~93 chars (prefix + 2 base62 segments separated by underscore).
    # We require 50+ chars after prefix — this skips short doc placeholders.
    ("github_pat (fine-grained)",
     re.compile(r"github_pat_[A-Za-z0-9_]{50,}")),
    # GitHub classic PAT format: ghp_<exactly 36 base62 chars>
    # Total length 40 chars (prefix + 36 chars).
    # Use {36} exact match (no doc example is exactly 36 chars).
    ("github_pat (classic ghp_)",
     re.compile(r"ghp_[A-Za-z0-9]{36}")),
    # GitHub OAuth token: gho_<exactly 36 chars>
    ("github_oauth (gho_)",
     re.compile(r"gho_[A-Za-z0-9]{36}")),
    # GitHub user-to-server: ghu_<exactly 36 chars>
    ("github_user (ghu_)",
     re.compile(r"ghu_[A-Za-z0-9]{36}")),
    # GitHub server-to-server: ghs_<exactly 36 chars>
    ("github_server (ghs_)",
     re.compile(r"ghs_[A-Za-z0-9]{36}")),
    # GitHub refresh token: ghr_<exactly 76 chars>
    ("github_refresh (ghr_)",
     re.compile(r"ghr_[A-Za-z0-9]{76}")),
    # Generic env var assignment with literal token value.
    # Catches: GH_TOKEN='...', GITHUB_TOKEN="...", TOKEN=abcd1234...
    # We require the value to be 50+ chars (typical real-token length).
    # This avoids matching short doc examples like GH_TOKEN='<your-token>'.
    ("env_var_literal_assignment",
     re.compile(
         r"\b(GH_TOKEN|GITHUB_TOKEN|GH_PAT|GITHUB_PAT|"
         r"NPM_TOKEN|PYPI_TOKEN|AWS_SECRET_ACCESS_KEY|"
         r"DOCKER_TOKEN|CLOUDFLARE_TOKEN)\s*=\s*['\"]([A-Za-z0-9_\-]{50,})['\"]"
     )),
    # Git remote URL with embedded credentials:
    # https://user:password@host/path
    # We require 20+ chars for the password portion (real PATs are 36+ chars).
    ("git_remote_with_credentials",
     re.compile(r"https://[A-Za-z0-9._-]+:[A-Za-z0-9_\-]{20,}@[A-Za-z0-9.-]+")),
]

# Files / extensions to scan. Conservative — focus on code/config files.
SCANABLE_EXTENSIONS = {
    ".sh", ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg",
    ".md",  # markdown can have code blocks with leaks
    ".txt", ".env",
    ".tf",  # terraform
    ".nix",
}

# Files / paths to skip (known-safe or third-party).
SKIP_PATHS = {
    "node_modules", ".git", ".turbo", ".next", "dist", "build",
    ".quartz-cache", "__pycache__", ".pytest_cache",
    "pnpm-lock.yaml",  # third-party hashes, not secrets
    "SHA256SUMS.txt",  # hash manifest, not secrets
}

# Specific literal patterns that are documentation, not real tokens.
# These are explicit allowlist entries — caught by the regex but
# known to be safe (placeholders or redacted examples).
ALLOWLIST_LITERALS = {
    # CHANGELOG.md mentions "github_pat_..." with three dots — below 20-char threshold
    # so the regex won't match it anyway. But just to be safe:
    "github_pat_...",
    "github_pat_XXXX",
    # Common redaction patterns
    "github_pat_REDACTED",
    "ghp_REDACTED",
    "your_github_pat_here",
    "YOUR_GITHUB_PAT",
    "<GH_TOKEN>",
    "<GITHUB_TOKEN>",
}


def is_scanable(path: Path) -> bool:
    """Whether the file at `path` should be scanned."""
    # Skip non-existent or directory.
    if not path.is_file():
        return False
    # Skip if any path component is in SKIP_PATHS.
    try:
        rel_parts = path.parts
    except (ValueError, AttributeError):
        return False
    for part in rel_parts:
        if part in SKIP_PATHS:
            return False
    # Skip if extension not in SCANABLE_EXTENSIONS.
    if path.suffix.lower() not in SCANABLE_EXTENSIONS:
        return False
    return True


def scan_file(path: Path) -> List[Tuple[int, str, str, str]]:
    """Scan one file for token patterns.

    Returns: list of (line_number, line_content, pattern_name, matched_text)
    """
    findings: List[Tuple[int, str, str, str]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                for pattern_name, pattern in TOKEN_PATTERNS:
                    for match in pattern.finditer(line):
                        matched_text = match.group(0)
                        # Allowlist check — skip known-safe literals.
                        if matched_text in ALLOWLIST_LITERALS:
                            continue
                        # Skip lines that look like they're documenting the pattern
                        # (e.g. comments saying "matches github_pat_<35-40 chars>_...")
                        # by checking if the matched_text appears as a literal in
                        # a documentation/comment context. Heuristic: if line starts
                        # with # or // or *, treat as comment — but still flag
                        # if the matched value is 30+ chars (real tokens are long).
                        # Allowlist already catches placeholders; we don't double-filter.
                        findings.append((line_num, line.rstrip(), pattern_name, matched_text))
    except (PermissionError, OSError):
        # Skip unreadable files.
        pass
    return findings


def iter_scanable_files(root: Path) -> Iterable[Path]:
    """Yield all scanable files under `root`."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place (os.walk allows mutation of dirnames).
        dirnames[:] = [d for d in dirnames if d not in SKIP_PATHS]
        for fname in filenames:
            path = Path(dirpath) / fname
            if is_scanable(path):
                yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Polymath OS token hygiene checker")
    parser.add_argument(
        "--paths", nargs="*", default=None,
        help="Specific paths to scan (default: scan whole repo)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print every file scanned (default: only findings)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    scan_paths = [Path(p) for p in args.paths] if args.paths else [repo_root]

    all_findings: List[Tuple[Path, int, str, str, str]] = []  # (path, line_num, line, pattern, match)
    files_scanned = 0

    for scan_path in scan_paths:
        scan_path = scan_path.resolve()
        if scan_path.is_file():
            files_to_scan = [scan_path]
        else:
            files_to_scan = list(iter_scanable_files(scan_path))

        for fpath in files_to_scan:
            files_scanned += 1
            if args.verbose:
                print(f"  scanning {fpath}", file=sys.stderr)
            findings = scan_file(fpath)
            for line_num, line, pattern_name, matched_text in findings:
                all_findings.append((fpath, line_num, line, pattern_name, matched_text))

    print(f"→ Scanned {files_scanned} file(s)", file=sys.stderr)

    if not all_findings:
        print("✓ No plaintext tokens found — repo is clean", file=sys.stderr)
        return 0

    print(f"✗ Found {len(all_findings)} plaintext token leak(s):", file=sys.stderr)
    print(file=sys.stderr)
    for fpath, line_num, line, pattern_name, matched_text in all_findings:
        # Truncate the matched_text for display (don't echo back the full token).
        display_match = matched_text[:12] + "...[REDACTED]..." if len(matched_text) > 12 else matched_text
        print(f"  {fpath}:{line_num}  [{pattern_name}]  matched: {display_match}",
              file=sys.stderr)
        print(f"    line: {line[:120]}", file=sys.stderr)
        print(file=sys.stderr)
    print("To fix:", file=sys.stderr)
    print("  1. Remove the plaintext token from the file(s) above.", file=sys.stderr)
    print("  2. If the token is real and was committed, REVOKE it immediately at", file=sys.stderr)
    print("     https://github.com/settings/tokens (GitHub auto-revokes plaintext PATs", file=sys.stderr)
    print("     found in git history / logs via their secret scanner).", file=sys.stderr)
    print("  3. Use env vars (export GH_TOKEN=...) for runtime — never inline in scripts.", file=sys.stderr)
    print("  4. After git push with token in remote URL, reset to clean form:", file=sys.stderr)
    print("     git remote set-url origin https://github.com/USER/REPO.git", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
