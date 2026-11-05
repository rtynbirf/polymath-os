#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for make verify claim 28.

Runs the polymath-agent v3.8.0 selftest (130 checks, zero dependencies).
Exits 0 iff all 130 checks pass.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "polymath_agent_v3.8.0.py"

def main() -> int:
    r = subprocess.run(
        [sys.executable, str(TARGET), "--selftest"],
        cwd=str(HERE), capture_output=True, text=True, timeout=120,
    )
    tail = (r.stdout or "").strip().splitlines()[-3:]
    print("\n".join(tail))
    ok = r.returncode == 0 and "130/130" in (r.stdout or "")
    print("POLYMATH-AGENT SELFTEST: PASS 130/130" if ok else "POLYMATH-AGENT SELFTEST: FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
