import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from singulyar_runtime import *  # noqa

KEY = b"test-redaction-key-0123456789abcdef"


def make_runtime(permissions=None, consented=None, **kw):
    remote = SimulatedRemoteAdapter()
    local = MemoryAdapter(adapter_id="local")
    caps = [Capability("remote-v1", "send", "simulated-remote", "medium", False, True, False, 10),
            Capability("local-v1", "send", "local", "high", True, True, True, 20),
            Capability("save-v1", "save", "local", "high", True, True, True, 10)]
    policy = Policy(permissions if permissions is not None else {"send", "save"}, consented or set())
    rt = Runtime(caps, [remote, local], policy, redaction_key=KEY, **kw)
    return rt, remote, local


def intent(iid="a", op="send", value="x", **kw):
    return Intent(iid, "test", op, {"value": value}, {"value": value}, **kw)
