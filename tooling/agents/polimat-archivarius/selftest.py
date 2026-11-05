#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POLIMAT-ARCHIVARIUS — selftest wrapper for `make verify` (check 31).

Contract (machine-checked by scripts/check.py):
  * `python3 selftest.py` in this directory must exit 0
  * stdout must contain "30/30 PASS"

The wrapper is a thin relay: the core `polimat.py selftest` runs its own
30 deterministic checks of the five organs (GENOME / Merkle / Reed-Solomon
k-of-n / GOSSIP-CRDT / JUDGE echo-detector) — offline, stdlib-only, state
in a temp dir — and prints the canonical summary line
"ИТОГ SELFTEST: 30/30 PASS, 0 FAIL".
"""
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    core = Path(__file__).resolve().parent / "polimat.py"
    if not core.exists():
        print("polimat.py missing next to selftest.py", file=sys.stderr)
        return 1
    env = dict(os.environ)
    # no __pycache__ in the repo tree (claim 11: no *.pyc)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run(
        [sys.executable, str(core), "selftest"],
        capture_output=True, text=True, timeout=110,
        env=env, cwd=str(core.parent),
    )
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
