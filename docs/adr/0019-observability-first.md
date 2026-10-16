# ADR-0019 — Observability-First (structured traces, no external deps)

**Date:** 2026-10-16 (v2.7.0)
**Status:** Accepted
**Deciders:** @USER

## Context

Per research_devex_ci_report.md (Gate-0 research): "Observability-first —
OTel SDK before business code, logs/metrics/traces to one sink." Per
ADR-0008: "OTel GenAI semconv not stable — use own attribute set."

The SINGULYAR EIR kernel currently has no structured trace output. Events
are written to the SQLite ledger (which is durable and hash-chained), but
there's no real-time observability — no way to see "what's the kernel
doing right now?" without querying the ledger.

World trend 2026: observability-first is standard practice. But OTel SDK
adds external dependencies (Tier 2 per ADR-0002). The sovereign path is:
structured traces via stdlib only, with OTel-compatible attribute names
so they CAN be forwarded to OTel collector when available.

## Decision

### 1. Structured trace events in the kernel

Add trace emission points in singulyar_runtime.py at key state transitions:
- INTENT_ACCEPTED → trace: {intent_id, operation, risk, constraints}
- CAPABILITY_SELECTED → trace: {intent_id, capability_id, adapter_id, priority}
- EXECUTION_STARTED → trace: {intent_id, capability_id, idempotency_key}
- ADAPTER_RETURN → trace: {intent_id, capability_id, result_type}
- EVIDENCE_VERIFIED → trace: {intent_id, verdict, observed_status}
- STATE_TRANSITION → trace: {intent_id, from_state, to_state, reason}

### 2. Trace format (JSON, one line per event, OTel-compatible)

```json
{"ts":"2026-10-16T17:00:00Z","trace_id":"<uuid>","span_id":"<uuid>",
 "intent_id":"test-1","capability_id":"llm.command","adapter_id":"llm.local",
 "event":"STATE_TRANSITION","from_state":"EXECUTING","to_state":"CONFIRMED",
 "verdict":"PASS","observed_status":"PRESENT","via":"rule-layer",
 "kernel_version":"v0.3"}
```

Attribute names follow OTel semantic conventions where stable:
- `intent_id` (custom, not OTel GenAI semconv — per ADR-0008)
- `capability_id` (custom)
- `verdict` (custom: PASS/FAIL/INCONCLUSIVE)
- `observed_status` (custom: PRESENT/ABSENT/UNAVAILABLE)

### 3. Trace sink: stderr by default, OTel collector when available

```python
import sys, json, time, uuid

def emit_trace(event, **attrs):
    """Emit a structured trace event to stderr.
    
    One JSON line per event. Compatible with OTel collector forwarding:
    if OTEL_EXPORTER_OTLP_ENDPOINT is set, a future v0.5 will forward
    to the collector. For now, stderr is the sink (grep-able, pipe-able).
    """
    trace = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trace_id": str(uuid.uuid4()),
        "event": event,
        "kernel_version": "v0.3",
        **attrs,
    }
    sys.stderr.write(json.dumps(trace, ensure_ascii=False) + "\n")
    sys.stderr.flush()
```

### 4. No external dependencies

The trace emission uses only Python stdlib (json, sys, time, uuid).
Per ADR-0002 Tier 1: no external SDK required. The traces are emitted
to stderr as JSON lines — grep-able, pipe-able, forward-able to OTel
collector, Loki, or any log sink.

## Consequences

- **+**: Real-time observability of kernel state transitions
- **+**: OTel-compatible attribute names (forward-ready)
- **+**: Zero external dependencies (Tier 1)
- **+**: Grep-able (`python3 demo.py 2>&1 | grep STATE_TRANSITION`)
- **-**: No distributed tracing (single-process only — multi-process
  would need OTel collector + trace propagation)
- **-**: No metrics aggregation (traces are events, not counters)

## Verification

- `python3 src/demo.py 2>&1 | grep -c '"event"'` → should show trace count
- Trace format is valid JSON (one line per event)
- No external deps (only stdlib)

## References

- ADR-0002 (Sovereignty Registry) — Tier 1 (stdlib only)
- ADR-0008 (MCP version pin) — own attribute set, not OTel GenAI semconv
- research_devex_ci_report.md — "Observability-first" principle
- AUDIT_SINGULYAR.md S22 (·21 ОБЩЕНИЕ wllama state staleness) — traces
  would catch state staleness (READY after death)
