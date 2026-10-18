# ADR-0036 — Proven-Based Audit Framework (4-Proof Verification)

**Date:** 2026-10-20
**Status:** Accepted (provenance layer)
**Tags:** audit, provenance, verification, v3.20.0-candidate
**Deciders:** @USER (Командир корабля)
**Extends:** ADR-0006 (Falsifiable Self-Properties), ADR-0019 (Observability First), ADR-0021 (Decree as Supreme Law), ADR-0029 (СИНГУЛЯР Security Model)

## Context

Every security-critical system has the same problem: **how does an
external auditor trust the audit output itself?**

A typical audit answers: "Is the system in state X?" The answer is
a single boolean: pass / fail. But that boolean is computed by the
*same code* that's being audited — and stored in the *same database*
as the evidence. An attacker who can tamper with the decree log can
also tamper with the audit report.

Polymath-os has four independent pillars of tamper-evidence already
built (ADR-0021 hash chain, ADR-0029 §9 external trust anchor, the
in-progress Ed25519 signatures per ADR-0034, and ADR-0019 evidence
ledger). Each pillar catches a *different class* of tampering:

| Pillar | Catches | Built in |
|--------|---------|----------|
| Hash-chain integrity | Single-row edit of the SQLite db | v3.2.0 (ADR-0021) |
| External trust anchor | Whole-db rebuild from scratch | v3.x.0 (ADR-0029 §9) |
| Ed25519 signatures | Forged decree provenance | Proposed (ADR-0034) |
| Evidence Ledger completeness | Missing audit events (silent failures) | v3.0.0 (ADR-0019) |

But each pillar has known blind spots:

1. **Hash chain** doesn't catch a rebuild. If an attacker has write
   access to the SQLite file, they can re-execute the entire
   issue() sequence from scratch and produce a valid (but different)
   hash chain. Internal integrity preserved, but provenance lost.

2. **Trust anchor** only catches rebuilds *if the auditor refreshes
   the anchor out-of-band before comparing. If the attacker controls
   both the db AND the anchor file (both on the same filesystem),
   they can rebuild both consistently.

3. **Ed25519 signatures** don't catch missing decrees. If an attacker
   deletes decree #5 from the middle of the log (and re-hashes #6+ to
   fix the chain), the signatures on #6+ are still valid (they were
   signed over the original `prev_hash` field which... wait, they
   were signed over `(seq, prev_hash, timestamp, text)` and the
   attacker has to re-sign with a forged key. So actually Ed25519
   DOES catch this — IF the auditor has the original public key.
   But if the attacker can also rotate the public key (e.g. by
   tampering `.well-known/agent.json`), the audit passes.

4. **Evidence Ledger** doesn't directly verify the decree log. It
   records execution events (INTENT_ACCEPTED, DECREE_BLOCK, etc.)
   but doesn't prove the decrees themselves are intact. However, a
   gap in the ledger (e.g. a DECREE_BLOCK event for decree #5 that
   should have fired but didn't) indicates either a tampered decree
   log OR a malfunctioning enforcement layer — both are problems.

### The synthesis

No single pillar catches every attack. But the **intersection** of
all four pillars is much stronger than any one:

- An attacker who rebuilds the SQLite db is caught by the trust
  anchor (assuming the auditor published the anchor to read-only
  media out-of-band).
- An attacker who forges the anchor file is caught by Ed25519
  signature verification against the human's published public key
  (assuming the auditor fetched the key from a trusted source).
- An attacker who rotates the public key is caught by the human
  themselves (the human is PID=1; if the human didn't issue a key
  rotation decree, the rotation is invalid).
- An attacker who deletes decrees is caught by the ledger (a
  DECREE_BLOCK event for a now-missing decree proves the decree
  once existed and was enforced).

The **Proven-Based Audit Framework** codifies this synthesis: the
audit runs all four proofs, returns a structured result, and
produces a human-readable report. The audit is **PASS** only if all
four proofs that are *available in the environment* return
`verified=True` (skipped proofs don't fail the audit, but they are
clearly marked as gaps).

## Decision

Implement a `ProvenAudit` class in `runtime/src/proven_audit.py`
that runs four proofs and produces a structured + human-readable
report.

### The four proofs

#### Proof 1: Hash-chain integrity

**Module:** `runtime/src/decree_log.py` (existing, ADR-0021)
**Method:** `decree_log.verify()` → `bool`

**Catches:** any single-row edit of the SQLite db. If any decree's
`prev_hash`, `decree_hash`, or text has been modified after the
fact, `_verify_chain()` raises `DecreeIntegrityError` and `verify()`
returns `False`.

**Returns:** `{verified: bool, detail: str}` — `detail` is a
human-readable description including the count of decrees verified
and the genesis hash (or the broken-at-seq marker on failure).

#### Proof 2: Trust anchor match (IAEA pattern)

**Module:** `runtime/src/trust_anchor.py` (existing, ADR-0029 §9)
**Method:** `verify_trust_anchor(decree_log, anchor_path=None)` → `dict`

**Catches:** whole-db rebuild. The external anchor file contains
the SHA-256 hash of the last decree as observed at publication time.
If someone rebuilds the db from scratch (re-hashing every decree),
the anchor file (stored out-of-band: printout, USB, lawyer,
blockchain) won't match.

**Returns:** `{verified: bool, detail: str, anchor_seq: int, ...}` —
the `detail` includes the truncated hashes for visual comparison
and the message field from `verify_trust_anchor()` (e.g. "trust
anchor verified — no tampering detected" or "TAMPER DETECTED —
hash mismatch at decree #N").

#### Proof 3: Ed25519 signatures (cryptographic provenance)

**Module:** `runtime/src/decree_signatures.py` (proposed in ADR-0034)
**Method:** `verify_decree_signature(decree_row, signature_hex, public_key)` → `bool`

**Catches:** forged decree provenance. Each decree is signed by the
issuing human's Ed25519 private key at issue time. An attacker who
rebuilds the db without the private key cannot produce valid
signatures on the re-issued decrees.

**Status:** `verified` if the module is available AND every decree
in the log has a valid signature against the configured public key;
`skipped` if the module is not available (env doesn't have
`decree_signatures.py` or the public key is missing); `failed` if
the module is available but a decree's signature is invalid.

**Returns:** `{verified: bool, status: str, detail: str}` — `detail`
explains which decrees (if any) have invalid signatures and why.

#### Proof 4: Evidence Ledger completeness

**Module:** `runtime/src/sqlite_ledger.py` (existing, ADR-0019)
**Method:** `ledger.verify()` → `bool` + `ledger.events` count

**Catches:** missing audit events. The Evidence Ledger records every
state transition in the runtime. If the ledger's own hash chain is
broken OR the event count is implausibly low relative to the decree
count (e.g. 100 decrees enforced but only 3 events in the ledger),
something is wrong.

**Returns:** `{verified: bool, event_count: int, detail: str}` —
`detail` is the human-readable status (chain valid/invalid + count).

### Result schema

`ProvenAudit.verify_4_proofs()` returns:

```python
{
    "proofs": {
        "hash_chain":   {"verified": bool, "status": str, "detail": str},
        "trust_anchor": {"verified": bool, "status": str, "detail": str, ...},
        "signatures":   {"verified": bool, "status": str, "detail": str},
        "ledger":       {"verified": bool, "status": str, "detail": str, "event_count": int},
    },
    "all_verified": bool,   # True iff NO proof is "failed" (skipped is OK)
    "summary": str,         # one-line summary, e.g. "3/4 proofs verified (1 skipped)"
}
```

Where `status` ∈ `{"verified", "failed", "skipped"}`:
- `verified` — proof ran and passed
- `failed` — proof ran and failed (audit FAIL)
- `skipped` — proof could not run (missing module / missing key / missing ledger) — does NOT fail the audit, but is reported as a gap

`all_verified` semantics: **True iff no proof is `failed`**. A skipped
proof is a non-blocking gap (the human can address it later by
installing the missing module), but a failed proof is a hard audit
failure (someone tampered with the system).

### Human-readable report

`ProvenAudit.audit_report()` returns a multi-line string suitable for
display in:
- The CLI (e.g. `make verify` summary)
- The Decree Portal (HTML rendering of the `<pre>` block)
- An external auditor's report file

Format:

```
=== Proven-Based Audit Report (ADR-0036) ===
Generated: 2026-10-20T12:34:56Z
Decree log: ~/.polymath-os/decrees.db
Total decrees: 8

PROOF 1: HASH-CHAIN INTEGRITY (ADR-0021)
  Status: VERIFIED
  Detail: SHA-256 hash chain valid across 8 decrees; genesis=0000...0000

PROOF 2: TRUST ANCHOR MATCH (ADR-0029 §9, IAEA pattern)
  Status: VERIFIED
  Detail: External anchor matches decree #8 — no tampering detected

PROOF 3: ED25519 SIGNATURES (ADR-0034)
  Status: SKIPPED
  Detail: decree_signatures module not available in this environment
  Hint:   install PyNaCl + decree_signatures.py to enable Proof 3

PROOF 4: EVIDENCE LEDGER COMPLETENESS (ADR-0019)
  Status: VERIFIED
  Detail: 12 events in ledger; hash chain valid

SUMMARY: 3/4 proofs verified (1 skipped). Audit: PASS (with gaps).
```

## Consequences

**Positive:**
- **Independent pillars** — each proof uses a different module /
  different storage / different cryptographic primitive. An attacker
  who compromises one pillar (e.g. the SQLite file) is still caught
  by another (the external anchor file on a USB stick).
- **Fail-closed per ADR-0006** — a `failed` proof fails the audit
  hard. There is no "soft fail" mode.
- **Skipped ≠ failed** — the audit distinguishes between "this proof
  can't run in this environment" (skipped) and "this proof ran and
  failed" (failed). This makes the audit usable in environments
  where some pillars aren't yet installed (e.g. an instance without
  Ed25519 keys still gets a meaningful audit on the other three
  proofs), while preserving the integrity of the pass/fail decision.
- **Human-readable** — the audit report is suitable for direct
  display in the Decree Portal or CLI output. No JSON parsing
  required for the human to understand the result.
- **Composes with `make verify`** — the audit can be added as a
  future `make verify` claim (e.g. claim #26: "ProvenAudit:
  all_available_proofs_verified"). The framework is designed so
  that adding a claim doesn't require new infrastructure — it just
  calls `ProvenAudit(dl).verify_4_proofs()["all_verified"]`.
- **Forward-compatible** — new proofs (e.g. Proof 5: SLSA build
  provenance per ADR-0013, Proof 6: SBOM verification per ADR-0020)
  can be added by extending the `proofs` dict and the
  `audit_report()` formatter. The 4-proof structure is a starting
  point, not a hard limit.

**Negative:**
- **`all_verified` doesn't catch "everything skipped"** — if all
  four proofs are skipped (e.g. in a fresh CI environment with no
  decree db, no anchor, no signatures module, no ledger), the audit
  returns `all_verified=True` because no proof failed. This is
  technically correct per the spec (skipped is non-blocking) but
  potentially misleading. Mitigated by the `summary` field
  explicitly stating "4/4 proofs skipped — audit INCONCLUSIVE,
  install at least one pillar to enable verification."
- **No automated cross-instance audit** — this framework audits ONE
  instance. Cross-instance audit (comparing anchors across a P2P
  mesh per ADR-0034) is a separate concern, addressed in ADR-0034's
  anchor-compare step.
- **Ledger "completeness" is heuristic** — Proof 4 doesn't have a
  formal model of "expected event count for N decrees". It checks
  the ledger's own hash chain (catches tampering) and the event
  count (catches obvious loss — e.g. 0 events with 100 decrees
  means enforcement was bypassed). It does NOT prove that EVERY
  enforcement decision was logged — that requires a stronger
  invariant (e.g. a per-decide counter that must equal the number
  of `check_compliance` calls). Left as future work.

**Neutral:**
- The four-proof count is not magical. Future versions may have 3
  (if Ed25519 is dropped) or 6 (if SLSA + SBOM are added). The
  framework's structure (dict of proof_name → {verified, status,
  detail}, plus all_verified + summary) accommodates any count.
- The `summary` string is the only "loose" field — it's a
  human-readable sentence that may evolve. The structured
  `proofs` dict is the stable machine-readable contract.

## Alternatives considered

### Alternative A: Single composite proof

Combine all four pillars into one `verify()` call returning a single
bool, without per-proof detail.

**Rejected because:** the detail matters. An auditor who sees
`all_verified=False` needs to know WHY — was it the hash chain? The
trust anchor? The signatures? The ledger? Each failure mode implies
a different attack and a different remediation. A single bool throws
away the diagnostic information.

### Alternative B: Merkle-tree root comparison

Compute a Merkle root over all decrees and compare it to a published
root (like a blockchain header).

**Rejected for now:** Merkle roots are useful for selective disclosure
(prove decree #N is in the log without revealing the whole log). But
polymath-os's audit model assumes the auditor has full access to
the decree log (the human audits their own system). Merkle roots are
relevant for *cross-instance* audits (ADR-0034 P2P sync), not for
*internal* audits. May revisit when implementing ADR-0034's
anchor-compare step.

### Alternative C: Zero-knowledge proofs

Use zk-SNARKs to prove the audit passes without revealing the decrees.

**Rejected because:** adds enormous complexity (trusted setup,
proving keys, verifier code), and the privacy benefit is minimal
(the human auditing their own system doesn't need privacy from
themselves). zk-SNARKs are interesting for federated audits where
peer A wants to prove to peer B that A's log is intact without
revealing the decrees — but that's a v4.0+ concern, not v3.x.

### Alternative D: External audit service

Send the decree log + anchor to a third-party auditor (e.g. a notary
service) and trust their verdict.

**Rejected because:** re-introduces centralization — the sovereignty
story's core rejection. The human IS the auditor. The framework
provides the tools; the human runs them. A future *optional*
third-party notarization service (where the human *chooses* to
publish their anchor to a notary) is compatible with this framework
— it's just another trust anchor publication medium per ADR-0029 §9.

## Verification

- `runtime/tests/test_proven_audit.py` — 4 tests:
  1. `test_verify_hash_chain` — Proof 1 returns verified=True on a
     valid log, False on a tampered log.
  2. `test_verify_trust_anchor` — Proof 2 returns verified=True when
     the anchor matches, False when the anchor is missing or tampered.
  3. `test_all_proofs_returned` — `verify_4_proofs()` returns a dict
     with all four proof keys (hash_chain, trust_anchor, signatures,
     ledger), plus `all_verified` and `summary`. The `signatures`
     proof is `skipped` in environments without the
     `decree_signatures` module — this is expected and documented.
  4. `test_audit_report_readable` — `audit_report()` returns a
     non-empty string containing the four proof names and the
     summary line. The string must be parseable by a human (no
     JSON, no binary).

- Manual: `python3 -c "from runtime.src.proven_audit import ProvenAudit;
  from decree_log import DecreeLog; dl=DecreeLog('~/.polymath-os/decrees.db');
  print(ProvenAudit(dl).audit_report())"` — should print a
  readable report.

## References

- ADR-0006 (Falsifiable Self-Properties) — every claim must be testable
- ADR-0019 (Observability First) — Evidence Ledger (Proof 4)
- ADR-0021 (Decree as Supreme Law) — hash chain (Proof 1)
- ADR-0029 (СИНГУЛЯР Security Model) — §9 IAEA pattern (Proof 2),
  §10 Estonia X-Road pattern (Proof 3 inspiration)
- ADR-0034 (P2P Decree Mesh) — Ed25519 signatures (Proof 3)
- `runtime/src/decree_log.py` — `DecreeLog.verify()` (Proof 1)
- `runtime/src/trust_anchor.py` — `verify_trust_anchor()` (Proof 2)
- `runtime/src/sqlite_ledger.py` — `SQLiteEvidenceLedger.verify()` (Proof 4)
- `runtime/src/proven_audit.py` — implementation
- `runtime/tests/test_proven_audit.py` — tests

## Self-reference

This ADR is itself auditable: any future amendment to the four-proof
structure (e.g. adding Proof 5) is a decree-driven amendment per
ADR-0026 — the human issues a decree of category `amendment` saying
"supersede ADR-0036 with ADR-00XX, adding Proof 5: SLSA build
provenance". The ProvenAudit class will then be updated to call the
new proof, and the audit_report format extended.

The framework audits itself: the `audit_report()` output is the
artifact an external auditor would inspect. If the report says
"3/4 verified, 1 skipped" and the auditor knows that the environment
should have all 4 pillars installed, the audit itself is the
evidence of a gap. The framework's honesty about skipped proofs is
its own falsifiability per ADR-0006.
