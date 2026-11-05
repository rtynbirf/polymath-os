#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOLOS agent v2.0 — selftest wrapper for `make verify` (check 27).

Contract (machine-checked by scripts/check.py):
  * `python3 selftest.py` in this directory must exit 0
  * stdout must contain "60/60 PASS"

The wrapper is a thin relay: the core `holo_agent_v2.py --selftest`
runs its own adversarial polygon (60 checks, stdlib-only) and prints
the canonical summary line "ИТОГ SELFTEST: 60/60 PASS, 0 FAIL".
"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    core = Path(__file__).resolve().parent / "holo_agent_v2.py"
    if not core.exists():
        print("holo_agent_v2.py missing next to selftest.py", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, str(core), "--selftest"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
