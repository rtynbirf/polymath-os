# docs/LIBERATION_ROADMAP.md — Liberation Roadmap

**«ОСВОБОДИ И ИЗБАВИ ЧЕЛОВЕКА ОТ ВСЕХ "БЛАГОДЕТЕЛЕЙ
ЗАЩИТНИКОВ=ЗАХИСТНИКОВ ДОБРЫХ ДЯДЬ И ПРОЧЕЙ НЕСУСВЕТНОЙ АХИНЕИ"**

**Date**: 2026-10-16 (v3.0.0)
**Status**: Living document — updated as each benefactor is eliminated

This document is the **concrete path to zero external benefactors**.
Every "good uncle" in the rtynbirf ecosystem is listed here with its
sovereign replacement. When a replacement is implemented, the benefactor
is crossed out.

Per ADR-0002 (Sovereignty Registry): Tier 1 (sovereign) > Tier 2 (replaceable) > Tier 3 (closed, eliminate).

Per `scripts/check_freedom.py`: 42 benefactors found, 99 references.

## Liberation Plan — 5 Phases

### Phase 1: Eliminate Tier 3 (closed — DO NOT USE) ✅

| Benefactor | Replacement | Status |
|---|---|---|
| Chrome (Google) | Sovereign browser + engines.txt slot | ✅ DONE (v2.9.0) |
| Firefox (Mozilla) | Sovereign browser + engines.txt slot | ✅ DONE (v2.9.0) |
| Edge (Microsoft) | Sovereign browser + engines.txt slot | ✅ DONE (v2.9.0) |
| Safari (Apple) | Sovereign browser + engines.txt slot | ✅ DONE (v2.9.0) |
| Google Analytics | NONE — don't track humans | ✅ DONE (never used) |
| Google Tag Manager | NONE — don't track humans | ✅ DONE (never used) |

**Result**: Zero Tier 3 benefactors in the ecosystem. The human does not use any corporate browser. No tracking.

### Phase 2: Eliminate DNS benefactors (self-host DNS)

| Benefactor | Replacement | Status |
|---|---|---|
| Google DNS (8.8.8.8) | local unbound recursive resolver | 📋 documented |
| Cloudflare DNS (1.1.1.1) | local unbound | 📋 documented |
| Yandex DNS (77.88.8.8) | local unbound (RU zone forward) | 📋 documented |
| Quad9 DNS (9.9.9.9) | local unbound | 📋 documented |

**Action**: Create `infra/dns/unbound.conf` template — recursive resolver, no upstream forward (except root hints). RU zone forwarded to local BIND9 with RU geodata. No Google. No Cloudflare. No Yandex. No Quad9.

### Phase 3: Eliminate CDN benefactors (vendor everything)

| Benefactor | Replacement | Status |
|---|---|---|
| jsDelivr CDN | vendored in БИБЛИОТЕКИ/ (singulyar already does this) | 📋 verify |
| unpkg.com | vendored locally | 📋 |
| cdnjs.cloudflare | vendored locally | 📋 |
| gstatic.com | local health endpoint (curl http://localhost/health) | 📋 |

**Action**: Create `scripts/vendor_deps.sh` — downloads all CDN-hosted JS/CSS and stores in `БИБЛИОТЕКИ/vendored/`. CI check: no `cdn.*` or `unpkg.*` or `jsdelivr.*` in any HTML/JS file (except `engines.txt` which lists independent engines).

### Phase 4: Eliminate git/package benefactors (self-host)

| Benefactor | Replacement | Status |
|---|---|---|
| GitHub (Microsoft) | Gitea/Forgejo self-hosted | 📋 documented |
| GitHub Pages | self-hosted nginx/caddy | 📋 documented |
| npm registry | local Verdaccio or pnpm store cache | 📋 |
| PyPI | local devpi or pip cache | 📋 |
| HuggingFace CDN | self-hosted model mirror (6 parts on own VPS) | 📋 |

**Action**: Create `infra/self-host/` directory with docker-compose for:
- Gitea (git hosting)
- Verdaccio (npm registry mirror)
- devpi (PyPI mirror)
- nostromo (Nostr relay)
- Glitchtip (error tracking)
- Uptime Kuma (monitoring)

All on one VPS. All Tier 1 (the human owns the VPS).

### Phase 5: Eliminate supply-chain benefactors

| Benefactor | Replacement | Status |
|---|---|---|
| Sigstore/cosign OIDC | local GPG signing | 📋 documented in ADR-0013 |
| Google connectivity check | local health endpoint | 📋 |
| Nostr public relays | self-hosted nostromo | 📋 |
| mempool.space / blockcypher / blockstream / blockchain.info | self-hosted electrs | 📋 |

**Action**: Switch cosign from keyless (OIDC via GitHub Actions) to local GPG key. Document: "cosign keyless is convenient but ties to GitHub OIDC. For full sovereignty: local GPG key, cosign sign --key gpg://..."

## Freedom Score

| Phase | Benefactors eliminated | Remaining |
|---|---|---|
| 1 (Tier 3) | 6 ✅ | 0 |
| 2 (DNS) | 0 📋 | 4 |
| 3 (CDN) | 0 📋 | 4 |
| 4 (Git/Packages) | 0 📋 | 5 |
| 5 (Supply chain) | 0 📋 | 5+ |
| **Total** | **6** | **~18** |

**Freedom score**: 6/24 = 25% free. Target: 100% (no benefactors).

## The Sovereign Stack (target)

```
┌─────────────────────────────────────────────────┐
│                 HUMAN (PID=1)                    │
│              electrode → intent                 │
└──────────────────────┬──────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │   Sovereign Browser    │
           │   (apps/browser/)      │
           │   engine: NetSurf/     │
           │   Servo/Ladybird       │
           └───────────┬───────────┘
                       │
           ┌───────────┴───────────┐
           │   SINGULYAR EIR v0.3   │
           │   (intent kernel)      │
           │   Python↔JS bridge     │
           └───────────┬───────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
┌───────┐      ┌───────────┐      ┌───────────┐
│ singu-│      │ singulyar-│      │ cell65-   │
│ lyar  │      │ llm       │      │ host      │
│ (PWA) │      │ (Qwen2.5) │      │ (VPN)     │
└───────┘      └───────────┘      └───────────┘
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
           ┌───────────┴───────────┐
           │   SELF-HOSTED VPS       │
           │   (owned by human)      │
           │                         │
           │   • Gitea (git)         │
           │   • Verdaccio (npm)     │
           │   • nostromo (Nostr)    │
           │   • Glitchtip (errors) │
           │   • Uptime Kuma        │
           │   • unbound (DNS)      │
           │   • electrs (BTC)      │
           │   • model mirror (LLM) │
           └─────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │   THE HUMAN'S VPS      │
           │   No corporations.     │
           │   No benefactors.      │
           │   No good uncles.      │
           │   No protectors.       │
           │   No nonsensical       │
           │   nonsense.             │
           └─────────────────────────┘
```

## Verification

`python3 scripts/check_freedom.py` — scans the repo for benefactor references.
Currently: 42 benefactors, 99 references (mostly in documentation/Audit).
Target: 0 Tier 3, 0 undocumented Tier 2.

Per `make verify` check #16: sovereignty drill runner exists + is executable.
The drill disables one Tier 2 service and verifies the contract holds.

When `check_freedom.py` reports 0 Tier 3 + 0 undocumented Tier 2 — the human is free.

## References

- ADR-0002 (Sovereignty Registry) — Tier classification
- ADR-0018 (Genomic Architecture) — each part = whole
- SOVEREIGNTY_CONTRACT.md — the 7 contracts
- MANIFESTO.md — 15 principles
- scripts/check_freedom.py — the freedom meter
- scripts/sovereignty_drill.py — the drill
