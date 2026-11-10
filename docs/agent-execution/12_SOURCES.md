# 12 — Sources and external practices

Research snapshot date: 2026-11-10. Sources below are references for engineering practices; they are not universal authorities and do not prove this repository implements them.

| Source | What is taken from it | Boundary |
|---|---|---|
| OpenAI, Harness engineering | Keep repository knowledge in structured docs; use short AGENTS.md as map; make plans and architecture/quality docs machine-checkable | A published experience report, not a mandatory standard |
| Microsoft Agent Framework, Harness | Harness composes model client, state, context providers, tools, approval, observability and bounded execution | Framework-specific architecture; use concepts, not dependency mandate |
| GitHub Actions security | Least privilege, immutable action references/lockfiles, OIDC, secure deployment | Apply based on actual workflows and GitHub features available |
| GitHub Artifact Attestations | Cryptographically verifiable claims about build provenance/integrity | Provenance does not prove software correctness |
| OWASP MCP Security Cheat Sheet | Per-server least privilege, inspect tool schemas, sandbox, validate inputs/outputs, human approval for sensitive actions | Security guidance; threat model must fit actual tool architecture |
| Microsoft MCP security best practices | MCP-specific token audience/authorization and prompt/tool poisoning concerns | Version-specific; check current MCP spec before implementation |
| AgentLens / AgentLens-Bench | Evaluate agent process trajectories, not only binary test pass; identify lucky-pass patterns | Research dataset/paper; benchmark results are not a guarantee about this project |

## Direct links

- OpenAI — https://openai.com/index/harness-engineering/
- Microsoft Agent Framework Harness — https://learn.microsoft.com/agent-framework/concepts/harness
- GitHub Actions security — https://docs.github.com/en/actions/how-tos/secure-your-work
- GitHub Artifact Attestations — https://docs.github.com/en/actions/concepts/security/artifact-attestations
- OWASP MCP Security Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html
- Microsoft MCP security guidance — https://github.com/microsoft/mcp-for-beginners/blob/main/02-Security/mcp-security-best-practices.md
- AgentLens — https://www.microsoft.com/en-us/research/publication/agentlens-revealing-the-lucky-pass-problem-in-swe-agent-evaluation/

Access and freshness caveat: external pages may change. Before implementing provider-specific APIs, authentication, MCP protocol requirements, or GitHub Actions policy, re-open the official current specification and record the version/date used.
