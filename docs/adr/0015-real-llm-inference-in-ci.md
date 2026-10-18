# ADR-0015 — Real LLM Inference in CI (CPU runner)

**Date:** 2026-10-16 (Gate-7 creativity)
**Status:** Accepted (implemented v3.20.0 — `.github/workflows/llm-integration.yml`)
**Deciders:** @USER
**Supersedes:** None

## Context

LIMITATIONS.md item 9 says "ИИ-моделей нет" — v0.3 has no real LLM weights.
Gate-3 added `LLMLocalAdapter` with optional `llama-cpp-python` integration,
but no actual inference runs in CI. The integration test
(`tests/test_llm_local_adapter_integration.py`) SKIPS unless `LLM_MODEL_PATH`
env var is set — which is never set in default CI.

This is a known gap. The integration test exists, but isn't exercised.

## Decision

**v2.0 target**: add a CI job that runs real Qwen2.5-0.5B-Instruct inference
on GitHub Actions CPU runner.

### Implementation plan (v2.0)

1. **New workflow**: `.github/workflows/llm-integration.yml`
2. **Trigger**: weekly schedule (Monday 04:00 UTC — after sovereignty drill)
   + workflow_dispatch (manual)
3. **Runner**: `ubuntu-latest` (CPU only, no GPU needed for 0.5B model)
4. **Setup**:
   - `pip install llama-cpp-python` (no CUDA — CPU build)
   - Download Qwen2.5-0.5B-Instruct GGUF q4_k_m from HuggingFace
     (~470 MB, 6 parts ≤100 MB each — same as singulyar-llm repo)
   - Cache the GGUF file in `~/.cache/polymath-os/` (saves re-download)
5. **Run**: `LLM_MODEL_PATH=/cache/path python3 -m unittest tests.test_llm_local_adapter_integration -v`
6. **Result**: 3 tests should pass (READY state, free-speech response,
   rule-layer short-circuit). If any fail → open issue.

### Honest constraints

- **Cost**: GitHub Actions CPU runner ~$0.008/min. ~5 min for download +
  2 min for inference = ~$0.06 per run. Weekly = ~$3/year. Cheap.
- **Time**: weekly cadence (not per-PR) — too expensive for per-PR
- **Model size**: 470 MB GGUF — fits in runner RAM (7 GB available)
- **No GPU**: 0.5B model is small enough for CPU inference (~5-30 sec per
  prompt depending on length)
- **Failure mode**: if HuggingFace CDN blocks CI IPs, test SKIPs with
  reason — same pattern as `tests/test_http_adapter.py::HTTPAdapterNetworkTests`

## Consequences

- **+**: LIMITATIONS.md item 9 fully closed — real LLM weights exercised
  in CI, not just locally
- **+**: Catches regressions in LLMLocalAdapter + rule-layer integration
- **+**: Weekly cadence is cheap and informative
- **-**: Adds ~5 min to one weekly CI run (acceptable)
- **-**: HuggingFace CDN dependency (Tier 2 per ADR-0002 — replaceable
  by self-hosted model mirror)

## Alternatives considered

1. **Per-PR LLM inference** — rejected: too expensive ($0.06 × N PRs/day)
2. **GPU runner** — rejected: 4× cost, 0.5B model doesn't need GPU
3. **Skip LLM in CI forever** — rejected: leaves LIMITATIONS.md item 9
   perpetually open
4. **Use OpenAI API instead of local model** — rejected: violates
   ADR-0002 Tier 2 (network-dependent, account-required). Local model
   is the sovereignty thesis.

## Verification (implemented v3.20.0)

- `LLM_MODEL_PATH` env var set in `llm-integration.yml` workflow
- 3 tests in `tests/test_llm_local_adapter_integration.py` all pass
- Workflow runs weekly without manual intervention
- Failure opens issue with P0 label (sovereignty regression)

## References

- ADR-0002 (Sovereignty Registry) — local model is Tier 1 (offline, no account)
- ADR-0006 (Falsifiable self-*) — test exercises the "real LLM" claim
- ADR-0012 (SINGULYAR EIR as Layer 5) — LLMLocalAdapter is first real consumer
- AUDIT_SINGULYAR.md S22 (·21 ОБЩЕНИЕ llm.local) — JS source of truth for
  the LLM adapter contract
- LIMITATIONS.md item 9 — closed by this ADR's implementation
