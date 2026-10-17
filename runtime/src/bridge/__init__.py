"""runtime/src/bridge/ — Python↔JS bridge for ecosystem integration.

This package provides the bridge that lets singulyar's JavaScript modules
call polymath-os's Python SINGULYAR EIR kernel. Two transport modes:

1. **Subprocess mode** (server-side): JS calls a Python subprocess via
   stdin/stdout JSON protocol. Works in Node.js server, Codespaces, or
   any environment with Python available.

2. **Pyodide/WASM mode** (browser-side, future): JS calls Python kernel
   compiled to WASM via Pyodide. Works in browser without server.
   Requires Pyodide + WASM-compiled singulyar_runtime.py.

Per ADR-0012 (SINGULYAR EIR as Layer 5): this bridge proves the kernel
works across language boundaries — Intent is language-agnostic, the
kernel preserves it across JS↔Python transitions.

Per ADR-0007: the bridge is a single executor + deterministic verifier.
JS sends Intent as JSON, Python kernel processes it, returns Evidence
as JSON. No second LLM in the loop.
"""
