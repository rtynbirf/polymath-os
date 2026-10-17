# ADR-0013 — SLSA Build L3 Target (hermetic builder isolation)

**Date:** 2026-10-16 (Gate-6 candidate ADR)
**Status:** Proposed (awaiting implementation in v0.5/v2.0)
**Deciders:** @USER
**Supersedes**: None (extends ADR-0004 — SLSA Build L2 Target)

## Context

ADR-0004 set v1.0 target = SLSA Build L2 (signed provenance from hosted build
platform via GitHub Actions OIDC). This was achieved in v1.4.0 (Gate-4) —
the `release.yml` workflow generates:
- `sbom.cyclonedx.json` (npm deps)
- `sbom.python.cyclonedx.json` (Python deps)
- `sbom.pem` (cosign keyless cert)
- `sbom.sig` (cosign keyless signature)
- `sbom.attestation.json` (cosign attest-blob output — in-toto statement)
- `sbom.slsa-provenance.json` (SLSA L2 provenance predicate)

But SLSA L2 has a known limitation: the build platform itself (GitHub Actions)
can forge provenance — there is no hermetic isolation. An attacker who
compromises the GitHub Actions runner can modify the build to produce a
malicious artifact while still emitting a valid-looking provenance.

SLSA L3 closes this by requiring the build platform to **prevent** the build
from forging provenance — typically via:
1. Hermetic build environment (no network access during build)
2. Reproducible build (deterministic output from same inputs)
3. Trusted builder (separate process that records provenance, isolated from
   the build itself)

## Decision

v2.0 (target: post-Gate-6) target = **SLSA Build L3** with hermetic builder
isolation. Implementation via:

1. **Use `slsa-framework/slsa-github-generator` reusable workflow** for
   artifact attestation (instead of self-generated provenance in `release.yml`).
   This workflow is hardened by the SLSA framework team and audited.

2. **Add hermetic build step**: build artifacts inside a sandboxed container
   with no network access (`--network=none` in Docker, or `firejail
   --net=none` on bare metal). Verify that the only network I/O during build
   is the initial `git clone` + `pnpm install --frozen-lockfile` (cached).

3. **Reproducible build verification**: after hermetic build, re-build the
   same commit and verify byte-identical output. If non-reproducible (e.g.,
   due to timestamps in SBOM), document and pin inputs.

4. **Trusted builder separation**: the provenance-recording step is a
   separate GitHub Actions job that depends only on `make verify` output +
   the artifact SHA — not on the build job's environment.

## Consequences

- **+**: SLSA L3 attestation — supply-chain integrity against runner compromise
- **+**: Hermetic build catches hidden network dependencies (e.g., a test
  that secretly hits `httpbin.org`)
- **-**: Slower CI (hermetic container startup ~30s overhead)
- **-**: Reproducible build may require pinning more inputs (e.g., pnpm-lock
  hash, Python venv hash)
- **-**: `slsa-framework/slsa-github-generator` is GitHub-specific — couples
  to GitHub (violates ADR-0002 Tier 2 sovereignty). Migration to GitLab/Forgejo
  would require a different SLSA L3 framework.

## Alternatives considered

1. **Stay at L2 forever** — rejected: ADR-0004 set L3 as deferred target,
   not abandoned. L2 provenance is "signed" but not "isolated".

2. **Self-implement L3 in release.yml** — rejected: implementing hermetic
   builder isolation from scratch is error-prone. The slsa-framework team
   has audited their workflow.

3. **Use `wolfi`/`apko` reproducible base images** — partial: gives
   reproducible container base, but not full SLSA L3 (still needs trusted
   builder separation).

4. **Run build in `bubblewrap`/`firejail --net=none`** — partial: gives
   hermetic build, but doesn't provide trusted-builder separation.

## Verification (deferred to v2.0 implementation)

- `slsa-framework/slsa-github-generator` reusable workflow in `release.yml`
- `act -W --container-architecture linux/amd64 --network none` for local
  hermetic CI parity
- `cosign verify-attestation` against the published artifact with SLSA
  provenance predicate type `https://slsa.dev/provenance/v0.2`
- Byte-identical rebuild: `git clone` → `make build` twice, diff the output

## References

- ADR-0004 (SLSA Build L2 Target) — the v1.0 target this extends
- https://slsa.dev/spec/v1.0/levels#build-l3
- https://github.com/slsa-framework/slsa-github-generator
- https://reproducible-builds.org/
- ADR-0002 Tier 2 — `slsa-framework/slsa-github-generator` is a Tier 2
  dependency (replaceable by in-toto + cosign attestation on a self-hosted
  runner with firejail)
