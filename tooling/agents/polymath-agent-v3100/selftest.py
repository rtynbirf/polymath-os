#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for make verify claim 32.

Runs the polymath-agent v3.10.0 selftest (135 checks, zero dependencies).
Exits 0 iff all 135 checks pass.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "polymath_agent_v3.10.0.py"

def main() -> int:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # claim 11: no *.pyc in tree
    r = subprocess.run(
        [sys.executable, str(TARGET), "--selftest"],
        cwd=str(HERE), capture_output=True, text=True, timeout=120, env=env,
    )
    tail = (r.stdout or "").strip().splitlines()[-3:]
    print("\n".join(tail))
    ok = r.returncode == 0 and "135/135" in (r.stdout or "")
    print("POLYMATH-AGENT v3.10.0 SELFTEST: PASS 135/135" if ok else "POLYMATH-AGENT v3.10.0 SELFTEST: FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
