"""runtime/tests/test_subprocess_bridge.py — Tests for Python↔JS bridge (Gate-ecosystem Step 3).

Verifies:
- One-shot mode: JSON Intent → JSON result
- Server mode: ready signal, multiple Intents, bye signal
- Honest failure: free speech without LLM → FAILED (not CONFIRMED)
- Rule-layer match: "пинг" → CONFIRMED with correct response
- JSON protocol: line-delimited, valid JSON on both sides

This proves the SINGULYAR EIR kernel works across language boundaries —
JS can call Python kernel via subprocess, Intent is language-agnostic.
"""

import json, os, subprocess, sys, unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRIDGE = REPO_ROOT / "runtime" / "src" / "bridge" / "subprocess_bridge.py"
RUNTIME_SRC = REPO_ROOT / "runtime" / "src"
ADAPTERS_SRC = RUNTIME_SRC / "adapters"

PYTHONPATH = f"{RUNTIME_SRC}:{ADAPTERS_SRC}"
ENV = {**os.environ, "PYTHONPATH": PYTHONPATH}


class SubprocessBridgeOneshotTests(unittest.TestCase):

    def test_oneshot_ping_returns_confirmed(self):
        """Rule-layer 'пинг' → CONFIRMED."""
        intent = json.dumps({
            "intent_id": "oneshot-1",
            "operation": "execute_command",
            "payload": {"phrase": "пинг"},
            "expected": {}
        })
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--oneshot", intent],
            capture_output=True, text=True, env=ENV, timeout=30
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["state"], "CONFIRMED")
        self.assertEqual(result["intent_id"], "oneshot-1")
        self.assertEqual(result["via"], "singulyar-eir-bridge")

    def test_oneshot_free_speech_returns_failed_or_waiting(self):
        """Free speech without LLM → FAILED or WAITING_FOR_HUMAN (never CONFIRMED)."""
        intent = json.dumps({
            "intent_id": "oneshot-free-1",
            "operation": "answer_question",
            "payload": {"phrase": "расскажи про эмерджентность"},
            "expected": {}
        })
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--oneshot", intent],
            capture_output=True, text=True, env=ENV, timeout=30
        )
        self.assertEqual(r.returncode, 0)
        result = json.loads(r.stdout)
        self.assertNotEqual(result["state"], "CONFIRMED",
                            "free speech without LLM must NOT be CONFIRMED — ADR-0006 falsifiability")

    def test_oneshot_invalid_json_returns_error(self):
        """Invalid JSON input → error, not crash."""
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--oneshot", "not-json"],
            capture_output=True, text=True, env=ENV, timeout=10
        )
        self.assertEqual(r.returncode, 1)
        result = json.loads(r.stdout)
        self.assertIn("error", result)


class SubprocessBridgeServerTests(unittest.TestCase):
    """Server mode: pipe stdin/stdout, multiple Intents."""

    def test_server_ready_signal(self):
        """Server sends 'ready' signal on stdout before processing."""
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--server"],
            input="exit\n",
            capture_output=True, text=True, env=ENV, timeout=10
        )
        self.assertEqual(r.returncode, 0)
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        first = json.loads(lines[0])
        self.assertEqual(first["type"], "ready")
        self.assertIn("singulyar-eir", first["kernel"])

    def test_server_multiple_intents(self):
        """Server processes multiple Intents, one per line."""
        stdin = json.dumps({"intent_id": "srv-1", "operation": "execute_command", "payload": {"phrase": "пинг"}, "expected": {}}) + "\n"
        stdin += json.dumps({"intent_id": "srv-2", "operation": "execute_command", "payload": {"phrase": "статус"}, "expected": {}}) + "\n"
        stdin += "exit\n"
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--server"],
            input=stdin, capture_output=True, text=True, env=ENV, timeout=15
        )
        self.assertEqual(r.returncode, 0)
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        # ready, srv-1 result, srv-2 result, bye
        self.assertGreaterEqual(len(lines), 4)
        msgs = [json.loads(l) for l in lines]
        self.assertEqual(msgs[0]["type"], "ready")
        self.assertEqual(msgs[1]["state"], "CONFIRMED")
        self.assertEqual(msgs[1]["intent_id"], "srv-1")
        self.assertEqual(msgs[2]["state"], "CONFIRMED")
        self.assertEqual(msgs[2]["intent_id"], "srv-2")
        self.assertEqual(msgs[-1]["type"], "bye")

    def test_server_ping_pong(self):
        """Server responds to ping with pong."""
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--server"],
            input='{"type":"ping"}\nexit\n',
            capture_output=True, text=True, env=ENV, timeout=10
        )
        self.assertEqual(r.returncode, 0)
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        msgs = [json.loads(l) for l in lines]
        self.assertEqual(msgs[0]["type"], "ready")
        self.assertEqual(msgs[1]["type"], "pong")

    def test_server_invalid_json_doesnt_crash(self):
        """Invalid JSON line → error message, server continues."""
        stdin = 'not-json\n' + json.dumps({"intent_id": "after-error", "operation": "execute_command", "payload": {"phrase": "пинг"}, "expected": {}}) + '\nexit\n'
        r = subprocess.run(
            [sys.executable, str(BRIDGE), "--server"],
            input=stdin, capture_output=True, text=True, env=ENV, timeout=15
        )
        self.assertEqual(r.returncode, 0)
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        msgs = [json.loads(l) for l in lines]
        # ready, error, after-error CONFIRMED, bye
        self.assertEqual(msgs[0]["type"], "ready")
        self.assertEqual(msgs[1]["type"], "error")
        self.assertEqual(msgs[2]["state"], "CONFIRMED")
        self.assertEqual(msgs[2]["intent_id"], "after-error")


if __name__ == "__main__":
    unittest.main()
