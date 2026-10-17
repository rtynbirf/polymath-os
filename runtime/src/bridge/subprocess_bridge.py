"""runtime/src/bridge/subprocess_bridge.py — JSON-over-stdin/stdout protocol
for JS↔Python SINGULYAR EIR kernel communication.

## Protocol

JS (Node.js) spawns Python subprocess:
```js
const { spawn } = require('child_process');
const py = spawn('python3', ['runtime/src/bridge/subprocess_bridge.py']);
py.stdin.write(JSON.stringify({
  "type": "intent",
  "intent_id": "js-call-1",
  "operation": "execute_command",
  "payload": {"phrase": "пинг"},
  "expected": {}
}) + "\n");
py.stdout.on('data', (data) => {
  const result = JSON.parse(data.toString());
  // result = {"state": "CONFIRMED", "evidence": {...}, "via": "rule-layer"}
});
```

Python receives JSON Intent on stdin, routes through SINGULYAR EIR
Runtime, returns JSON Evidence on stdout. One line per exchange
(line-delimited JSON protocol).

## Modes

- **server mode** (default): reads stdin line-by-line, processes each
  Intent through the kernel, writes result as one JSON line to stdout.
  Exits on EOF or "exit" command.

- **one-shot mode** (`--oneshot`): reads one Intent from argv, writes
  one result to stdout, exits. Simpler for single-call scenarios.

## Adapters wired

By default, wires LLMLocalAdapter (offline LLM + rule-layer). Can be
extended with --adapter flag to add HTTPAdapter, WebRTCAdapter, etc.

Per ADR-0002: the bridge itself is Tier 1 (pure Python stdlib —
json, sys, subprocess, no external deps). The adapters it wires are
Tier 1 (LLMLocalAdapter rule-layer) or Tier 2 (HTTPAdapter network,
WebRTCAdapter aiortc).

Per ADR-0006: every state transition is honest — if the kernel can't
process the Intent (no compatible adapter), it returns
{"state": "WAITING_FOR_HUMAN", "reason": "..."} — never lies CONFIRMED.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Bootstrap path
_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_ADAPTERS = _SRC / "adapters"
if str(_ADAPTERS) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS))

from singulyar_runtime import Runtime, Policy, Intent, State
from adapters.llm_local_adapter import LLMLocalAdapter, CAPABILITIES as LLM_CAPS


def create_runtime() -> Runtime:
    """Create a SINGULYAR EIR Runtime wired with all available adapters."""
    adapter = LLMLocalAdapter()
    caps = list(LLM_CAPS)
    permissions = {"execute_command", "answer_question", "generate_response", "check_status"}
    rt = Runtime(
        caps, [adapter],
        Policy(permissions),
        redaction_key=b"bridge-default-key-0123456789abcdef",
    )
    return rt


def process_intent(rt: Runtime, intent_data: dict) -> dict:
    """Process a JSON Intent through the SINGULYAR EIR kernel.

    Returns a JSON-serializable result dict with:
    - state: str (CREATED/PLANNED/EXECUTING/CONFIRMED/UNKNOWN/FAILED/...)
    - intent_id: str
    - evidence: dict (if available) — verdict, observed_status, note
    - adapter_status: dict — current adapter status()
    - error: str (if exception)
    """
    intent_id = intent_data.get("intent_id", f"bridge-{os.getpid()}-{int(__import__('time').time()*1000)}")
    description = intent_data.get("description", intent_data.get("intent_id", "bridge intent"))
    operation = intent_data.get("operation", "execute_command")
    payload = intent_data.get("payload", {})
    expected = intent_data.get("expected", {})

    intent = Intent(
        intent_id=intent_id,
        description=description,
        operation=operation,
        payload=payload,
        expected=expected,
    )

    try:
        state = rt.run(intent)
        result = {
            "state": state.name,
            "intent_id": intent_id,
            "via": "singulyar-eir-bridge",
            "kernel_version": "v0.3",
        }
        # Get adapter status for transparency
        for adapter in rt.adapters:
            if hasattr(adapter, "status"):
                result["adapter_status"] = adapter.status()
                break
        return result
    except Exception as e:
        return {
            "state": "ERROR",
            "intent_id": intent_id,
            "error": str(e),
            "via": "singulyar-eir-bridge",
        }


def server_mode():
    """Read JSON Intents from stdin line-by-line, write results to stdout."""
    rt = create_runtime()
    # Write ready signal
    sys.stdout.write(json.dumps({"type": "ready", "kernel": "singulyar-eir-v0.3", "adapters": ["llm.local"]}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "bye"):
            break
        try:
            intent_data = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stdout.write(json.dumps({"type": "error", "error": f"invalid JSON: {e}"}) + "\n")
            sys.stdout.flush()
            continue

        if intent_data.get("type") == "ping":
            sys.stdout.write(json.dumps({"type": "pong", "kernel": "singulyar-eir-v0.3"}) + "\n")
            sys.stdout.flush()
            continue

        result = process_intent(rt, intent_data)
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    # Cleanup
    sys.stdout.write(json.dumps({"type": "bye", "kernel": "singulyar-eir-v0.3"}) + "\n")
    sys.stdout.flush()


def oneshot_mode(intent_json: str):
    """Process one Intent from argv, write result to stdout, exit."""
    try:
        intent_data = json.loads(intent_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"type": "error", "error": f"invalid JSON: {e}"}))
        sys.exit(1)

    rt = create_runtime()
    result = process_intent(rt, intent_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description="SINGULYAR EIR subprocess bridge — JS↔Python JSON protocol")
    p.add_argument("--oneshot", metavar="JSON", default=None,
                   help="process one Intent from argv, write result, exit")
    p.add_argument("--server", action="store_true", default=False,
                   help="server mode: read JSON Intents from stdin, write results to stdout (default)")
    args = p.parse_args()

    if args.oneshot:
        oneshot_mode(args.oneshot)
    else:
        server_mode()


if __name__ == "__main__":
    main()
