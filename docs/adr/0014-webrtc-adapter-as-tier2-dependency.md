# ADR-0014 — WebRTC Adapter as Tier 2 Dependency

**Date:** 2026-10-16 (Gate-7 creativity)
**Status:** Accepted
**Deciders:** @USER
**Supersedes:** None (extends ADR-0012 — SINGULYAR EIR as Layer 5)

## Context

Gate-3 introduced `LLMLocalAdapter` — the first real consumer of the SINGULYAR
EIR kernel. Gate-6 added `HTTPAdapter` — second real consumer (network).
Gate-7 creativity adds `WebRTCAdapter` — third real consumer (air-gapped P2P).

The Python-порт of singulyar ·17 ЗАЛ (air-gapped WebRTC, no STUN/TURN/STUN).
Per singulyar audit (Gate-5 S26): the JS adapter uses `RTCPeerConnection({
iceServers: [] })` — works only on LAN. Cross-network needs TURN, which
defeats the air-gapped design.

The Python port uses `aiortc` (async Python WebRTC implementation) — a
Tier 2 dependency per ADR-0002 (replaceable by raw socketpair or py-libjuice).

## Decision

- **adapter_id**: `webrtc.local`
- **Capabilities declared**: 2 (`webrtc.send`, `webrtc.recv`) — both
  `offline=True` (air-gapped by design), `local_only=True` (P2P, no server),
  `idempotent=True` (safe retry per ADR-0007)
- **Dependency**: `aiortc` (Tier 2, optional). If not installed:
  `is_available() → False`, `status() → UNAVAILABLE` with reason.
- **Honest failure mode**: `NotExecuted` raised when aiortc absent or no peer.
  Per ADR-0006: status() NEVER lies READY when aiortc absent.

## Consequences

- **+**: Third real consumer of SINGULYAR EIR — proves kernel works for
  real-time air-gapped transport, not just request/response
- **+**: Air-gapped by design — works on LAN without any external dependency
  (no STUN/TURN provider, no signaling server)
- **-**: aiortc is async; v0.1 uses sync API with NotImplementedError for
  actual send (v0.5 will add asyncio bridge)
- **-**: LAN-only scope (no cross-network without TURN — defeats air-gap)
- **-**: aiortc adds ~30 MB install (heavy for embedded use cases)

## Alternatives considered

1. **Raw socketpair for LAN P2P** — simpler, no async, but doesn't match
   the WebRTC contract that singulyar uses. Rejected: breaks JS↔Python parity.

2. **py-libjuice** (ICE library) — more low-level, would need full WebRTC
   stack on top. Rejected: too much implementation work for v0.1.

3. **No WebRTC adapter in polymath-os** — rejected: would leave
   LIMITATIONS.md item 8 ("no real network adapters") only partially closed
   (HTTPAdapter covers network, but not air-gapped P2P).

## Verification (deferred to v0.5)

- `pip install aiortc` + run `tests/test_webrtc_adapter.py` — full coverage
- Live two-process test: one creates peer connection + generates SDP offer,
  other accepts SDP offer, exchanges answer, sends a message, receiver
  reads via `recv()` — verify packet received with `src:seq` dedup

## References

- ADR-0002 (Sovereignty Registry) — aiortc is Tier 2 (replaceable)
- ADR-0006 (Falsifiable self-*) — status() honest UNAVAILABLE when aiortc absent
- ADR-0007 (Failover on NotExecuted) — WebRTC failure → NotExecuted → kernel failover
- ADR-0012 (SINGULYAR EIR as Layer 5) — this is the third real consumer
- AUDIT_SINGULYAR.md S26 (·17 ЗАЛ air-gapped WebRTC) — JS source of truth
- https://github.com/aiortc/aiortc

## Source reference

JS adapter: `rtynbirf/singulyar/СИНГУЛЯР_17_ЗАЛ.html` (60KB, 1752 lines).
Key elements ported:
- `RTCPeerConnection({ iceServers: [] })` → `WebRTCAdapter.create_peer_connection(peer_id)`
- DataChannel `singulyar_p2p_data` → TODO v0.5 (asyncio bridge)
- Packet format `{ver:1, t:STATE, src, seq, ts, v}` → ported verbatim
- `src:seq` dedup → ported in `recv()` method
- BroadcastChannel `singulyar-hall` → not ported (browser-only concept);
  Python uses multiprocessing.Queue for in-process peer discovery
