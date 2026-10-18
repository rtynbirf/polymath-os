# runtime/src/decree_signing.py — Decree Cryptographic Signing (ADR-0031)
#
# PROVENANCE: hash-chain (DecreeLog) proves INTEGRITY — a decree was not
# altered. A signature proves AUTHORSHIP — THIS key holder issued THIS
# decree. Without a signature, anyone with DB access could have written
# the decree; with one, the decree is attributable to the PID=1 key.
#
# Per ADR-0031:
#   - Signature covers the decree's chain hash (SHA-256 of
#     prev_hash|timestamp|decree_text), so it binds authorship to the
#     exact chain entry: text, position, and all history before it.
#   - Ed25519 (RFC 8032), PURE PYTHON — zero third-party dependencies.
#     The repo's open-source contract is "no installation required,
#     Python 3.10+"; this module keeps that promise (sovereignty).
#   - Keys: OpenSSH format (ssh-keygen compatible). The human generates:
#       ssh-keygen -t ed25519 -f ~/.polymath-os/signing-key -N ""
#     We parse the OpenSSH wire format ourselves (unencrypted keys).
#   - Signatures are stored in a SEPARATE append-only table
#     (decree_signatures) — the decrees table and its hash chain are
#     never touched. verify() of the chain stays byte-identical.
#
# Honesty rules (per ADR-0006/0007 style):
#   - verify on a decree without a signature → verified=False,
#     reason="not_signed" (never an exception, never a fake pass).
#   - tampered text → verified=False, reason="integrity_failed".
#   - wrong key / foreign signature → verified=False,
#     reason="signature_mismatch".
from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

__version__ = "v0.1.0"

# ══════════════════════════════════════════════════════════════════
# Ed25519 — RFC 8032, pure python ( twisted Edwards, extended coords )
# ══════════════════════════════════════════════════════════════════

_Q = 2 ** 255 - 19                      # field modulus
_L = 2 ** 252 + 27742317777372353535851937790883648493  # group order
_I = pow(2, (_Q - 1) // 4, _Q)          # sqrt(-1) mod q


def _inv(x: int) -> int:
    return pow(x, _Q - 2, _Q)


_D = (-121665 * _inv(121666)) % _Q      # curve constant


def _xrecover(y: int) -> int:
    xx = ((y * y - 1) * _inv(_D * y * y + 1)) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_By = (4 * _inv(5)) % _Q
_Bx = _xrecover(_By)
# base point + identity in extended coords (x, y, z, t)
_B = (_Bx % _Q, _By % _Q, 1, (_Bx * _By) % _Q)
_IDENT = (0, 1, 1, 0)


def _edwards_add(P: Tuple[int, int, int, int], Q: Tuple[int, int, int, int]):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = (y1 - x1) * (y2 - x2) % _Q
    b = (y1 + x1) * (y2 + x2) % _Q
    c = 2 * _D * t1 * t2 % _Q
    dd = 2 * z1 * z2 % _Q
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % _Q, g * h % _Q, f * g % _Q, e * h % _Q)


def _scalarmult(P, e: int):
    Q = _IDENT
    while e > 0:
        if e & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        e >>= 1
    return Q


def _point_equal(P, Q) -> bool:
    x1, y1, z1, _ = P
    x2, y2, z2, _ = Q
    return (x1 * z2 - x2 * z1) % _Q == 0 and (y1 * z2 - y2 * z1) % _Q == 0


def _point_compress(P) -> bytes:
    x, y, z, _ = P
    zi = _inv(z)
    x = x * zi % _Q
    y = y * zi % _Q
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _point_decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _Q:
        return None
    x = _xrecover(y)
    if x & 1 != sign:
        x = _Q - x
    P = (x, y, 1, x * y % _Q)
    # on-curve check: z != 0 and x*y == z*t
    if P[2] % _Q == 0 or (P[0] * P[1] - P[2] * P[3]) % _Q != 0:
        return None
    return P


def _secret_expand(seed: bytes) -> Tuple[int, bytes]:
    if len(seed) != 32:
        raise ValueError("ed25519 seed must be 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= (1 << 254)
    return a, h[32:]


def ed25519_public_key(seed: bytes) -> bytes:
    a, _ = _secret_expand(seed)
    return _point_compress(_scalarmult(_B, a))


def ed25519_sign(seed: bytes, msg: bytes) -> bytes:
    a, prefix = _secret_expand(seed)
    pub = ed25519_public_key(seed)
    r = int.from_bytes(hashlib.sha512(prefix + msg).digest(), "little") % _L
    Rs = _point_compress(_scalarmult(_B, r))
    h = int.from_bytes(hashlib.sha512(Rs + pub + msg).digest(), "little") % _L
    s = (r + h * a) % _L
    return Rs + int.to_bytes(s, 32, "little")


def ed25519_verify(pub: bytes, msg: bytes, signature: bytes) -> bool:
    if len(pub) != 32 or len(signature) != 64:
        return False
    A = _point_decompress(pub)
    if A is None:
        return False
    Rs = signature[:32]
    R = _point_decompress(Rs)
    if R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(Rs + pub + msg).digest(), "little") % _L
    sB = _scalarmult(_B, s)
    hA = _scalarmult(A, h)
    return _point_equal(sB, _edwards_add(R, hA))


# ══════════════════════════════════════════════════════════════════
# OpenSSH key format (unencrypted Ed25519) — ssh-keygen compatible
# ══════════════════════════════════════════════════════════════════

class DecreeSigningError(Exception):
    """Raised for malformed keys, missing files, invalid operations."""


def _read_ssh_string(buf: bytes, off: int) -> Tuple[bytes, int]:
    if off + 4 > len(buf):
        raise DecreeSigningError("OpenSSH wire: truncated length")
    n = int.from_bytes(buf[off:off + 4], "big")
    off += 4
    if off + n > len(buf):
        raise DecreeSigningError("OpenSSH wire: truncated string")
    return buf[off:off + n], off + n


def load_signing_key(path: str) -> Tuple[bytes, bytes]:
    """Load an unencrypted OpenSSH Ed25519 private key.

    Returns (seed, public_key) — both 32 bytes. Accepts the file produced
    by: ssh-keygen -t ed25519 -f <path> -N ""
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except OSError as e:
        raise DecreeSigningError(f"{path}: cannot read key ({e})") from e
    lines = text.splitlines()
    if (
        len(lines) < 3
        or lines[0].strip() != "-----BEGIN OPENSSH PRIVATE KEY-----"
        or lines[-1].strip() != "-----END OPENSSH PRIVATE KEY-----"
    ):
        raise DecreeSigningError(
            f"{path}: not an unencrypted OPENSSH PRIVATE KEY block"
        )
    try:
        blob = base64.b64decode("".join(lines[1:-1]))
    except Exception as e:  # noqa: BLE001
        raise DecreeSigningError(f"{path}: bad base64 ({e})") from e

    if blob[:15] != b"openssh-key-v1\x00":
        raise DecreeSigningError(f"{path}: bad magic {blob[:15]!r}")
    off = 15  # magic is raw bytes, NOT length-prefixed (OpenSSH spec)
    cipher, off = _read_ssh_string(blob, off)
    _kdf, off = _read_ssh_string(blob, off)
    _kdfopts, off = _read_ssh_string(blob, off)
    if len(blob) < off + 4:
        raise DecreeSigningError(f"{path}: truncated key count")
    nkeys = int.from_bytes(blob[off:off + 4], "big")
    off += 4
    if nkeys < 1:
        raise DecreeSigningError(f"{path}: no keys in block")
    if cipher not in (b"none", b""):
        raise DecreeSigningError(
            f"{path}: encrypted keys unsupported (cipher={cipher!r}); "
            "regenerate with -N ''"
        )
    _pub_wire, off = _read_ssh_string(blob, off)  # outer public copy
    priv_section, off = _read_ssh_string(blob, off)

    check1 = int.from_bytes(priv_section[0:4], "big")
    check2 = int.from_bytes(priv_section[4:8], "big")
    if check1 != check2:
        raise DecreeSigningError(f"{path}: checkint mismatch (corrupt key)")
    poff = 8
    algo, poff = _read_ssh_string(priv_section, poff)
    if algo != b"ssh-ed25519":
        raise DecreeSigningError(
            f"{path}: expected ssh-ed25519, got {algo.decode(errors='replace')}"
        )
    _pub_a, poff = _read_ssh_string(priv_section, poff)
    priv_blob, poff = _read_ssh_string(priv_section, poff)
    if len(priv_blob) != 64:
        raise DecreeSigningError(
            f"{path}: ed25519 private section must be 64 bytes, "
            f"got {len(priv_blob)}")
    seed = priv_blob[:32]
    return seed, ed25519_public_key(seed)


def parse_public_key(source) -> bytes:
    """Parse an OpenSSH public key: a file path OR a 'ssh-ed25519 AAAA...'
    line. Returns the raw 32-byte key.
    """
    text = source
    if isinstance(source, (str, bytes)) and os.sep in str(source) and "\n" not in str(source):
        p = os.path.expanduser(str(source))
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                text = f.read().strip()
    text = str(text).strip()
    parts = text.split()
    if not parts:
        raise DecreeSigningError("empty public key")
    b64 = parts[1] if parts[0] == "ssh-ed25519" and len(parts) >= 2 else parts[0]
    try:
        wire = base64.b64decode(b64)
    except Exception as e:  # noqa: BLE001
        raise DecreeSigningError(f"bad public key base64 ({e})") from e
    algo, off = _read_ssh_string(wire, 0)
    if algo != b"ssh-ed25519":
        raise DecreeSigningError(
            f"expected ssh-ed25519, got {algo.decode(errors='replace')}"
        )
    key, off = _read_ssh_string(wire, off)
    if len(key) != 32:
        raise DecreeSigningError("ed25519 public key must be 32 bytes")
    return key


def _default_key_path() -> str:
    return os.environ.get("POLYMATH_OS_SIGNING_KEY") \
        or os.path.expanduser("~/.polymath-os/signing-key")


# ══════════════════════════════════════════════════════════════════
# Signature store — separate append-only table (chain untouched)
# ══════════════════════════════════════════════════════════════════

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decree_signatures (
    sig_seq    INTEGER PRIMARY KEY AUTOINCREMENT,
    decree_seq INTEGER NOT NULL,
    alg        TEXT NOT NULL DEFAULT 'ed25519',
    pubkey     TEXT NOT NULL,
    signature  TEXT NOT NULL,
    signer_id  TEXT NOT NULL DEFAULT 'pid1',
    signed_at  TEXT NOT NULL
);
"""


def _ensure_table(decree_log) -> None:
    decree_log.db.execute(_SCHEMA)
    decree_log.db.commit()


def _signing_message(prev_hash: str, timestamp: str, text: str,
                     decree_hash: str) -> bytes:
    """Bytes covered by the signature: the decoded chain hash.

    The hash is already SHA-256(prev_hash|timestamp|decree_text) — signing
    the 32 raw bytes binds authorship to this exact entry AND its position
    in the chain (any tamper with text/history changes the hash).
    """
    return bytes.fromhex(decree_hash)


def sign_decree(decree_log, seq: int, key_path: Optional[str] = None,
                signer_id: str = "pid1") -> Dict[str, Any]:
    """Sign an existing decree with the PID=1 Ed25519 key (ADR-0031).

    The signature is appended to decree_signatures (append-only); the
    decree itself and its chain are untouched.
    """
    key_path = key_path or _default_key_path()
    seed, pub = load_signing_key(key_path)
    _ensure_table(decree_log)

    row = decree_log.db.execute(
        "SELECT seq, prev_hash, timestamp, decree_text, decree_hash "
        "FROM decrees WHERE seq = ?", (seq,)
    ).fetchone()
    if row is None:
        raise DecreeSigningError(f"decree #{seq} not found")
    got_seq, prev_hash, ts, text, dhash = row
    msg = _signing_message(prev_hash, ts, text, dhash)
    sig = ed25519_sign(seed, msg)

    signed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = decree_log.db.execute(
        "INSERT INTO decree_signatures "
        "(decree_seq, alg, pubkey, signature, signer_id, signed_at) "
        "VALUES (?, 'ed25519', ?, ?, ?, ?)",
        (seq, pub.hex(), sig.hex(), signer_id, signed_at),
    )
    decree_log.db.commit()
    return {
        "sig_seq": cur.lastrowid,
        "decree_seq": seq,
        "alg": "ed25519",
        "pubkey": pub.hex(),
        "signature": sig.hex(),
        "signer_id": signer_id,
        "signed_at": signed_at,
    }


def issue_signed(decree_log, text: str, key_path: Optional[str] = None,
                 category: str = "directive", scope: str = "all",
                 classification: str = "public", signer_id: str = "pid1"
                 ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Issue a decree AND sign it in one step (the ADR-0031 flow)."""
    decree = decree_log.issue(text=text, category=category, scope=scope,
                              classification=classification)
    sig = sign_decree(decree_log, decree["seq"], key_path, signer_id)
    return decree, sig


def verify_decree_signature(decree_log, seq: int,
                            pubkey_path=None) -> Dict[str, Any]:
    """Verify all signatures on decree #seq. Honest result dict, no throws
    for cryptographic mismatches; malformed setup raises DecreeSigningError.
    """
    row = decree_log.db.execute(
        "SELECT seq, prev_hash, timestamp, decree_text, decree_hash "
        "FROM decrees WHERE seq = ?", (seq,)
    ).fetchone()
    if row is None:
        return {"seq": seq, "verified": False, "reason": "decree_not_found"}
    got_seq, prev_hash, ts, text, dhash = row

    # Step 1 — INTEGRITY: the chain entry must still hash to itself.
    recomputed = decree_log._hash_decree(prev_hash, ts, text)
    if recomputed != dhash:
        return {"seq": seq, "verified": False,
                "reason": "integrity_failed",
                "detail": "decree hash does not match its chain position"}

    _ensure_table(decree_log)
    sigs = decree_log.db.execute(
        "SELECT sig_seq, alg, pubkey, signature, signer_id, signed_at "
        "FROM decree_signatures WHERE decree_seq = ? ORDER BY sig_seq",
        (seq,),
    ).fetchall()
    if not sigs:
        return {"seq": seq, "verified": False, "reason": "not_signed",
                "detail": "no signatures recorded for this decree"}

    msg = _signing_message(prev_hash, ts, text, dhash)
    expected_pub = None
    if pubkey_path is not None:
        expected_pub = parse_public_key(pubkey_path)

    results = []
    for sig_seq, alg, pub_hex, sig_hex, signer_id, signed_at in sigs:
        if alg != "ed25519":
            results.append({"sig_seq": sig_seq, "verified": False,
                            "reason": "unsupported_alg"})
            continue
        pub = bytes.fromhex(pub_hex)
        sig = bytes.fromhex(sig_hex)
        ok = ed25519_verify(pub, msg, sig)
        if ok and expected_pub is not None and pub != expected_pub:
            ok = False  # valid sig, but by a different key than demanded
        results.append({
            "sig_seq": sig_seq,
            "verified": ok,
            "reason": "ok" if ok else "signature_mismatch",
            "signer_id": signer_id,
            "signed_at": signed_at,
            "pubkey_sha256": hashlib.sha256(pub).hexdigest()[:16],
        })

    return {
        "seq": seq,
        "verified": any(r["verified"] for r in results),
        "reason": "ok" if any(r["verified"] for r in results)
                  else results[0]["reason"],
        "signatures": results,
    }


def verify_all(decree_log, pubkey_path=None) -> List[Dict[str, Any]]:
    """Verify signatures on every signed decree (unsigned ones are
    reported honestly as not_signed — provenance gaps, not errors).
    """
    _ensure_table(decree_log)
    seqs = [r[0] for r in decree_log.db.execute(
        "SELECT DISTINCT decree_seq FROM decree_signatures ORDER BY decree_seq"
    ).fetchall()]
    return [verify_decree_signature(decree_log, s, pubkey_path) for s in seqs]


def provenance_report(decree_log, pubkey_path=None) -> Dict[str, Any]:
    """Human-readable provenance: per-decree signed/unsigned status."""
    _ensure_table(decree_log)
    total = decree_log.count()
    signed = [verify_decree_signature(decree_log, s, pubkey_path)
              for s in range(1, total + 1)]
    ok = sum(1 for r in signed if r["verified"])
    return {
        "decrees_total": total,
        "decrees_signed": ok,
        "all_signed": ok == total and total > 0,
        "details": signed,
    }
