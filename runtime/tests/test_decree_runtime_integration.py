"""End-to-end: DecreeLog attached to Runtime → prohibition decree blocks Intent."""
import os, sys, tempfile, unittest
from pathlib import Path
_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
if str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
from singulyar_runtime import Runtime, Policy, Capability, Intent, State, MemoryAdapter
from decree_log import DecreeLog

class DecreeRuntimeIntegrationTests(unittest.TestCase):
    def test_prohibition_decree_blocks_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(str(Path(tmp) / "decrees.db"))
            dl.issue("never use Google", category="prohibition")
            dl.issue("never use Cloudflare", category="prohibition")
            caps = [Capability("c1", "send", "mem", "low", True, True)]
            rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), redaction_key=b"k")
            rt.set_decree_log(dl)
            intent = Intent("d1", "send data to Google API", "send", {"v": "x"}, {"v": "x"})
            st = rt.run(intent)
            self.assertNotEqual(st, State.CONFIRMED, "prohibition decree must block Google")

    def test_no_decree_log_allows_all(self):
        caps = [Capability("c1", "send", "mem", "low", True, True)]
        rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), redaction_key=b"k")
        rt.set_decree_log(None)  # explicitly None
        intent = Intent("d2", "test", "send", {"v": "x"}, {"v": "x"})
        st = rt.run(intent)
        self.assertEqual(st, State.CONFIRMED)

    def test_permission_decree_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl = DecreeLog(str(Path(tmp) / "decrees.db"))
            dl.issue("allow local unbound DNS", category="permission")
            caps = [Capability("c1", "send", "mem", "low", True, True)]
            rt = Runtime(caps, [MemoryAdapter()], Policy({"send"}), redaction_key=b"k")
            rt.set_decree_log(dl)
            intent = Intent("d3", "configure local unbound DNS", "send", {"v": "x"}, {"v": "x"})
            st = rt.run(intent)
            self.assertEqual(st, State.CONFIRMED)

if __name__ == "__main__":
    unittest.main()
