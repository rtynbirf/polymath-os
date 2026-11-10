#!/usr/bin/env python3
"""Validate the agent documentation package only; never execute target repository code.

Works in two placements:
- canonical pack directory (ROOT = pack root);
- installed overlay inside a host repository (same layout at ROOT).
The link check is scoped to pack-owned paths, so pre-existing host documentation
is out of scope (host files are governed by host policy, not by this validator).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md", "README_RU.md", "docs/README.md",
    "docs/agent-execution/01_OPERATING_CONTRACT.md",
    "docs/agent-execution/02_TASK_CONTRACT.md",
    "docs/agent-execution/03_SYSTEM_ARCHITECTURE.md",
    "docs/agent-execution/04_AGENT_ROLES.md",
    "docs/agent-execution/05_EXECUTION_WORKFLOW.md",
    "docs/agent-execution/06_EVIDENCE_MODEL.md",
    "docs/agent-execution/07_SECURITY_AND_PERMISSIONS.md",
    "docs/agent-execution/08_TESTING_AND_EVALUATION.md",
    "docs/agent-execution/09_CROSS_REPO_RULES.md",
    "docs/agent-execution/10_ROADMAP.md",
    "docs/agent-execution/11_AGENT_RUNBOOK.md",
    "docs/agent-execution/12_SOURCES.md",
    ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/agent-task.yml",
    "docs/agent-execution/00_EXECUTION_SPEC.md", "docs/agent-execution/13_TASK_GRAPH.md",
    "tasks/A1_REPO_SNAPSHOT.task.json", "tasks/A2_BUILD_BASELINE.task.json",
    "tasks/A3_ARCHITECTURE_MAP.task.json", "tasks/A4_SECURITY_POSTURE.task.json",
    "examples/agent-manifest.json", "examples/claim.json",
]
# In installed mode the host may keep its own PR template (upper-case variant);
# the pack never overwrites differing host files.
PR_TEMPLATE_ALTS = [".github/PULL_REQUEST_TEMPLATE.md"]
PACK_MD_SCOPE = [
    "README_RU.md", "docs/README.md", "docs/agent-execution",
    "templates", "tasks", "examples",
]

def main() -> int:
    errors=[]
    for rel in REQUIRED:
        if (ROOT/rel).is_file(): continue
        if rel == ".github/pull_request_template.md" and any((ROOT/a).is_file() for a in PR_TEMPLATE_ALTS):
            continue  # installed mode: host PR template already present, pack copy intentionally skipped
        errors.append(f"missing required file: {rel}")
    schema_dir=ROOT/"schemas/agent-execution"
    for p in sorted(schema_dir.glob("*.json")):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            if obj.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"wrong/missing JSON Schema draft: {p.relative_to(ROOT)}")
        except Exception as e: errors.append(f"invalid JSON in {p.relative_to(ROOT)}: {e}")
    for rel in ["templates/task.json","templates/evidence-record.json","templates/run-record.json","examples/EXAMPLE_TASK.json"]:
        try: json.loads((ROOT/rel).read_text(encoding="utf-8"))
        except Exception as e: errors.append(f"invalid JSON in {rel}: {e}")
    # Validate task/evidence/run examples against JSON Schema when jsonschema is installed.
    try:
        from jsonschema import Draft202012Validator
        schema_map={
            "tasks/A1_REPO_SNAPSHOT.task.json":"task.schema.json",
            "tasks/A2_BUILD_BASELINE.task.json":"task.schema.json",
            "tasks/A3_ARCHITECTURE_MAP.task.json":"task.schema.json",
            "tasks/A4_SECURITY_POSTURE.task.json":"task.schema.json",
            "templates/task.json":"task.schema.json",
            "examples/agent-manifest.json":"agent.schema.json",
            "examples/claim.json":"claim.schema.json",
            "templates/evidence-record.json":"evidence.schema.json",
            "templates/run-record.json":"run.schema.json",
        }
        for rel,schema_name in schema_map.items():
            data=json.loads((ROOT/rel).read_text(encoding="utf-8"))
            schema=json.loads((schema_dir/schema_name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            errors_list=list(Draft202012Validator(schema).iter_errors(data))
            if errors_list:
                errors.append(f"schema validation failed for {rel}: " + "; ".join(e.message for e in errors_list))
    except ImportError:
        print("WARN — jsonschema is not installed; JSON syntax checked, schema/example conformance skipped.")
    # Local links only, scoped to pack-owned paths; external URLs are not fetched.
    import re
    md_files: list[Path] = []
    for rel in PACK_MD_SCOPE:
        p = ROOT/rel
        if p.is_file(): md_files.append(p)
        elif p.is_dir(): md_files.extend(sorted(p.rglob("*.md")))
    for p in md_files:
        text=p.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("https://","http://","mailto:","#")): continue
            target_path=(p.parent/target.split("#",1)[0]).resolve()
            if target.split("#",1)[0] and not target_path.exists(): errors.append(f"broken local link {p.relative_to(ROOT)} -> {target}")
    if errors:
        print("FAIL — agent pack validation")
        for e in errors: print(f"- {e}")
        return 1
    print(f"PASS — {len(REQUIRED)} required files; {len(list(schema_dir.glob('*.json')))} schemas; JSON files parsed; pack-scoped Markdown links checked; schema examples validated when jsonschema is installed.")
    print("NOTE — this validates the package, not polymath-os or its runtime.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
