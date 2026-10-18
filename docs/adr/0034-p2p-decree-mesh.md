# ADR-0034 — P2P Decree Mesh (WebRTC + Ed25519 Federation)

**Date:** 2026-10-20
**Status:** Proposed — requires `aiortc` for implementation
**Tags:** federation, webrtc, ed25519, p2p, v3.20.0-candidate
**Deciders:** @USER (Командир корабля)
**Extends:** ADR-0021 (Decree as Supreme Law), ADR-0027 (Decree-Enforced HTTP JSON-RPC Server), ADR-0029 (СИНГУЛЯР Security Model)

## Context

The decree system is currently single-instance: one human, one SQLite
`~/.polymath-os/decrees.db`, one local Agent Mesh. The human can already
federate INTENTS across instances via ADR-0027 (HTTP JSON-RPC server) and
ADR-0025 (outbound A2A client) — but the **decrees themselves** do not
propagate. A second polymath-os instance (on a laptop, a VPS, a phone)
does not see decrees issued on the first.

This is a real gap for the sovereignty story. Three concrete scenarios:

1. **Multi-device human** — the human issues "never use Google DNS" on the
   desktop. The laptop has no idea. An Intent on the laptop to "configure
   Google 8.8.8.8" passes the decree gate because the laptop's local
   `decrees.db` is empty.

2. **Federation with another human** — two polymath-os operators want to
   share prohibitions (e.g. a household-level "never install Chrome on any
   family device" rule). Today they have to copy-paste decree texts into
   each other's Decree Portal, which is manual, error-prone, and not
   hash-chained across instances.

3. **Air-gapped fallback** — the human's VPS goes offline. HTTP federation
   (ADR-0027) is dead. But if the human has another local instance on the
   same LAN (e.g. a Raspberry Pi acting as a backup trust anchor), the
   decrees should still be able to sync over direct P2P — no signaling
   server, no STUN, no TURN. **Per ADR-0014 (WebRTC adapter as Tier 2
   dependency)**, this is the exact use case the WebRTC adapter was
   designed for: air-gapped P2P using QR-encoded SDP exchange.

### What's now available

Three pieces of infrastructure are now in place that make P2P decree
mesh feasible for the first time:

1. **WebRTC DataChannel transport** — `runtime/src/adapters/webrtc_adapter.py`
   (per ADR-0014). Uses `aiortc` when available, returns `NotExecuted`
   with honest UNAVAILABLE status when not (per ADR-0006 — no
   READY-with-lies). The adapter already declares `webrtc.send` and
   `webrtc.recv` capabilities with `offline=True, local_only=True`
   (air-gapped by design).

2. **Federation endpoint** — `runtime/src/agent_mesh_server.py` (per
   ADR-0027). HTTP JSON-RPC 2.0 server, zero external deps (Python
   stdlib). Already declares `/.well-known/agent.json` (Agent Card
   per ADR-0023), `GET /health`, `POST /agent/{agent_id}`. DECREE_BLOCK
   → HTTP 403. This server is the **discovery + control plane** for the
   P2P mesh: peers find each other's Agent Cards over HTTP, then upgrade
   to direct WebRTC DataChannels for high-throughput decree sync.

3. **External trust anchor** — `runtime/src/trust_anchor.py` (per
   ADR-0029 §9, IAEA pattern). Publishes the SHA-256 hash of the last
   decree to an out-of-band file. This is the **anchor** for cross-mesh
   verification: when peer B claims it has the same decrees as peer A,
   peer A compares its `verify_trust_anchor()` output against peer B's
   reported anchor hash. Mismatch → tamper detected, sync refused.

### What's still missing

- **Ed25519 decree signatures.** Today the decree hash chain proves
  *internal* integrity (no one row has been edited), but it does not
  prove *provenance* (which human issued this decree). A polymath-os
  instance that receives a decree over the mesh has no cryptographic way
  to verify that the decree actually came from the human it claims to
  be from. This is the X-Road / Estonia pattern (ADR-0029 §10) —
  cryptographically signed federation messages — applied to decrees
  specifically. **A future `runtime/src/decree_signatures.py` module
  will attach an Ed25519 signature to each decree at issue time.**
  The signature is computed over `(seq, prev_hash, timestamp, decree_text)`
  and stored alongside the decree row. Verification uses the issuing
  human's published Ed25519 public key (the human's `~/.polymath-os/`
  pubkey is published in their `.well-known/agent.json` so peers can
  fetch it before verifying).

- **Real `aiortc` transport in `webrtc_adapter.py`.** The adapter is
  a Tier 2 stub — it returns `NotExecuted` when `aiortc` is not
  installed. Production deployment of this ADR requires `aiortc` to
  actually be installed (`pip install aiortc`) and the adapter's
  `send()` / `recv()` paths to be exercised end-to-end.

## Decision

Implement **P2P Decree Mesh** as a three-layer federation protocol
stack on top of existing infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Decree Sync Protocol (this ADR)                    │
│   - peer discovery via Agent Card (ADR-0023)                │
│   - decree batch exchange over WebRTC DataChannel           │
│   - Ed25519 signature verification on every received decree │
│   - trust anchor cross-verification (ADR-0029 §9)           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Transport (existing)                               │
│   - WebRTC DataChannel (ADR-0014 webrtc_adapter)           │
│   - HTTP JSON-RPC control plane (ADR-0027 agent_mesh_server)│
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Cryptography (existing + new)                      │
│   - SHA-256 hash chain (ADR-0021 DecreeLog)                │
│   - External trust anchor (ADR-0029 §9 trust_anchor.py)    │
│   - Ed25519 signatures [NEW — decree_signatures.py module]  │
└─────────────────────────────────────────────────────────────┘
```

### Decree sync flow

When peer A discovers peer B (via `GET /.well-known/agent.json` on
peer B's HTTP federation endpoint), the sync proceeds:

1. **Discovery** — A fetch B's Agent Card. A checks `decree_scope`
   on B's card — if B is in a different scope (e.g. B is
   `scope=cell65-host` and A is `scope=polymath-os`), sync is
   limited to decrees with `scope='all'` (per v3.19.0 scope hierarchy).
2. **Anchor compare** — A calls `verify_trust_anchor()` locally and
   sends its anchor hash to B. B does the same. If anchors match,
   the two instances are already in sync — no transfer needed.
   If anchors differ, the instance with the LOWER `last_decree_seq`
   requests the missing decrees from the higher one.
3. **Batch transfer** — the higher instance serializes the missing
   decrees as a JSON array (each entry: `seq, prev_hash, timestamp,
   decree_text, decree_hash, category, scope, signature`) and sends
   them over the WebRTC DataChannel in a single `DECREE_SYNC` message.
4. **Signature verify** — the receiving instance verifies the
   Ed25519 signature on every decree using the issuing human's
   published public key (fetched from the sender's
   `.well-known/agent.json`). Decrees with invalid signatures are
   REJECTED — not appended to the local log.
5. **Chain verify** — the receiving instance verifies that each
   received decree's `prev_hash` correctly chains to the previous
   one, AND that the first received decree's `prev_hash` chains to
   the local last decree (no gap, no fork).
6. **Append + re-anchor** — verified decrees are appended to the
   local SQLite log via `DecreeLog.issue()` (which auto-publishes
   a fresh trust anchor per the existing hook in `issue()`).

### Ed25519 key management

- Each human generates an Ed25519 keypair on first run:
  `~/.polymath-os/decree_signing_key` (private, mode 0600) and
  `~/.polymath-os/decree_public_key` (public, published in
  `.well-known/agent.json` under a new `decree_public_key` field).
- The keypair is per-human, not per-instance. Multiple polymath-os
  instances owned by the same human share the same keypair (the
  private key is synced manually — e.g. via the existing age-encrypted
  vault sync).
- A peer that receives a decree verifies the signature against the
  sender's published Ed25519 public key. A peer that has not yet
  fetched the public key refuses to sync (fail-closed per ADR-0006).
- Key rotation: issuing a new "I am rotating my signing key to <new
  pubkey>" decree, signed by BOTH the old and new keys, rotates the
  trust root. This is the standard PGP-style rotation pattern.

## Implementation outline

> **This is an outline, not a full implementation.** A full implementation
> requires `aiortc` to be installed (`pip install aiortc`), which may not
> be available in this environment. The stubs below are written to fail
> closed (return `NotExecuted` / `False`) when `aiortc` or
> `decree_signatures` is absent — exactly the pattern established by
> `runtime/src/adapters/webrtc_adapter.py` for the same dependency.

### New module: `runtime/src/decree_signatures.py` (future)

```python
# Sketch — not implemented in this ADR.
#
# import nacl.signing  # PyNaCl (libsodium wrapper) — Tier 2 dependency
# import json
# from pathlib import Path
#
# def sign_decree(decree_row: dict, private_key_path: str) -> str:
#     """Return Ed25519 signature (hex) over (seq, prev_hash, timestamp, decree_text)."""
#     ...
#
# def verify_decree_signature(decree_row: dict, signature_hex: str, public_key: str) -> bool:
#     """Verify Ed25519 signature. Returns True iff valid."""
#     ...
#
# def load_public_key(path: str) -> str:
#     """Load Ed25519 public key (hex) from a file."""
#     ...
```

### New module: `runtime/src/p2p_decree_mesh.py` (future)

```python
# Sketch — not implemented in this ADR.
#
# class P2PDecreeMesh:
#     def __init__(self, decree_log, signing_key_path=None, public_key_path=None):
#         self.decree_log = decree_log
#         self.signing_key_path = signing_key_path
#         self.public_key_path = public_key_path
#         # aiortc is a Tier 2 dependency — fail closed if absent.
#         try:
#             from aiortc import RTCPeerConnection  # type: ignore
#             self._has_aiortc = True
#         except ImportError:
#             self._has_aiortc = False
#
#     def discover_peer(self, peer_agent_url: str) -> dict:
#         """Fetch peer's Agent Card via HTTP (ADR-0027)."""
#         # Uses A2AClient (ADR-0025) under the hood — same outbound decree gate.
#         ...
#
#     def sync_with_peer(self, peer_agent_url: str) -> dict:
#         """Run the 6-step sync flow described above. Returns a report:
#         {synced_count, rejected_count, anchor_before, anchor_after, errors}.
#         Returns NotExecuted-style dict when aiortc absent."""
#         if not self._has_aiortc:
#             return {"status": "unavailable",
#                     "reason": "aiortc not installed — install with: pip install aiortc"}
#         ...
#
#     def verify_received_decree(self, decree_row: dict, signature_hex: str,
#                                peer_public_key: str) -> bool:
#         """Steps 4 + 5: signature + chain verification."""
#         try:
#             from decree_signatures import verify_decree_signature
#             if not verify_decree_signature(decree_row, signature_hex, peer_public_key):
#                 return False
#         except ImportError:
#             # If the decree_signatures module is not yet implemented,
#             # fail closed — refuse to sync (per ADR-0006).
#             return False
#         # Chain verification is done by DecreeLog._verify_chain on append.
#         return True
```

### Wire format for `DECREE_SYNC` messages

```json
{
  "ver": 1,
  "type": "DECREE_SYNC",
  "src": "singulyar-eir.local",
  "ts": "2026-10-20T12:34:56Z",
  "decrees": [
    {
      "seq": 8,
      "prev_hash": "abc...def",
      "timestamp": "2026-10-20T12:30:00Z",
      "decree_text": "never use Google DNS",
      "decree_hash": "012...345",
      "category": "prohibition",
      "scope": "all",
      "signature": "ed25519:fed...cba"
    }
  ],
  "anchor_after": "012...345"
}
```

The wire format follows the existing packet convention from the JS
`СИНГУЛЯР_17_ЗАЛ.html` reference (see `webrtc_adapter.py` docstring):
`{ver, t, src, seq, ts, v}` — extended with the `decrees` and
`anchor_after` fields specific to sync.

### CLI sketch

```
python3 -m runtime.src.p2p_decree_mesh sync --peer http://192.168.1.42:7654
  → discovers peer, runs sync, prints report

python3 -m runtime.src.p2p_decree_mesh sign-decree --seq 8
  → attaches an Ed25519 signature to decree #8 (uses local private key)

python3 -m runtime.src.p2p_decree_mesh verify-decree --seq 8 --peer-key <hex>
  → verifies a decree's signature against a peer's published public key
```

## Consequences

**Positive:**
- **Closes the multi-device sovereignty gap** — decrees issued on one
  polymath-os instance propagate to all instances owned by the same
  human, with cryptographic provenance
- **Air-gapped fallback** — works over LAN P2P when HTTP federation
  is offline (consistent with the air-gapped-by-design principle of
  ADR-0014 and `СИНГУЛЯР_17_ЗАЛ`)
- **Composes with existing trust anchor** — the IAEA-pattern external
  anchor (ADR-0029 §9) is the cross-mesh verification primitive; no
  new trust root needed
- **Composes with existing scope hierarchy** — v3.19.0 scope hierarchy
  naturally limits which decrees propagate to which peers (e.g. a
  household-level rule on a parent's instance doesn't auto-propagate to
  a child's `polymath-os.browser` instance unless scope='all')
- **Fail-closed by default** — every unimplemented layer (aiortc,
  decree_signatures) refuses the operation rather than degrading to
  unsigned / unverified sync (per ADR-0006)

**Negative:**
- **New Tier 2 dependency on PyNaCl (libsodium)** for Ed25519. PyNaCl
  is well-maintained, MIT-licensed, and the de-facto Python Ed25519
  library. It is replaceable by `cryptography.hazmat.primitives.asymmetric.ed25519`
  if PyNaCl is unsuitable — the signature algorithm is standardized
  (RFC 8032), so any conformant library works.
- **New Tier 2 dependency on `aiortc`** for WebRTC. Already declared
  Tier 2 by ADR-0014. The DataChannel contract is the Tier 1
  interface — `aiortc` is one possible backend.
- **No relay / no TURN** — air-gapped by design means sync only works
  on the same LAN or via manual SDP exchange (QR code, paste). For
  cross-network federation without HTTP, a TURN server would be needed
  — explicitly out of scope (would re-introduce the centralization the
  sovereignty story rejects).
- **Key rotation is a manual process** — the human must coordinate the
  "I am rotating my signing key" decree across instances. Future work:
  automate rotation via a decree-driven workflow.
- **No transitive sync** — if A syncs with B and B syncs with C, A
  does not automatically get C's decrees (each sync is pairwise).
  This is the right default (prevents decree spam propagation) but
  may surprise users expecting gossip-style mesh propagation.

**Neutral:**
- The Ed25519 signature is computed over the same fields the SHA-256
  hash chain uses (`seq, prev_hash, timestamp, decree_text`). This is
  not a coincidence — the signature is over the *exact bytes* that
  the hash chain commits to, so signature verification and chain
  verification are checking the same underlying data.
- The `decree_public_key` field added to `.well-known/agent.json`
  is forward-compatible — peers that don't understand it ignore it
  (per ADR-0023's `additionalProperties: true` schema).

## Alternatives considered

### Alternative A: HTTP-only decree sync (extend ADR-0027)

Instead of WebRTC, expose `POST /agent/{agent_id}/decree-sync` on the
existing HTTP server. Peer A POSTs its trust anchor hash; peer B
responds with the missing decrees as JSON.

**Rejected because:** HTTP sync requires both instances to be online
and on the same network-reachable address. It also requires a
long-running server on each instance — fine for a VPS, but breaks
for a laptop behind NAT or a phone on cellular. WebRTC P2P handles
NAT traversal via the SDP exchange (the human manually exchanges a
QR code if needed). HTTP remains the *control plane* (Agent Card
discovery, anchor compare) but the *data plane* (bulk decree transfer)
is WebRTC.

### Alternative B: Git-based decree sync

Push the SQLite db to a git remote; peers `git pull` and merge.

**Rejected because:** SQLite + git is famously bad — binary blobs,
no meaningful diffs, merge conflicts on the `.db` file. Also requires
a git host (GitHub, self-hosted), which re-introduces the
centralization the sovereignty story rejects. The trust anchor
comparison still works (the anchor is a separate JSON file that
*is* git-friendly), but the decree db itself should not go through
git.

### Alternative C: Append-only CRDT (Mercurial-style)

Treat each decree log as a CRDT; merge by `(seq, prev_hash)` causal
graph; conflicts resolved by hash-chain topology.

**Rejected for now:** CRDTs are the right long-term answer (the
ROADMAP_v4.0.0 §5.6 already lists "CRDT-based vault sync" as a
v4.0.0 target). But CRDT semantics for *decrees* (which are
authoritative, not consensus-driven) are subtle: a CRDT would let
two humans issue conflicting decrees and "merge" them, which
violates the sovereignty principle that **the human's word is
law, not the mesh's consensus**. Ed25519 signatures preserve
provenance; CRDTs would erase it. CRDTs are appropriate for the
vault (notes), not for the decree log (law).

### Alternative D: Blockchain / external SSI

Use a public blockchain (Bitcoin, Ethereum) or a self-sovereign
identity network (Hyperledger Indy) as the global decree ledger.

**Rejected because:** introduces an external trust root that is
NOT under the human's control — directly violates the sovereignty
principle. The whole point of polymath-os is that the human's
device IS the trust root. Blockchain is appropriate only as one
possible *external* trust anchor (per ADR-0029 §9, the IAEA pattern
allows blockchain publication of the anchor hash as one option
among many — printout, USB, lawyer, blockchain).

## Verification

> Verification is conditional on the missing dependencies being
> installed. The tests must skip cleanly when `aiortc` or
> `decree_signatures` is absent (using `unittest.skipUnless`).

- `runtime/tests/test_p2p_decree_mesh.py` — to be written when the
  module is implemented. Tests:
  1. `test_discover_peer_via_agent_card` — fetch peer's Agent Card
  2. `test_anchor_compare_match_no_sync` — anchors equal → no transfer
  3. `test_anchor_compare_mismatch_triggers_sync` — anchors differ → sync
  4. `test_received_decree_with_invalid_signature_rejected` — tamper detected
  5. `test_received_decree_with_broken_chain_rejected` — fork detected
  6. `test_aiortc_absent_returns_unavailable` — fail-closed, no crash
  7. `test_decree_signatures_module_absent_refuses_sync` — fail-closed
- `runtime/tests/test_decree_signatures.py` — to be written when the
  module is implemented. Tests:
  1. `test_sign_and_verify_roundtrip` — sign then verify returns True
  2. `test_verify_with_wrong_key_returns_false` — provenance check
  3. `test_sign_decree_tampered_text_returns_false` — integrity check
  4. `test_load_public_key_missing_file_raises` — fail-closed

## References

- ADR-0014 (WebRTC adapter as Tier 2 dependency) — transport layer
- ADR-0021 (Decree as Supreme Law) — append-only hash-chained invariant
- ADR-0023 (Agent Card Protocol) — peer discovery
- ADR-0025 (Decree-Driven A2A Client) — outbound decree gate for HTTP
- ADR-0027 (Decree-Enforced HTTP JSON-RPC Server) — federation endpoint
- ADR-0029 (СИНГУЛЯР Security Model) — §9 IAEA pattern, §10 Estonia X-Road
- `runtime/src/adapters/webrtc_adapter.py` — WebRTC transport stub
- `runtime/src/agent_mesh_server.py` — HTTP federation server
- `runtime/src/trust_anchor.py` — external trust anchor (IAEA pattern)
- [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) — Ed25519
- [aiortc](https://github.com/aiortc/aiortc) — async Python WebRTC
- [PyNaCl](https://pynacl.readthedocs.io/) — Python libsodium bindings
- [Estonia X-Road](https://www.x-road.global) — federation without centralization

## Self-reference

This ADR is **Proposed** — it cannot move to **Accepted** until:
1. The `decree_signatures.py` module is implemented (Ed25519 signing)
2. The `p2p_decree_mesh.py` module is implemented (sync protocol)
3. `aiortc` is added as an optional dependency (`pip install aiortc`)
4. The 11 tests listed in §Verification all pass

Once those four conditions are met, a decree-driven amendment per
ADR-0026 can mark this ADR Accepted:
```
Decree #N (amendment): "supersede ADR-0034 status Proposed with Accepted,
  conditions met: decree_signatures module + p2p_decree_mesh module +
  aiortc installed + 11 tests pass"
```

Until then, this ADR documents the **design intent** and the
**integration points** with already-built infrastructure, so a future
implementer has a clear specification to work from.

The air-gapped P2P decree mesh is the **last mile** of the sovereignty
story: not just "the human's word is law on this device" but "the human's
word is law on every device the human owns, with cryptographic provenance
and zero centralization." ВОЛЯ ЧЕЛОВЕКОИЗЪЯВЛЕНИЯ = НАКАЗ — across
devices, not just on one.
