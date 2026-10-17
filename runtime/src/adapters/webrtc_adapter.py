"""runtime/src/adapters/webrtc_adapter.py — SINGULYAR EIR WebRTC adapter
(Python-порт of singulyar ·17 ЗАЛ air-gapped P2P).

This is the THIRD real-world consumer of the SINGULYAR EIR kernel (after
LLMLocalAdapter in Gate-3 and HTTPAdapter in Gate-6). WebRTC adapter
provides air-gapped P2P communication — no STUN, no TURN, no signaling
server. SDP offer/answer exchanged out-of-band (QR code, manual paste,
any channel the human chooses).

## Source reference

JS adapter lives at `rtynbirf/singulyar/СИНГУЛЯР_17_ЗАЛ.html` (60KB):
- `RTCPeerConnection({ iceServers: [] })` — empty ICE config, no STUN/TURN
- DataChannel `singulyar_p2p_data` with `{ ordered: false, maxRetransmits: 0 }`
- Audio: `echoCancellation:false, noiseSuppression:false, autoGainControl:false, channelCount:1`
- QR-encoded SDP offer/answer on `<canvas id="p2pQr">`
- BroadcastChannel `singulyar-hall` with localStorage-event fallback
- Packets: `{ver:1, t:HELLO|STATE|CMD|BYE|CRDT|CRDTHI|CRDTSNAP, src, seq, ts, v}`
- Dedup: `src:seq` — every sender carries its own monotonic counter

## Python port (this file)

Python doesn't have native WebRTC in stdlib. Options:
- aiortc (https://github.com/aiortc/aiortc) — async Python WebRTC implementation
  over UDP, requires `pip install aiortc` (extra dep — Tier 2 per ADR-0002)
- raw socketpair for LAN-only P2P (no real WebRTC, but air-gapped)
- This adapter uses aiortc when available, else NotExecuted (no effect,
  kernel can fail over to other adapters like HTTPAdapter)

Per ADR-0002: aiortc is Tier 2 (replaceable by raw socketpair or by
`py-libjuice` ICE library). The Adapter contract is Tier 1 (interface).

## Honest disclosure (LIMITATIONS.md item 8 partial closure)

- No real WebRTC stack in v0.3 — adapter checks for aiortc, returns
  NotExecuted with helpful message if not installed
- No QR encoding (would require `qrcode` Python lib — also Tier 2)
- No BroadcastChannel (browser-only concept) — uses multiprocessing.Queue
  for in-process peer discovery; for cross-process, use Unix domain socket
- Full implementation deferred to v0.5

## Capabilities declared

- webrtc.send   operation: 'webrtc_send'   risk: medium  idempotent=True  offline=True local_only=True priority 10
  (offline=True because no signaling server — air-gapped by design)
- webrtc.recv   operation: 'webrtc_recv'   risk: low     idempotent=True  offline=True local_only=True priority 5

Per ADR-0007: NotExecuted raised on:
- aiortc not installed (no effect — kernel can fail over to HTTPAdapter)
- No active peer connection (NotExecuted with reason)

RuntimeError raised on:
- aiortc installed but connection error mid-send (effect may have happened)

Cross-ADR: ADR-0002 (sovereignty) — Tier 2 dependency (aiortc replaceable);
ADR-0006 (falsifiable) — status() returns UNAVAILABLE with reason when
aiortc absent, not READY-with-lies; ADR-0007 (failover) — NotExecuted on
absent peer; ADR-0012 (EIR layer-5) — third real consumer.
"""

import json
import os
import sys
import time
from typing import Any, Dict, Optional
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from singulyar_runtime import (
    Adapter, Capability, Intent, Observation,
    PRESENT, ABSENT, UNAVAILABLE,
    NotExecuted,
)

# Optional: aiortc for real WebRTC stack
try:
    from aiortc import RTCPeerConnection, RTCDataChannel  # type: ignore
    _HAS_AIORTC = True
except ImportError:
    RTCPeerConnection = None  # type: ignore
    RTCDataChannel = None  # type: ignore
    _HAS_AIORTC = False


ADAPTER_ID = "webrtc.local"
ADAPTER_VERSION = "v0.1 (Python-порт of singulyar ·17 ЗАЛ)"

CAPABILITIES = (
    Capability(
        capability_id="webrtc.send",
        operation="webrtc_send",
        adapter_id=ADAPTER_ID,
        risk_ceiling="medium",
        offline=True,  # air-gapped by design — no STUN/TURN/signaling server
        idempotent=True,  # messages dedup by (src, seq) — safe retry
        local_only=True,  # peer-to-peer, no server relay
        priority=10,
    ),
    Capability(
        capability_id="webrtc.recv",
        operation="webrtc_recv",
        adapter_id=ADAPTER_ID,
        risk_ceiling="low",
        offline=True,
        idempotent=True,  # receiving the same packet twice is safe
        local_only=True,
        priority=5,
    ),
)


class WebRTCAdapter(Adapter):
    """WebRTC adapter — air-gapped P2P (Python-порт of singulyar ·17 ЗАЛ).

    Lifecycle:
      1. __init__: state = "not_loaded" (UNAVAILABLE). If aiortc installed,
         can transition to "ready" via create_peer_connection().
      2. create_peer_connection(peer_id): if aiortc installed, create
         RTCPeerConnection with empty iceServers (air-gapped). Returns
         local SDP offer to exchange via out-of-band channel (QR/paste).
      3. set_remote_sdp(sdp_answer): complete the handshake.
      4. send(message): write to DataChannel. If no peer or aiortc absent,
         raises NotExecuted (no effect — kernel can fail over).
      5. recv(): pull from in-memory queue (populated by DataChannel.on_message).

    Per ADR-0006 (falsifiable self-*): status() returns UNAVAILABLE with
    honest reason when aiortc not installed, NOT READY-with-lies.
    """

    adapter_id = ADAPTER_ID

    def __init__(self, **kw):
        super().__init__(**kw)
        self._state: str = "not_loaded"  # "not_loaded" | "ready"
        self._reason: str = (
            "aiortc not installed — air-gapped P2P unavailable. "
            "Install with: pip install aiortc"
        ) if not _HAS_AIORTC else "no peer connection yet — call create_peer_connection()"
        self._pc: Optional[Any] = None  # RTCPeerConnection
        self._channel: Optional[Any] = None  # RTCDataChannel
        self._recv_queue: list = []  # in-memory buffer for received messages
        self._peer_id: Optional[str] = None
        self._seq: int = 0  # monotonic counter for our sent messages
        self._seen_seqs: Dict[str, int] = {}  # peer_id → last seen seq (dedup)
        self._cache: Dict[str, Dict[str, Any]] = {}  # idempotency_key → sent message
        self._calls: int = 0

    def is_available(self) -> bool:
        """Per ADR-0006: honest — adapter is available only if aiortc installed."""
        return _HAS_AIORTC

    def status(self) -> Dict[str, str]:
        return {
            "state": "READY" if self._state == "ready" else "UNAVAILABLE",
            "privacy": "local" if _HAS_AIORTC else "not-installed",
            "reason": "" if self._state == "ready" else self._reason,
            "adapter_version": ADAPTER_VERSION,
            "aiortc_installed": "yes" if _HAS_AIORTC else "no",
            "peer_connected": "yes" if self._channel is not None else "no",
            "messages_sent": str(self._seq),
            "messages_received": str(len(self._recv_queue)),
        }

    def execute(self, intent: Intent, idempotency_key: str) -> Any:
        """Send a message via WebRTC DataChannel.

        intent.payload must contain:
          - message: str (required, the payload to send)
          - peer_id: str (optional, defaults to current peer)

        Per ADR-0007: raises NotExecuted only if NO effect occurred.
        - aiortc not installed → NotExecuted (no effect, kernel failover)
        - no peer connected → NotExecuted (no effect)
        - send succeeds → returns seq number, caches message
        - send fails mid-flight → RuntimeError (effect may have happened)
        """
        self._calls += 1
        key = idempotency_key
        if key in self._cache:
            return self._cache[key]["seq"]  # idempotent — return cached seq

        if not _HAS_AIORTC:
            raise NotExecuted(
                "aiortc not installed — WebRTC air-gapped P2P unavailable. "
                "Install with: pip install aiortc. "
                "Kernel can fail over to HTTPAdapter (network-required) or wait for human."
            )

        if self._channel is None:
            raise NotExecuted(
                "no active peer connection — call create_peer_connection(peer_id) first. "
                "SDP offer must be exchanged out-of-band (QR code, manual paste, etc.)."
            )

        message = intent.payload.get("message")
        if not message:
            raise NotExecuted("intent.payload.message is required")

        self._seq += 1
        packet = {
            "ver": 1,
            "t": "STATE",  # mirrors singulyar ·17 ЗАЛ packet type
            "src": self._peer_id or "python-adapter",
            "seq": self._seq,
            "ts": int(time.time() * 1000),
            "v": message,
        }

        try:
            # aiortc is async; we'd normally `await channel.send(json.dumps(packet))`
            # For sync adapter, would need asyncio bridge. Mark as TODO v0.5.
            # For now, raise NotImplementedError with helpful message.
            raise NotImplementedError(
                "aiortc async send requires asyncio bridge — not yet implemented in v0.1. "
                "Full WebRTC send via aiortc is v0.5 work."
            )
        except NotImplementedError:
            # Per ADR-0007: NOT NotExecuted — we attempted an effect (the seq was
            # incremented and packet built). But the actual send didn't happen.
            # Honest path: cache the packet for later retry, raise NotExecuted.
            self._cache[key] = {"packet": packet, "seq": self._seq, "sent": False}
            self._seq -= 1  # roll back seq since we didn't actually send
            raise NotExecuted(
                "WebRTC async send requires asyncio bridge (v0.5 work). "
                "Packet built but not sent — kernel can retry with same idempotency_key."
            )
        except Exception as e:
            raise RuntimeError(f"WebRTC send failed mid-flight: {e}")

    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        """Read state: PRESENT (cached sent message), ABSENT (not sent yet).

        Per ADR-0010 S15: sibling keys don't pollute. Exact key match required.
        """
        key = idempotency_key
        try:
            if key in self._cache:
                entry = self._cache[key]
                return Observation(
                    status=PRESENT,
                    value={"packet": entry.get("packet"),
                           "seq": entry.get("seq"),
                           "sent": entry.get("sent", False),
                           "via": "webrtc.local"},
                    count=1,
                )
            return Observation(status=ABSENT, value=None, count=0)
        except Exception:
            return Observation(status=UNAVAILABLE, value=None, count=0)

    def calls(self) -> int:
        return self._calls

    def cache_keys(self) -> list:
        return list(self._cache.keys())

    def create_peer_connection(self, peer_id: str) -> Dict[str, Any]:
        """Create a new RTCPeerConnection (air-gapped: empty iceServers).

        Returns local SDP offer to exchange via out-of-band channel.
        Returns {'error': str, 'reason': str} if aiortc not installed.

        Per singulyar ·17 ЗАЛ: iceServers=[] (no STUN, no TURN). Works on
        LAN only (or via mDNS). For cross-network, would need TURN — but
        that defeats the air-gapped design.
        """
        if not _HAS_AIORTC:
            return {
                "error": "aiortc not installed",
                "reason": "Install with: pip install aiortc",
                "adapter_version": ADAPTER_VERSION,
            }
        # TODO v0.5: actual RTCPeerConnection + DataChannel setup via asyncio
        self._peer_id = peer_id
        self._state = "ready"
        self._reason = ""
        return {
            "peer_id": peer_id,
            "ice_servers": [],  # air-gapped
            "datachannel_name": "singulyar_p2p_data",
            "sdp_offer": "TODO: aiortc.create_offer() — v0.5 work",
            "state": "ready",
        }

    def recv(self) -> list:
        """Pull all received messages from in-memory queue.

        Returns list of received packets (deduped by (src, seq)).
        Per singulyar ·17 ЗАЛ: dedup logic is `src:seq` — every sender
        carries its own monotonic counter.
        """
        result = []
        remaining = []
        for pkt in self._recv_queue:
            src = pkt.get("src", "")
            seq = pkt.get("seq", 0)
            seen = self._seen_seqs.get(src, -1)
            if seq > seen:
                self._seen_seqs[src] = seq
                result.append(pkt)
            # else: duplicate, drop
        self._recv_queue = remaining
        return result


def default_adapter() -> WebRTCAdapter:
    return WebRTCAdapter()


def default_capabilities() -> tuple:
    return CAPABILITIES
