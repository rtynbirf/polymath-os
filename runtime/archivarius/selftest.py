#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for make verify claim 27.

Runs the АРХИВАРИУС v1.3.1 selftest (84 checks: chain, neighbour audit,
birth signatures, Reed-Solomon, judge verdicts). Exits 0 iff 84/84 PASS.

Line provenance: bit-for-bit copies, see SHA256SUMS.txt and README.md.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "АРХИВАРИУС_v1.3_СОГЛАСОВАННОСТЬ.py"

def main() -> int:
    r = subprocess.run(
        [sys.executable, str(TARGET), "--selftest"],
        cwd=str(HERE), capture_output=True, text=True, timeout=120,
    )
    tail = (r.stdout or "").strip().splitlines()[-3:]
    print("\n".join(tail))
    ok = r.returncode == 0 and "84/84 PASS" in (r.stdout or "")
    print("ARCHIVARIUS SELFTEST: PASS 84/84" if ok else "ARCHIVARIUS SELFTEST: FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
