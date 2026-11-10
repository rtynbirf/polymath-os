# 15 — Governance crosswalk: world practice of 2026 mapped to this pack

Research snapshot date: 2026-11-10. This document maps the pack's mechanisms to independent 2026 frameworks for agent governance and supply-chain security. It is a positioning aid, not proof of compliance: every mapping below is **PROPOSED** until verified against the actual repository and executed runs (see `docs/README.md` maturity labels).

## Why a crosswalk

In 2026 the governance question shifted from "what did the model say" to "what did the system do, why was it allowed, and who is accountable". Orchestration frameworks matured in parallel. This pack deliberately does not compete with orchestration runtimes: it supplies the missing governance substrate — task contracts, agent identity, evidence, run records, and human gates — that any of those runtimes can emit into.

## Crosswalk table

| # | World practice (2026) | What it demands | Where it lives in this pack | Honest boundary |
|---|---|---|---|---|
| 1 | CSA Agentic Trust Framework (Feb 2026): Zero Trust applied to autonomous agents | Continuous verification of agent identity and actions; no implicit trust between agents | `schemas/agent-execution/agent.schema.json` (agent manifest, FR-003); `07_SECURITY_AND_PERMISSIONS.md` (typed, scoped, time-bound tool authorization, FR-005); human gates (FR-006) | Pack records identity and permissions; runtime enforcement of "continuous" checks is not implemented yet |
| 2 | Microsoft Cloud Adoption Framework: govern and secure AI agents (Jun 2026) | Identity and ownership; data and access rules; behavioral guardrails; audit evidence | Agent manifest (FR-003); isolation and bounded scopes (FR-004); frozen acceptance criteria (FR-009); run records and append-only auditability (FR-008, FR-019) | Guardrails are contractual here; technical sandboxing backend is an open ADR (`00_EXECUTION_SPEC.md` §7) |
| 3 | Brookings (Oct 2026): accountability for agent systems | Answer "what the system did, why allowed, who is accountable" from records, not from memory | `06_EVIDENCE_MODEL.md` (claim → evidence lineage); run records with commands, exit codes, commit IDs (FR-008); honest status values incl. `UNKNOWN` (FR-020) | Records exist only if agents actually write them; adoption is measurable only after first pilot runs |
| 4 | GitHub Artifact Attestations + SLSA (Jan 2026: code-to-cloud traceability, SLSA build L3) | Cryptographically verifiable build provenance for published artifacts | Complementary layer: pack's evidence lineage covers *code changes and decisions*; attestation covers *built artifacts*. Target host already tracks cosign/SLSA L2 and an OSPS baseline matrix | Attestations require release workflows emitting binaries; generation is not wired into this pack yet |
| 5 | GitHub Actions security hardening (2026 checklists): actions pinned by full SHA, least-privilege `GITHUB_TOKEN`, no `pull_request_target` on public repos, interpolation via env indirection | Supply-chain-safe CI | `07_SECURITY_AND_PERMISSIONS.md` + `12_SOURCES.md`; the target host's CI already pins actions by SHA (observed 2026-11-10) | CI hardening belongs to the host repository; the pack only references the practice |
| 6 | AgentLens / lucky-pass problem (Microsoft Research) | Evaluate the agent's *process trajectory*, not only the binary test result | FR-017: outcome and process are both evaluated; claim register separates PASS from evidence | Trajectory capture tooling is not part of this pack; evaluation protocol is documented, not automated |
| 7 | Multi-agent orchestration field of 2026 (LangGraph, Microsoft Agent Framework, CrewAI, Google ADK, OpenAI Agents SDK) | Runtime composition, state, observability | Explicitly out of pack scope by design (FR-015 portability): the pack's schemas are runtime-agnostic; the orchestrator is an ADR decision (`00_EXECUTION_SPEC.md` §7) | No vendor lock-in, but also no orchestration convenience until an ADR selects and integrates a runtime |
| 8 | OWASP MCP Security Cheat Sheet | Per-server least privilege, tool schema inspection, input/output validation, human approval for sensitive actions | `07_SECURITY_AND_PERMISSIONS.md` (tool authorization model) and `12_SOURCES.md` | Pack defines the policy layer; MCP server configuration itself lives in the host repository |

## What makes the combination distinctive

1. **Schemas first.** Task, agent, run, claim and evidence are JSON Schema (draft 2020-12) validated artifacts, not prose promises — machine-checkable by CI or any reviewer.
2. **Honesty as a type.** `UNKNOWN`/`DECLARED`/`OBSERVED`/`EXECUTED`/`INDEPENDENTLY_VERIFIED` are first-class statuses; a claim without evidence cannot be PASS by construction.
3. **Non-destructive install.** The pack merges with host instructions (`AGENTS.md`) instead of replacing them; conflicts stop the process instead of overwriting.
4. **Governance without lock-in.** The same evidence format outlives any single orchestration framework or model provider — the 2026 frameworks above are consumers of the records, not prerequisites.

## Sources

- Cloud Security Alliance — Agentic Trust Framework (Feb 2026): https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-agent-governance-framework-gap-20260403
- Microsoft Learn — Govern and secure AI agents across the organization (Jun 2026): https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ai-agents/governance-security-across-organization
- Brookings — Shaping global governance of AI agents (Oct 2026): https://www.brookings.edu/articles/shaping-global-governance-of-ai-agents/
- GitHub Changelog — Code-to-cloud traceability and SLSA build level 3 (Jan 2026): https://github.blog/changelog/2026-01-20-strengthen-your-supply-chain-with-code-to-cloud-traceability-and-slsa-build-level-3-security/
- GitHub Docs — Artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations
- Microsoft Research — AgentLens (lucky-pass problem): https://www.microsoft.com/en-us/research/publication/agentlens-revealing-the-lucky-pass-problem-in-swe-agent-evaluation/
- LangChain — The best AI agent frameworks in 2026 (Jun 2026): https://www.langchain.com/resources/ai-agent-frameworks
- OWASP — MCP Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html

Freshness caveat: external frameworks evolve quickly. Re-open the current version of any source before claiming conformance, and record the version/date consulted (see `12_SOURCES.md`).
