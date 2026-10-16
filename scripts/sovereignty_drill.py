#!/usr/bin/env python3
"""scripts/sovereignty_drill.py — Sovereignty drill runner (Gate-6).

Per ADR-0002 Sovereignty Registry: quarterly "учение выхода" — disable one
Tier 2 service, show that core+data work, record recovery time.

This script simulates the absence of a Tier 2 service by setting env vars
that block the service, then runs `make verify` + `cd runtime && python3 scripts/check.py`
to confirm the open-source contract still holds.

Output: JSON report with:
- service_disabled: str
- verify_pass: bool
- runtime_tests_pass: bool
- recovery_time_ms: int
- timestamp: ISO 8601

Usage:
    python3 scripts/sovereignty_drill.py --service github_pages
    python3 scripts/sovereignty_drill.py --service sentry
    python3 scripts/sovereignty_drill.py --service openrouter
    python3 scripts/sovereignty_drill.py --service 1password
    python3 scripts/sovereignty_drill.py --service all_tier2

Per ADR-0006 falsifiable self-*: this script is the falsifiability witness
for ADR-0002. Without this drill, "sovereignty" is just a label.
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TIER2_SERVICES = {
    # GitHub-tier: disable by setting GITHUB_ACTIONS=local (act-style)
    "github_pages": {
        "description": "GitHub Pages — the canonical mirror of polymath-os public site",
        "env_block": {"POLYMATH_DISABLE_GITHUB_PAGES": "1"},
        "expected_fallback": "local `python -m http.server` or `gh-pages` CLI",
    },
    "github_actions": {
        "description": "GitHub Actions — CI runner. Replaced by local `act -W` per ADR-0002 Tier 2",
        "env_block": {"POLYMATH_DISABLE_GITHUB_ACTIONS": "1", "GITHUB_ACTIONS": "local"},
        "expected_fallback": "`act -W .github/workflows/ci.yml -j ci` locally",
    },
    # Telemetry-tier: disable by clearing DSN env vars
    "sentry": {
        "description": "Sentry — error telemetry. Replaced by self-hosted Glitchtip (per ADR-0002 Tier 2)",
        "env_block": {"SENTRY_DSN": "", "GLITCHTIP_DSN": ""},
        "expected_fallback": "logs in Loki/local file, no remote telemetry",
    },
    "openrouter": {
        "description": "OpenRouter — LLM API gateway. Replaced by local Ollama/vLLM (per ADR-0002 Tier 2)",
        "env_block": {"OPENROUTER_API_KEY": "", "OPENAI_API_KEY": ""},
        "expected_fallback": "LLMLocalAdapter with llama-cpp-python (offline, no API key)",
    },
    "1password": {
        "description": "1Password CLI — secret extraction. Replaced by SOPS+age (per ADR-0002 Tier 1)",
        "env_block": {"OP_CONNECT_HOST": "", "OP_SERVICE_ACCOUNT_TOKEN": ""},
        "expected_fallback": "SOPS+age encrypted files in git, age key from operator's offline store",
    },
    "hetzner": {
        "description": "Hetzner Cloud — VPS hosting. Replaced by OVH/Scaleway/local bare-metal (per ADR-0002 Tier 2)",
        "env_block": {"HCLOUD_TOKEN": ""},
        "expected_fallback": "any Tier 2 VPS provider or local hardware",
    },
    "cloudflare": {
        "description": "Cloudflare — DNS/CDN. Replaced by bind9/local DNS (per ADR-0002 Tier 2)",
        "env_block": {"CLOUDFLARE_API_TOKEN": ""},
        "expected_fallback": "bind9 zone file, no CDN (direct VPS)",
    },
    "github_repo": {
        "description": "GitHub repo itself — the git hosting. Replaced by Gitea/Forgejo/Codeberg (per ADR-0002 Tier 2)",
        "env_block": {"POLYMATH_DISABLE_GITHUB_REPO": "1"},
        "expected_fallback": "`git remote set-url origin gitea@...` or local bare repo",
    },
    "obsidian": {
        "description": "Obsidian — vault viewer (closed-source app). Replaced by Foam/Logseq/`less` (per ADR-0002 Tier 2)",
        "env_block": {"POLYMATH_DISABLE_OBSIDIAN": "1"},
        "expected_fallback": "`cat`/`less` reads markdown directly; Foam in VSCode as GUI",
    },
    "quartz": {
        "description": "Quartz v4 — static site generator for garden. Replaced by MkDocs (per ADR-0002 Tier 2)",
        "env_block": {"POLYMATH_DISABLE_QUARTZ": "1"},
        "expected_fallback": "MkDocs Material — equivalent markdown-first SSG",
    },
    "betterstack": {
        "description": "BetterStack — uptime monitoring. Replaced by Uptime Kuma (per ADR-0002 Tier 2)",
        "env_block": {"BETTERSTACK_API_KEY": ""},
        "expected_fallback": "self-hosted Uptime Kuma or `curl -fsS -m 2` cron",
    },
}

def run_drill(service_name: str) -> dict:
    """Disable one service, verify core+data still work, record recovery time."""
    if service_name == "all_tier2":
        # Run all drills sequentially
        results = []
        for s in TIER2_SERVICES:
            if s != "github_repo":  # github_repo is too disruptive to test together
                r = run_drill(s)
                results.append({"service": s, **r})
        return {"services": results, "all_pass": all(r["verify_pass"] and r["runtime_tests_pass"] for r in results)}

    if service_name not in TIER2_SERVICES:
        return {"error": f"unknown service: {service_name}", "available": list(TIER2_SERVICES)}

    svc = TIER2_SERVICES[service_name]
    started = time.time()
    env = os.environ.copy()
    env.update(svc["env_block"])

    # Run make verify (Python-only, no network required)
    print(f"[drill] disabling {service_name} — {svc['description']}")
    print(f"[drill] expected fallback: {svc['expected_fallback']}")
    print(f"[drill] running `make verify`...")
    verify_result = subprocess.run(
        ["make", "verify"], cwd=REPO_ROOT, env=env,
        capture_output=True, text=True, timeout=60
    )
    verify_pass = verify_result.returncode == 0

    # Run runtime tests
    print(f"[drill] running `cd runtime && python3 scripts/check.py`...")
    runtime_result = subprocess.run(
        ["python3", "scripts/check.py"], cwd=REPO_ROOT / "runtime", env=env,
        capture_output=True, text=True, timeout=60
    )
    runtime_tests_pass = runtime_result.returncode == 0

    recovery_ms = int((time.time() - started) * 1000)

    report = {
        "service_disabled": service_name,
        "description": svc["description"],
        "expected_fallback": svc["expected_fallback"],
        "env_block_keys": list(svc["env_block"].keys()),
        "verify_pass": verify_pass,
        "verify_exit_code": verify_result.returncode,
        "verify_last_line": verify_result.stdout.strip().split("\n")[-1] if verify_result.stdout else "",
        "runtime_tests_pass": runtime_tests_pass,
        "runtime_exit_code": runtime_result.returncode,
        "runtime_last_line": runtime_result.stdout.strip().split("\n")[-1] if runtime_result.stdout else "",
        "recovery_time_ms": recovery_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return report


def main():
    p = argparse.ArgumentParser(description="Sovereignty drill runner — falsifiable witness for ADR-0002")
    p.add_argument("--service", "-s", required=True,
                   choices=list(TIER2_SERVICES) + ["all_tier2"],
                   help="which Tier 2 service to disable for the drill")
    p.add_argument("--output", "-o", default=None, help="write JSON report to file (default: stdout)")
    args = p.parse_args()

    report = run_drill(args.service)
    output = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"[drill] report written to {args.output}")
    else:
        print(output)

    # Exit non-zero if drill failed (verify or runtime tests broken)
    if isinstance(report, dict) and "verify_pass" in report:
        sys.exit(0 if report["verify_pass"] and report["runtime_tests_pass"] else 1)
    elif isinstance(report, dict) and "all_pass" in report:
        sys.exit(0 if report["all_pass"] else 1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
