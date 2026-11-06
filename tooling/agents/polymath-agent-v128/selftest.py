#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for the polymath-agent v1.2.8 selftest (19 checks, zero dependencies).

Runs the kernel's built-in offline probe suite T01–T19.
Exits 0 iff all 19 checks pass.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "polymath_agent_v1.2.8.py"


def main() -> int:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # гигиена: без *.pyc в дереве
    r = subprocess.run(
        [sys.executable, str(TARGET), "--selftest"],
        cwd=str(HERE), capture_output=True, text=True, timeout=120, env=env,
    )
    tail = (r.stdout or "").strip().splitlines()[-3:]
    print("\n".join(tail))
    ok = r.returncode == 0 and "19/19" in (r.stdout or "")
    print("POLYMATH-AGENT v1.2.8 SELFTEST: PASS 19/19" if ok else "POLYMATH-AGENT v1.2.8 SELFTEST: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
