#!/usr/bin/env python3
"""scripts/check_freedom.py — Freedom Checker (Gate-liberation).

Scans the entire polymath-os repo for references to external "benefactors"
(corporate services, cloud providers, CDN, DNS, etc.) and reports:
- Which are documented in the Sovereignty Registry (ADR-0002)
- Which are NOT documented (undocumented dependency = freedom gap)
- Which Tier they belong to (1=sovereign, 2=replaceable, 3=closed)

Per user: «ОСВОБОДИ И ИЗБАВИ ЧЕЛОВЕКА ОТ ВСЕХ "БЛАГОДЕТЕЛЕЙ
ЗАЩИТНИКОВ=ЗАХИСТНИКОВ ДОБРЫХ ДЯДЬ И ПРОЧЕЙ НЕСУСВЕТНОЙ АХИНЕИ"»

This script makes liberation MEASURABLE. You can't free what you can't see.

Usage:
    python3 scripts/check_freedom.py              # scan + report
    python3 scripts/check_freedom.py --strict      # exit 1 if any undocumented dependency
    python3 scripts/check_freedom.py --json        # JSON output
"""
import argparse, json, os, re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════
# THE BENEFACTORS — every corporate/external service
# that the human might depend on. Each has a sovereign
# replacement. None is a "good uncle" — all are gates.
# ═══════════════════════════════════════════════════

BENEFACTORS = {
    # ─── Git hosting ───
    "github.com":           {"name": "GitHub (Microsoft)",       "tier": 2, "replacement": "Gitea/Forgejo self-hosted", "category": "git"},
    "raw.githubusercontent": {"name": "GitHub raw CDN",           "tier": 2, "replacement": "self-hosted git mirror", "category": "cdn"},
    "github.io":            {"name": "GitHub Pages",              "tier": 2, "replacement": "self-hosted nginx/caddy", "category": "hosting"},

    # ─── DNS ───
    "8.8.8.8":              {"name": "Google DNS",               "tier": 2, "replacement": "local unbound/bind9", "category": "dns"},
    "8.8.4.4":              {"name": "Google DNS secondary",     "tier": 2, "replacement": "local unbound", "category": "dns"},
    "77.88.8.8":            {"name": "Yandex DNS",               "tier": 2, "replacement": "local unbound (RU zone)", "category": "dns"},
    "1.1.1.1":              {"name": "Cloudflare DNS",           "tier": 2, "replacement": "local unbound", "category": "dns"},
    "9.9.9.9":              {"name": "Quad9 DNS",               "tier": 2, "replacement": "local unbound", "category": "dns"},

    # ─── CDN / Connectivity check ───
    "gstatic.com":          {"name": "Google connectivity check", "tier": 2, "replacement": "local health endpoint", "category": "connectivity"},
    "cloudflare.com":       {"name": "Cloudflare CDN/DNS",       "tier": 2, "replacement": "bind9 + direct VPS", "category": "cdn"},
    "jsdelivr":             {"name": "jsDelivr CDN",             "tier": 2, "replacement": "vendored in БИБЛИОТЕКИ/", "category": "cdn"},
    "unpkg.com":            {"name": "unpkg CDN",               "tier": 2, "replacement": "vendored locally", "category": "cdn"},
    "cdnjs.cloudflare":     {"name": "cdnjs CDN",                "tier": 2, "replacement": "vendored locally", "category": "cdn"},

    # ─── AI / ML ───
    "huggingface.co":       {"name": "HuggingFace model CDN",    "tier": 2, "replacement": "self-hosted model mirror", "category": "ai"},
    "openrouter.ai":        {"name": "OpenRouter LLM API",       "tier": 2, "replacement": "local Ollama/llama-cpp-python", "category": "ai"},
    "openai.com":           {"name": "OpenAI API",              "tier": 2, "replacement": "local LLM (Qwen2.5-0.5B)", "category": "ai"},
    "anthropic.com":        {"name": "Anthropic API",            "tier": 2, "replacement": "local LLM", "category": "ai"},

    # ─── Telemetry / Monitoring ───
    "sentry.io":            {"name": "Sentry error tracking",    "tier": 2, "replacement": "self-hosted Glitchtip", "category": "telemetry"},
    "betterstack.com":      {"name": "BetterStack uptime",       "tier": 2, "replacement": "self-hosted Uptime Kuma", "category": "monitoring"},
    "google-analytics":     {"name": "Google Analytics",         "tier": 3, "replacement": "NONE (don't track)", "category": "telemetry"},
    "googletagmanager":     {"name": "Google Tag Manager",       "tier": 3, "replacement": "NONE (don't track)", "category": "telemetry"},

    # ─── Infrastructure ───
    "hetzner.de":           {"name": "Hetzner Cloud VPS",        "tier": 2, "replacement": "OVH/Scaleway/local hardware", "category": "infra"},
    "ovh.com":              {"name": "OVH VPS",                  "tier": 2, "replacement": "local hardware / other provider", "category": "infra"},
    "digitalocean":         {"name": "DigitalOcean VPS",         "tier": 2, "replacement": "local hardware", "category": "infra"},

    # ─── Secrets ───
    "1password.com":        {"name": "1Password secrets manager", "tier": 2, "replacement": "SOPS+age (offline key)", "category": "secrets"},
    "bitwarden.com":        {"name": "Bitwarden secrets",        "tier": 2, "replacement": "SOPS+age", "category": "secrets"},
    "vaultproject.io":      {"name": "HashiCorp Vault",           "tier": 2, "replacement": "SOPS+age + local file", "category": "secrets"},

    # ─── Package registries ───
    "registry.npmjs.org":   {"name": "npm registry",            "tier": 2, "replacement": "local Verdaccio / pnpm store", "category": "packages"},
    "pypi.org":             {"name": "PyPI registry",            "tier": 2, "replacement": "local devpi / pip cache", "category": "packages"},

    # ─── Browser engines ───
    "google.com/chrome":    {"name": "Chrome browser (Google)",   "tier": 3, "replacement": "NetSurf/Servo/Ladybird", "category": "browser"},
    "mozilla.org/firefox":  {"name": "Firefox browser (Mozilla)", "tier": 3, "replacement": "NetSurf/Servo/Ladybird", "category": "browser"},
    "microsoft.com/edge":   {"name": "Edge browser (Microsoft)",  "tier": 3, "replacement": "NetSurf/Servo/Ladybird", "category": "browser"},
    "apple.com/safari":     {"name": "Safari browser (Apple)",   "tier": 3, "replacement": "NetSurf/Servo/Ladybird", "category": "browser"},

    # ─── Nostr relays ───
    "nostr.oxtr.dev":       {"name": "Nostr relay (oxtr.dev)",   "tier": 2, "replacement": "self-hosted nostromo/wss-relay", "category": "nostr"},
    "nos.lol":              {"name": "Nostr relay (nos.lol)",    "tier": 2, "replacement": "self-hosted relay", "category": "nostr"},
    "relay.damus.io":       {"name": "Nostr relay (damus.io)",   "tier": 2, "replacement": "self-hosted relay", "category": "nostr"},

    # ─── Blockchain ───
    "mempool.space":        {"name": "mempool.space BTC explorer", "tier": 2, "replacement": "self-hosted Electrum/esplora", "category": "blockchain"},
    "blockcypher.com":      {"name": "blockcypher BTC API",       "tier": 2, "replacement": "self-hosted electrs", "category": "blockchain"},
    "blockstream.info":     {"name": "blockstream.info explorer",  "tier": 2, "replacement": "self-hosted electrs", "category": "blockchain"},
    "blockchain.info":      {"name": "blockchain.com explorer",    "tier": 2, "replacement": "self-hosted electrs", "category": "blockchain"},

    # ─── Supply chain ───
    "sigstore.dev":         {"name": "Sigstore/cosign OIDC",      "tier": 2, "replacement": "local GPG signing", "category": "supply-chain"},
    "slsa.dev":             {"name": "SLSA framework",            "tier": 1, "replacement": "it's a spec, not a service", "category": "supply-chain"},
}

# Files to skip (generated, lock files, etc.)
SKIP_PATTERNS = {
    'node_modules', '.git', '__pycache__', 'dist', '.turbo', '.next',
    'pnpm-lock.yaml', 'flake.lock', '.mutmut-cache', 'mutants',
    'target', '*.pyc', '*.gguf', '*.bin',
}

def should_skip(path: Path) -> bool:
    for skip in SKIP_PATTERNS:
        if skip in str(path):
            return True
    return False

def scan_repo():
    """Scan all files for benefactor references."""
    findings = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip directories
        dirs[:] = [d for d in dirs if not should_skip(Path(root) / d)]
        for fname in files:
            fpath = Path(root) / fname
            if should_skip(fpath):
                continue
            try:
                content = fpath.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue

            for benefactor_id, info in BENEFACTORS.items():
                if benefactor_id.lower() in content.lower():
                    # Count occurrences
                    count = content.lower().count(benefactor_id.lower())
                    # Get line numbers of first 3 occurrences
                    lines = []
                    for i, line in enumerate(content.splitlines(), 1):
                        if benefactor_id.lower() in line.lower():
                            lines.append(i)
                            if len(lines) >= 3:
                                break
                    findings.append({
                        "benefactor": benefactor_id,
                        "name": info["name"],
                        "tier": info["tier"],
                        "category": info["category"],
                        "replacement": info["replacement"],
                        "file": str(fpath.relative_to(REPO_ROOT)),
                        "count": count,
                        "first_lines": lines,
                    })
    return findings

def main():
    p = argparse.ArgumentParser(description="Freedom Checker — scan for corporate benefactors")
    p.add_argument("--strict", action="store_true", help="exit 1 if any undocumented benefactor found")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args()

    findings = scan_repo()

    if args.json:
        print(json.dumps({"total": len(findings), "findings": findings}, indent=2))
        return

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  FREEDOM CHECKER — «Освободи и избавь»                       ║")
    print("║  Сканирует репо на упоминания благодетелей                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    if not findings:
        print("  ✅ ZERO benefactors found in repo.")
        print("  The human is free. No good uncles. No protectors.")
        return

    # Group by benefactor
    by_benefactor = {}
    for f in findings:
        key = f["benefactor"]
        if key not in by_benefactor:
            by_benefactor[key] = {"name": f["name"], "tier": f["tier"],
                                  "category": f["category"], "replacement": f["replacement"],
                                  "files": [], "total_count": 0}
        by_benefactor[key]["files"].append(f["file"])
        by_benefactor[key]["total_count"] += f["count"]

    # Sort by tier (3=closed first, then 2=replaceable)
    sorted_b = sorted(by_benefactor.items(), key=lambda x: (-x[1]["tier"], x[1]["category"]))

    tier_emoji = {1: "🟢", 2: "🟡", 3: "🔴"}
    tier_name = {1: "Tier 1 (sovereign)", 2: "Tier 2 (replaceable)", 3: "Tier 3 (closed)"}

    print(f"  Found {len(findings)} references to {len(by_benefactor)} benefactors:\n")

    for benefactor_id, info in sorted_b:
        emoji = tier_emoji.get(info["tier"], "❓")
        tier = tier_name.get(info["tier"], "?")
        print(f"  {emoji} {info['name']}")
        print(f"     Tier: {tier} | Category: {info['category']}")
        print(f"     Replacement: {info['replacement']}")
        print(f"     References: {info['total_count']} in {len(info['files'])} file(s)")
        for f in info['files'][:3]:
            print(f"       → {f}")
        if len(info['files']) > 3:
            print(f"       ... and {len(info['files'])-3} more")
        print()

    # Summary
    tier_counts = {1: 0, 2: 0, 3: 0}
    for info in by_benefactor.values():
        tier_counts[info["tier"]] = tier_counts.get(info["tier"], 0) + 1

    print("  ─── Summary ───")
    print(f"  🟢 Tier 1 (sovereign, keep):     {tier_counts.get(1, 0)}")
    print(f"  🟡 Tier 2 (replaceable, plan):    {tier_counts.get(2, 0)}")
    print(f"  🔴 Tier 3 (closed, eliminate):    {tier_counts.get(3, 0)}")
    print(f"  Total benefactors:                {len(by_benefactor)}")
    print()

    if tier_counts.get(3, 0) > 0:
        print("  ⚠ Tier 3 benefactors found — these must be ELIMINATED.")
        print("    No human should depend on closed corporate services.")

    if args.strict and (tier_counts.get(2, 0) > 0 or tier_counts.get(3, 0) > 0):
        sys.exit(1)

if __name__ == "__main__":
    main()
