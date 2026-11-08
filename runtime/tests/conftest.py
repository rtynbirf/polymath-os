"""Pytest configuration: add src/ to sys.path so tests can import singulyar_runtime, sqlite_ledger, schema_validate.

mutmut 3.x copies src + tests into mutants/ subdir and runs pytest from there.
Without this, 'from singulyar_runtime import *' fails with ModuleNotFoundError.
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, '..', 'src'))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# also make tests/ importable for `from _helpers import *`
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
