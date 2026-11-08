"""runtime/src/adapters/ — SINGULYAR EIR real-world adapters.

This package contains Python ports of real-world adapters (vs the test
scaffolding adapters MemoryAdapter / SQLiteEffectAdapter which live in
src/singulyar_runtime.py).

Each adapter here is a SINGULYAR EIR consumer — it implements the
Adapter contract (execute + read_state returning Observation tri-state)
and is wired to a real external system.

Gate-3 introduces llm_local_adapter — the Python port of the JS
'llm.local' adapter from singulyar/БИБЛИОТЕКИ/adapter-os/llm.mjs (·21 ОБЩЕНИЕ).
This is the first real consumer of the SINGULYAR kernel beyond tests.
"""
