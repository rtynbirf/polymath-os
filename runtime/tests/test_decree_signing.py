# runtime/tests/test_decree_signing.py — ADR-0031 (decree cryptographic signing)
#
# Hermetic: keys are generated into tmpdirs (OpenSSH format, written by the
# test helper itself). The RFC 8032 test vectors pin the pure-python Ed25519
# to the standard. An interop test (skipped when `cryptography` is absent)
# cross-checks our implementation against the reference library.
import base64
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
for _p in (str(_SRC), str(_HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from decree_log import DecreeLog
from decree_signing import (  # noqa: E402
    DecreeSigningError,
    ed25519_public_key,
    ed25519_sign,
    ed25519_verify,
    issue_signed,
    load_signing_key,
    parse_public_key,
    provenance_report,
    sign_decree,
    verify_all,
    verify_decree_signature,
)

try:  # optional interop reference (NOT a runtime dependency)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    HAS_CRYPTO = True
except ImportError:  # pragma: no cover
    HAS_CRYPTO = False


# ── helpers: OpenSSH key files without ssh-keygen ─────────────────
def _ssh_string(b: bytes) -> bytes:
    return len(b).to_bytes(4, "big") + b


def _openssh_private_bytes(seed: bytes, pub: bytes, comment: str = "t") -> bytes:
    blob = b"openssh-key-v1\x00"
    blob += _ssh_string(b"none") + _ssh_string(b"none") + _ssh_string(b"")
    blob += (1).to_bytes(4, "big")
    pubwire = _ssh_string(b"ssh-ed25519") + _ssh_string(pub)
    blob += _ssh_string(pubwire)
    check = os.urandom(4)
    priv = check + check
    priv += _ssh_string(b"ssh-ed25519") + _ssh_string(pub)
    priv += _ssh_string(seed + pub) + _ssh_string(comment.encode())
    pad = 1
    while len(priv) % 8 != 0:
        priv += bytes([pad])
        pad += 1
    blob += _ssh_string(priv)
    b64 = base64.b64encode(blob).decode()
    lines = [b64[i:i + 70] for i in range(0, len(b64), 70)]
    return "-----BEGIN OPENSSH PRIVATE KEY-----\n" + "\n".join(lines) \
        + "\n-----END OPENSSH PRIVATE KEY-----\n"


def _write_keypair(tmp: str, name: str) -> tuple:
    seed = os.urandom(32)
    pub = ed25519_public_key(seed)
    priv_path = os.path.join(tmp, name)
    with open(priv_path, "w", encoding="utf-8") as f:
        f.write(_openssh_private_bytes(seed, pub))
    pub_path = os.path.join(tmp, name + ".pub")
    publine = "ssh-ed25519 " + base64.b64encode(
        _ssh_string(b"ssh-ed25519") + _ssh_string(pub)).decode() + " test\n"
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write(publine)
    return priv_path, pub_path


class Ed25519CoreTests(unittest.TestCase):
    """RFC 8032 test vectors — the standard pins the math."""

    def test_rfc8032_vector_1_empty_message(self):
        seed = bytes.fromhex(
            "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        pub = bytes.fromhex(
            "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        sig = ed25519_sign(seed, b"")
        self.assertEqual(ed25519_public_key(seed), pub)
        self.assertEqual(
            sig.hex(),
            "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901"
            "555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a1"
            "00b")
        self.assertTrue(ed25519_verify(pub, b"", sig))

    def test_rfc8032_vector_2_two_octets(self):
        seed = bytes.fromhex(
            "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
        pub = bytes.fromhex(
            "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
        sig = ed25519_sign(seed, b"\x72")
        self.assertEqual(ed25519_public_key(seed), pub)
        self.assertTrue(ed25519_verify(pub, b"\x72", sig))

    def test_verify_rejects_tampered_message(self):
        seed = os.urandom(32)
        pub = ed25519_public_key(seed)
        sig = ed25519_sign(seed, b"decree A")
        self.assertFalse(ed25519_verify(pub, b"decree B", sig))

    def test_verify_rejects_wrong_key_and_bad_sig(self):
        seed_a, seed_b = os.urandom(32), os.urandom(32)
        sig = ed25519_sign(seed_a, b"msg")
        self.assertFalse(ed25519_verify(ed25519_public_key(seed_b), b"msg", sig))
        bad = bytearray(sig)
        bad[0] ^= 0x01
        self.assertFalse(ed25519_verify(
            ed25519_public_key(seed_a), b"msg", bytes(bad)))


class OpenSSHKeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.priv, self.pub = _write_keypair(self.tmp, "k1")

    def test_load_roundtrip(self):
        seed, pub = load_signing_key(self.priv)
        self.assertEqual(len(seed), 32)
        self.assertEqual(ed25519_public_key(seed), pub)

    def test_publine_parse_from_file_and_inline(self):
        line = open(self.pub).read().strip()
        from_file = parse_public_key(self.pub)
        inline = parse_public_key(line)
        _, pub = load_signing_key(self.priv)
        self.assertEqual(from_file, pub)
        self.assertEqual(inline, pub)

    def test_missing_file_raises(self):
        with self.assertRaises(DecreeSigningError):
            load_signing_key(os.path.join(self.tmp, "nope"))

    def test_garbage_file_raises(self):
        p = os.path.join(self.tmp, "junk")
        open(p, "w").write("hello world\n")
        with self.assertRaises(DecreeSigningError):
            load_signing_key(p)

    def test_pem_like_wrong_header_raises(self):
        p = os.path.join(self.tmp, "pem")
        open(p, "w").write(
            "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----\n")
        with self.assertRaises(DecreeSigningError):
            load_signing_key(p)


class DecreeSigningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = str(Path(self.tmp) / "decrees.db")
        self.priv, self.pub = _write_keypair(self.tmp, "pid1")

    def _dl(self):
        return DecreeLog(self.db)

    def test_issue_signed_verifies(self):
        dl = self._dl()
        decree, sig = issue_signed(dl, "never use Google DNS",
                                   key_path=self.priv, category="prohibition")
        self.assertEqual(decree["seq"], 1)
        res = verify_decree_signature(dl, 1, pubkey_path=self.pub)
        self.assertTrue(res["verified"], res)
        self.assertEqual(res["reason"], "ok")
        dl.close()

    def test_sign_existing_decree(self):
        dl = self._dl()
        d = dl.issue(text="human is PID=1", category="law")
        sig = sign_decree(dl, d["seq"], key_path=self.priv)
        self.assertEqual(sig["decree_seq"], d["seq"])
        res = verify_decree_signature(dl, d["seq"], pubkey_path=self.pub)
        self.assertTrue(res["verified"])
        self.assertTrue(dl.verify(), "chain must stay intact after signing")
        dl.close()

    def test_unsigned_decree_is_not_signed(self):
        dl = self._dl()
        d = dl.issue(text="observe: clock skew", category="observation")
        res = verify_decree_signature(dl, d["seq"])
        self.assertFalse(res["verified"])
        self.assertEqual(res["reason"], "not_signed")
        dl.close()

    def test_tampered_text_fails_integrity(self):
        dl = self._dl()
        issue_signed(dl, "allow only local DNS", key_path=self.priv)
        # DB-level tamper: rewrite the text in place (breaks chain hash)
        dl.db.execute(
            "UPDATE decrees SET decree_text='allow ANY DNS' WHERE seq=1")
        dl.db.commit()
        res = verify_decree_signature(dl, 1, pubkey_path=self.pub)
        self.assertFalse(res["verified"])
        self.assertEqual(res["reason"], "integrity_failed")
        dl.close()

    def test_foreign_key_is_reported_when_demanded(self):
        dl = self._dl()
        priv_b, pub_b = _write_keypair(self.tmp, "attacker")
        issue_signed(dl, "law one", key_path=self.priv)
        self.assertTrue(
            verify_decree_signature(dl, 1, pubkey_path=self.pub)["verified"])
        res_b = verify_decree_signature(dl, 1, pubkey_path=pub_b)
        self.assertFalse(res_b["verified"])
        self.assertEqual(res_b["reason"], "signature_mismatch")
        # the attacker's own key pair must NOT validate either
        with self.assertRaises(DecreeSigningError):
            load_signing_key(priv_b), parse_public_key(priv_b)
        dl.close()

    def test_two_signatures_both_recorded_append_only(self):
        dl = self._dl()
        priv2, pub2 = _write_keypair(self.tmp, "cosigner")
        d = dl.issue(text="dual-sig law", category="law")
        sign_decree(dl, d["seq"], key_path=self.priv, signer_id="pid1")
        sign_decree(dl, d["seq"], key_path=priv2, signer_id="cosigner")
        res = verify_decree_signature(dl, d["seq"])
        self.assertTrue(res["verified"])
        self.assertEqual(len(res["signatures"]), 2)
        rows = dl.db.execute(
            "SELECT COUNT(*) FROM decree_signatures WHERE decree_seq=?",
            (d["seq"],)).fetchone()[0]
        self.assertEqual(rows, 2)
        dl.close()

    def test_verify_all_and_provenance_report(self):
        dl = self._dl()
        dl.issue(text="unsigned observation", category="observation")
        issue_signed(dl, "signed law", key_path=self.priv, category="law")
        results = verify_all(dl, pubkey_path=self.pub)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["verified"])
        report = provenance_report(dl, pubkey_path=self.pub)
        self.assertEqual(report["decrees_total"], 2)
        self.assertEqual(report["decrees_signed"], 1)
        self.assertFalse(report["all_signed"])
        # sign the gap → full provenance
        sign_decree(dl, 1, key_path=self.priv)
        report = provenance_report(dl, pubkey_path=self.pub)
        self.assertTrue(report["all_signed"])
        dl.close()

    def test_missing_decree_honest(self):
        dl = self._dl()
        res = verify_decree_signature(dl, 999)
        self.assertFalse(res["verified"])
        self.assertEqual(res["reason"], "decree_not_found")
        dl.close()

    def test_multisig_threshold_interplay_untouched(self):
        """ADR-0031 must not disturb required_signatures (v3.18.0 N-of-M)."""
        dl = self._dl()
        d = dl.issue(text="pending law", category="law", required_signatures=3)
        self.assertEqual(len(dl.get_active_laws()), 0,
                         "PENDING decree must not be active (pre-existing)")
        sign_decree(dl, d["seq"], key_path=self.priv)
        self.assertEqual(len(dl.get_active_laws()), 0,
                         "Ed25519 signing is provenance, NOT co-signature")
        dl.close()


@unittest.skipUnless(HAS_CRYPTO, "cryptography lib not installed")
class CryptographyInteropTests(unittest.TestCase):
    """Cross-check the pure-python Ed25519 against the reference lib."""

    def test_our_signature_verifies_with_cryptography(self):
        seed = os.urandom(32)
        msg = b"interop decree \xf0\x9f\x8f\xa0"
        sig = ed25519_sign(seed, msg)
        priv = Ed25519PrivateKey.from_private_bytes(seed)
        pub = priv.public_key().public_bytes_raw()
        self.assertTrue(ed25519_verify(pub, msg, sig))
        priv.public_key().verify(sig, msg)  # reference lib agrees

    def test_cryptography_signature_verifies_with_ours(self):
        priv = Ed25519PrivateKey.generate()
        seed = priv.private_bytes_raw()
        msg = b"reverse interop"
        sig = priv.sign(msg)
        self.assertTrue(ed25519_verify(ed25519_public_key(seed), msg, sig))


if __name__ == "__main__":
    unittest.main()
