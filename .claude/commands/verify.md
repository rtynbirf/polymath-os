---
description: Run `make verify` and report results. The open-source contract: 12 verifiable claims.
allowed-tools: Bash
---

# /verify — Polymath OS verification

Run the open-source contract check.

## What this does

`make verify` runs `python3 scripts/check.py` — 12 independent checks:

1. SINGULYAR EIR — all 40 tests pass (in `runtime/`)
2. JSON Schemas (Intent / Capability / Evidence) valid
3. ADRs 0001-0012 present
4. ADRs follow template (Date/Status/Context/Decision/Consequences)
5. `AUDIT_RESPONSE.md` cross-references all ADRs
6. Sovereignty Registry covers all `package.json` dependencies
7. RUNBOOK hardened (ПРЕДУСЛОВИЯ + ПРОВЕРКА + ⛔ irreversible markers)
8. LICENSE = MIT
9. `ARCHITECTURE.md` documents 5 layers + Sovereignty + falsifiable self-*
10. `runtime/src/*.py` compiles (Python syntax)
11. No `__pycache__` or `*.pyc` tracked in git
12. CI workflow runs `pnpm install` + `turbo run` + `gitleaks`

## Execution

```bash
make verify
```

## Reporting

After running:
- If exit 0 → report "All 12 claims verified. Repo is reproducible."
- If non-zero → list which checks failed and what each failure means.
- Map each failed check to its corresponding ADR (see `docs/adr/` and
  `docs/AUDIT_RESPONSE.md` for cross-references).

**Do not commit code that breaks `make verify`.** This is the open-source
contract: clone → `make verify` → same result. If a check is broken by
intention (e.g., adding a new dep), update the corresponding ADR
(especially ADR-0002 Sovereignty Registry) AND `scripts/check.py` in the
same commit.
