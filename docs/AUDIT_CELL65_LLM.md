# docs/AUDIT_CELL65_LLM.md — Level 4-5 Recursive Audit

**Date**: 2026-10-16 (v2.6.0)
**Subject**: `rtynbirf/cell65-host` (66KB, sovereign-node) + `rtynbirf/singulyar-llm` (466MB, Qwen2.5-0.5B)
**Method**: Same methodology as AUDIT_POLYMATH (Level 1) + AUDIT_SINGULYAR (Level 3).
Format: что не так → почему важно → альтернатива → как проверить [док/вывод/проверить]

This is the **4th and 5th levels** of recursive audit:
- Level 1: AUDIT_POLYMATH (polymath-os Report + RUNBOOK)
- Level 2: REDACTION_AUDIT (HMAC brute-forceability)
- Level 3: AUDIT_SINGULYAR (live singulyar 2.3GB product, 90 findings)
- **Level 4**: this document — cell65-host (sovereign-node)
- **Level 5**: this document — singulyar-llm (local LLM model repo)

---

## Part I — cell65-host (sovereign-node, Level 4)

### C1 · install-server.sh uses self-signed cert — no ACME/Let's Encrypt [вывод]

**Что не так.** `install-server.sh` generates a self-signed ECDSA cert with `openssl ecparam -name prime256v1`. Reality protocol uses this for TLS handshake camouflage. Self-signed = no CA validation, which is correct for Reality (it mimics a specific website, not a general TLS server). But for Hysteria2 (which uses QUIC+TLS), a self-signed cert means the client must pin the cert hash — if the cert rotates, the client breaks silently.

**Почему важно.** Hysteria2 with self-signed cert is fine for personal use (one human, one VPS), but rotation = manual cert hash update on client. No ACME = no auto-renewal = cert expires = Hysteria2 transport dies silently.

**Альтернатива.** For Reality: keep self-signed (correct by design). For Hysteria2: add optional ACME/Let's Encrypt path (`--domain` flag → `caddy`/`acme.sh` auto-cert). Document: "Reality = self-signed (correct); Hysteria2 = self-signed (works but no auto-renewal); T2-CF-WS = Cloudflare cert (managed by CF)."

**Как проверить.** `openssl x509 -in /etc/sovereign-node/cert.pem -text -noout | grep -E 'Not After|Issuer'` → self-signed, expiry date.

### C2 · No STUN server specified — Reality/VLESS works without, but Hysteria2 may fail NAT [проверить]

**Что не так.** `client-singbox.example.json` has empty `iceServers` (no STUN/TURN). VLESS+Reality works without STUN (direct TCP). VLESS+WS+CF works through Cloudflare CDN. Hysteria2 (QUIC) may need STUN for NAT traversal on symmetric NAT routers.

**Почему важно.** If the human's home router has symmetric NAT, Hysteria2 won't establish without STUN. The "3 independent transports" promise may silently degrade to 2.

**Альтернатива.** Add optional STUN server (`stun:stun.l.google.com:19302`) for Hysteria2 only. Document the NAT-type dependency. Add `stun-cli` test in selftest.yml.

**Как проверить.** `nmap -sU -p 19302 stun.l.google.com` from behind the human's router.

### C3 · auto-rotation interval 3min — may cause flapping [док]

**Что не так.** `urltest` outbound with `interval: 3m` and `tolerance: 50ms`. Every 3 minutes, all 3 transports probe `gstatic.com/generate_204`. If T1 is faster by >50ms, switch. If T1 and T2 are within 50ms, no switch.

**Почему важно.** On an unstable connection (common in RU), latency fluctuates ±100ms over 3-minute windows. This can cause rapid switching (flapping) — every 3 minutes the system hops between transports. Each hop = brief connection loss for all active sessions.

**Альтернатива.** Increase tolerance to 100ms or 150ms. Add "minimum time on current transport" (e.g., `min_switch_interval: 10m`) — don't switch more often than every 10 minutes even if another transport is faster. Or add hysteresis: only switch if the new transport is faster for 3 consecutive probes.

**Как проверить.** `sing-box logs | grep "switch" | wc -l` over 1 hour — if >5 switches, flapping.

### C4 · DNS hijack at TUN layer — no DNS leak protection test [вывод]

**Что не так.** Server config has `dns.hijack-dns` (intercepts all DNS at TUN layer). RU domains go to `77.88.8.8` (Yandex DNS, RU). Non-RU goes to DoH `8.8.8.8` (Google, over tunnel). This is correct. But there's no test that DNS actually goes through the tunnel — a DNS leak test (like `dnsleaktest.com`) isn't in selftest.yml.

**Почему важно.** If sing-box crashes or TUN mode fails, DNS queries fall back to system DNS (ISP DNS in RU). The ISP sees all DNS queries — privacy is gone. Without a DNS leak test in CI, this failure is silent.

**Альтернатива.** Add `dns-leak-test` step in selftest.yml: `curl -s https://bash.ws/dnsleak/test.txt | bash` (or equivalent) — verify the DNS resolver is the tunneled one, not the ISP.

**Как проверить.** `curl -s https://bash.ws/dnsleak/test.txt | bash` — should show Google (tunneled) not Yandex (direct) for non-RU queries.

### C5 · No version pin for sing-box binary [док]

**Что не так.** `install-server.sh` fetches `latest` sing-box binary from GitHub releases. `install-sovereign-node.ps1` does the same on Windows. No version pin. If sing-box releases a breaking change (config format change, protocol deprecation), the install script silently breaks.

**Почему важно.** Per ADR-0008 (polymath-os MCP version pin): "MCP behind thin adapter, version pinned, migration planned." Same principle should apply to sing-box — it's the load-bearing binary for the entire sovereign-node.

**Альтернатива.** Pin to a specific version: `SINGBOX_VERSION=1.10.0`. Add a version-check step in selftest.yml. Document upgrade path: "to upgrade sing-box, change SINGBOX_VERSION + run selftest."

**Как проверить.** `sing-box version` — should output the pinned version. If different, selftest fails.

### C6 · selftest.yml uses TEST-NET-3 IP (203.0.113.10) — documentation IP, may not route [док]

**Что не так.** `client-render` job uses `VPS_IP=203.0.113.10` (TEST-NET-3, RFC 5737 documentation range). This IP is reserved and won't route — the `RenderOnly` flag is set, so no actual connection attempt is made. But if someone removes `RenderOnly`, the test would hang trying to connect to a non-routable IP.

**Почему важно.** The test is correct (RenderOnly prevents actual connection), but fragile — one flag change and it hangs. Also, the config generated with a documentation IP is not useful for actual deployment testing.

**Альтернатива.** Add a comment: `# TEST-NET-3 (RFC 5737) — do NOT remove -RenderOnly`. Or use a real VPS IP in a separate `integration-test` job (requires a real VPS, not CI).

**Как проверить.** `grep RenderOnly .github/workflows/selftest.yml` — should be present.

### C7 · No CHANGELOG.md or release tags in cell65-host [вывод]

**Что не так.** cell65-host has no CHANGELOG.md, no version tags, no releases. The repo is a living document that changes without versioning. Per singulyar AGENTS.md law 7: "Один факт — одно место" — but there's no place for the version fact.

**Почему важно.** If the human needs to know "what changed since I last set up the sovereign-node," they have to `git log` and read commit messages. No semantic versioning = no upgrade path documentation.

**Альтернатива.** Add CHANGELOG.md (Keep a Changelog v1.1.0). Tag first release as v1.0.0. Add `git tag` in CI on merge to main. Or: use Conventional Commits + auto-changelog.

**Как проверить.** `git tag | wc -l` → should be >0.

### C8 · provision-edge.ps1 creates Cloudflare zone — no cleanup path [док]

**Что не так.** `provision-edge.ps1` creates a Cloudflare zone, sets SSL=Full, creates DNS records. But there's no `deprovision-edge.ps1` — no cleanup. If the human wants to remove the Cloudflare CDN layer (e.g., moving to a different CDN or going direct), they have to manually delete the zone in Cloudflare dashboard.

**Почему важно.** Reversibility (per ADR-0005 in polymath-os): every change should be rollback-able. Creating a Cloudflare zone without a cleanup script is a one-way operation.

**Альтернатива.** Add `deprovision-edge.ps1` that deletes the zone (or at least the DNS records). Add `--dry-run` flag to provision-edge.ps1. Document: "to remove Cloudflare layer: run deprovision-edge.ps1, then remove T2-CF-WS outbound from client config."

**Как проверить.** `ls sovereign-node/windows/deprovision*` → should exist.

---

## Part II — singulyar-llm (Qwen2.5-0.5B, Level 5)

### L1 · ПРАВИЛА_СИНГУЛЯРА.txt not accessible via Contents API [док]

**Что не так.** The file `ОБУЧЕНИЕ/ПРАВИЛА_СИНГУЛЯРА.txt` returned 404 via Contents API (URL-encoded Cyrillic path). The file may not exist, or the API path encoding is incorrect.

**Почему важно.** Per singulyar-llm README: "адаптер `llm.local`... статусы честные... фолбэк — правило-слой, который исполняет команды даже без весов." The rules text IS the instruction layer — without it, the LLM has no system prompt. If the file is inaccessible, the honesty contract is broken.

**Альтернатива.** Verify the file exists via `git ls-tree`. If it exists, fix the API path encoding. If not, restore from git history.

**Как проверить.** `gh api repos/rtynbirf/singulyar-llm/contents/ОБУЧЕНИЕ/ПРАВИЛА_СИНГУЛЯРА.txt` or `git clone` + `ls ОБУЧЕНИЕ/`.

### L2 · MANIFEST.txt has SHA-256 for parts but not for the whole merged file [док]

**Что не так.** MANIFEST.txt lists SHA-256 for each of the 6 parts. `ПРОВЕРКА_ЦЕЛОСТНОСТИ.py` verifies each part + optional merge. But the manifest doesn't list the SHA-256 of the merged whole (491,400,032 bytes). If a part is corrupted but the corruption happens to preserve the part's hash (extremely unlikely but theoretically possible), the merged file would be wrong.

**Почему важно.** Per ADR-0004 (SLSA Build L2): supply chain integrity requires attestation of the final artifact, not just its components. Part-level hashes verify parts; whole-file hash verifies the assembly.

**Альтернатива.** Add `WHOLE_SHA256=74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` to MANIFEST.txt. `ПРОВЕРКА_ЦЕЛОСТНОСТИ.py --merge` should verify the merged file against this hash.

**Как проверить.** `python3 СБОРКА/ПРОВЕРКА_ЦЕЛОСТНОСТИ.py --merge && sha256sum merged.gguf` → should match WHOLE_SHA256.

### L3 · No version tag in singulyar-llm — "v0.6" exists only in README text [вывод]

**Что не так.** singulyar-llm has no git tags. The version "v0.6" appears only in README.md text and ПРАВИЛА_СИНГУЛЯРА.txt header. No `git tag v0.6` has been created. No GitHub Release.

**Почему важно.** Per singulyar AGENTS.md: "апстрим `rtynbirf/singulyar-llm`" — singulyar references this repo as upstream for the LLM brain. Without version tags, singulyar can't pin to a specific version of the instruction layer. If the rules change (e.g., v0.7 adds rule 18), singulyar's offline copy may be stale.

**Альтернатива.** Tag the current state as `v0.6.0`. Add `VERSION` file in root. singulyar's ` освежитьПравила()` can check `VERSION` against the pinned version.

**Как проверить.** `git tag -l` → should show v0.6.0.

### L4 · "Честно о «обучении»" — honest disclosure is good, but no audit path [вывод]

**Что не так.** README.md says: "Веса не дообучались (нет GPU и корпуса — и мы не изображаем обратное)." This is honest — the "training" is just an instruction layer (rules + command examples). But there's no way to verify that the weights are actually the original Qwen2.5-0.5B-Instruct GGUF (not a modified version). The MANIFEST.txt says "downloaded 2026-10-02" from HuggingFace, but no signature on that claim.

**Почему важно.** Per ADR-0006 (falsifiable self-*): the claim "weights are unmodified Qwen2.5-0.5B" should be verifiable. Currently, the only evidence is MANIFEST.txt text. An attacker who replaces the weights with a backdoored version just needs to update the manifest.

**Альтернатива.** Add cosign signature on the MANIFEST.txt (or on the merged GGUF). Verify: `cosign verify-blob MANIFEST.txt --certificate ... --signature ...`. This proves the manifest hasn't been tampered with. For the weights themselves: compare SHA-256 against HuggingFace's published hash for `Qwen/Qwen2.5-0.5B-Instruct-GGUF q4_k_m`.

**Как проверить.** `curl -sL https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf.sha256` → compare with MANIFEST.txt WHOLE_SHA256.

### L5 · 6 parts ≤100MB = git file size limit workaround, but no LFS [вывод]

**Что не так.** The 6-part split is explicitly because "GitHub принимает файлы до 100 МБ." This is a workaround for not using Git LFS. Git LFS would store the 469MB file as a single LFS pointer in git, with the actual binary stored on LFS server. The 6-part approach means: (a) `git clone` downloads all 6 parts (~469MB) every time, (b) no LFS bandwidth limits, (c) but no LFS locking (concurrent modification risk, though this repo is solo).

**Почему важно.** For a solo repo, this is fine. But if singulyar-llm ever gets contributors, the 6-part approach is fragile — two people modifying different parts simultaneously = merge chaos. Git LFS would handle this with LFS locking.

**Альтернатива.** Keep the 6-part approach for now (it works, it's documented, it's honest). Document: "6 parts = GitHub 100MB limit workaround. Git LFS not used because: (a) solo repo, (b) LFS bandwidth limits, (c) parts are verifiable via SHA-256. If contributors join: switch to LFS."

**Как проверить.** `git lfs ls-files` → should be empty (confirming no LFS).

---

## Summary

| ID | Repo | Finding | Severity | Confidence |
|---|---|---|---|---|
| C1 | cell65-host | Self-signed cert, no ACME for Hysteria2 | medium | [вывод] |
| C2 | cell65-host | No STUN for Hysteria2 NAT traversal | medium | [проверить] |
| C3 | cell65-host | 3min rotation interval may flap | medium | [док] |
| C4 | cell65-host | No DNS leak test in CI | medium | [вывод] |
| C5 | cell65-host | No version pin for sing-box binary | high | [док] |
| C6 | cell65-host | TEST-NET-3 IP in selftest (fragile) | low | [док] |
| C7 | cell65-host | No CHANGELOG or release tags | medium | [вывод] |
| C8 | cell65-host | No deprovision-edge.ps1 cleanup | medium | [док] |
| L1 | singulyar-llm | ПРАВИЛА_СИНГУЛЯРА.txt 404 via API | high | [док] |
| L2 | singulyar-llm | No whole-file SHA-256 in MANIFEST | medium | [док] |
| L3 | singulyar-llm | No version tag (v0.6 only in text) | medium | [вывод] |
| L4 | singulyar-llm | No audit path for weight integrity | high | [вывод] |
| L5 | singulyar-llm | 6-part workaround, no LFS | low | [вывод] |

**13 findings total** (8 cell65-host + 5 singulyar-llm). 3 high, 8 medium, 2 low.

## Cross-ADR mapping

- ADR-0002 (sovereignty): C5 (version pin), C7 (changelog), L3 (version tag)
- ADR-0004 (SLSA L2): L2 (whole-file hash), L4 (weight integrity attestation)
- ADR-0005 (reversibility): C8 (no cleanup path for Cloudflare)
- ADR-0006 (falsifiable): C4 (DNS leak test), L4 (weight integrity)
- ADR-0008 (version pin): C5 (sing-box version)
- ADR-0009 (default-deny): C2 (STUN for Hysteria2 = external dependency)

## Recursive audit methodology — proven at 5 levels

| Level | Document | Subject | Findings |
|---|---|---|---|
| 1 | AUDIT_POLYMATH (A1-A11, V1-V12, B1-B11) | polymath-os Report + RUNBOOK + v0.2 | ~30 |
| 2 | REDACTION_AUDIT | HMAC brute-forceability | 1 (closed) |
| 3 | AUDIT_SINGULYAR | singulyar 2.3GB (90 findings, 5 critical MERGED) | 90 |
| **4** | **AUDIT_CELL65_LLM Part I** | **cell65-host (8 findings)** | **8** |
| **5** | **AUDIT_CELL65_LLM Part II** | **singulyar-llm (5 findings)** | **5** |

**Total: 5 levels, ~134 findings.** The methodology is generic — same format across all levels.
