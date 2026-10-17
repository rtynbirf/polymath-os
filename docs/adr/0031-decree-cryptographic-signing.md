# ADR-0031 — Decree Cryptographic Signing (Provenance)

**Date:** 2026-10-17
**Status:** Accepted
**Tags:** decree, provenance, ed25519, v3.20.0
**Deciders:** @USER
**Supersedes:** None (extends ADR-0021 Decree as Supreme Law, ADR-0029 §9 Trust Anchor)

## Context

Per ADR-0021, the DecreeLog is append-only, immutable, hash-chained.
The chain proves **INTEGRITY**: a decree was not altered after issuance,
and verify() detects any tampering with the text or the chain history.

But integrity is not authorship. Anyone with filesystem access to the
SQLite database could have INSERTED a decree — the chain would attest
that it was issued "at some point" by "someone". For the human's word
to be legally attributable (who issued this?), the system needs a
signature from a key only the human controls:

| Without signing key | With signing key |
|---------------------|------------------|
| Hash-chain = integrity (decree not altered) | + Signature = authorship (decree issued by PID=1) |
| Anyone with DB access could issue a decree | Only the key holder can issue attributable decrees |
| A decree is indistinguishable from an AI-generated one | A decree is cryptographically attributable to the human |
| ADR-0031 — not implemented | ADR-0031 — implemented |

Constraints from the sovereignty contract (README: "no installation
required, Python 3.10+"): no third-party crypto library may be added.
The key format must be what the human already has from `ssh-keygen`.

## Decision

Implement **decree cryptographic signing** in
`runtime/src/decree_signing.py`:

1. **Algorithm:** Ed25519 (RFC 8032), implemented in **pure Python
   stdlib** (hashlib + int arithmetic). No `cryptography`, no `nacl`.
   Signing a decree takes milliseconds — performance is irrelevant at
   decree volumes.

2. **Keys:** OpenSSH format, `ssh-keygen` compatible:

   ```bash
   ssh-keygen -t ed25519 -f ~/.polymath-os/signing-key -N ""
   ```

   The module parses the unencrypted OpenSSH wire format itself
   (`openssh-key-v1` container, `ssh-ed25519` algo). Encrypted keys are
   rejected with an honest error (regenerate with `-N ''`).

3. **What is signed:** the decree's **chain hash** — the raw 32 bytes
   of SHA-256(prev_hash|timestamp|decree_text). This binds authorship
   to the exact entry AND its position in the chain: altering the text,
   reordering history, or rebuilding the chain all change the hash and
   invalidate the signature.

4. **Storage:** signatures live in a separate append-only table
   `decree_signatures (sig_seq, decree_seq, alg, pubkey, signature,
   signer_id, signed_at)` in the same SQLite file. The `decrees` table
   and its chain are never touched — `verify()` stays byte-identical,
   the trust anchor (ADR-0029 §9) is unaffected.

5. **API (honesty rules per ADR-0006/0007 style):**

   - `issue_signed(dl, text, key_path, ...)` — issue + sign in one step
   - `sign_decree(dl, seq, key_path)` — sign an existing decree
   - `verify_decree_signature(dl, seq, pubkey_path=None)` — returns a
     result dict, never throws on cryptographic mismatch:
     `verified=False, reason=` one of `integrity_failed` (text tampered),
     `not_signed` (no signatures), `signature_mismatch` (wrong key),
     `decree_not_found`, `unsupported_alg`
   - `verify_all(dl)` / `provenance_report(dl)` — per-decree
     signed/unsigned status; unsigned decrees are provenance gaps,
     reported honestly, not errors
   - `sign_decree` is provenance only — it does NOT count toward
     `required_signatures` (N-of-M thresholds stay v3.18.0 co-signature
     semantics; the two concepts are deliberately independent)

6. **Verification order:** integrity first (recompute chain hash from
   the stored row), then signature over the recomputed hash. A signature
   over a tampered decree can never verify.

## Consequences

**Positive:**
- Decrees are attributable: provenance_report() shows exactly which
  decrees the PID=1 key signed
- A future adversarial agent (or a compromised adapter) cannot forge a
  signed decree without the private key
- Zero new dependencies; works on a bare Python 3.10 install
- make verify claim #26 pins the implementation contract (pure stdlib,
  RFC 8032 vectors in the test suite)

**Negative:**
- Pure-python Ed25519 is slow compared to a C implementation (~ms per
  op) — irrelevant at decree volumes, documented honestly
- The private key must be protected by the human (it is outside the
  system, per ADR-0022: the human is PID=1, keys never enter the repo)
- Losing the key loses the ability to sign new decrees; past signatures
  remain verifiable with the public key alone

**Neutral:**
- Multi-signature (several keys on one decree) is supported naturally —
  each signature is a row; verification demands one match for
  `verified=True`, or a specific key via `pubkey_path`
