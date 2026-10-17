# MCP Adapters for SINGULYAR EIR (Layer 5)

This package is a **thin internal adapter layer** bridging
[Model Context Protocol][mcp] (MCP) server tools to the
SINGULYAR EIR `Adapter` interface (Layer 5, per ADR-0012).

If the MCP specification changes, **only this adapter layer is touched** —
never business logic. The MCP version is pinned (ADR-0008 §2); bumps require
a migration ADR (ADR-0008 §3).

## Layering

```
┌──────────────────────────────────────────────────────────────┐
│  SINGULYAR EIR (Layer 5) — Runtime / planner / verifier      │
│      Adapter.execute(intent, key)                             │
│      Adapter.read_state(intent, key) → Observation            │
│      consults MCPCapabilityRegistry to pick Capability        │
└──────────────────────────────────────────────────────────────┘
                       ↓ uses
┌──────────────────────────────────────────────────────────────┐
│  MCPAdapter (this package) — thin internal adapter           │
│      maps SINGULYAR operation → MCP tool name                │
│      dispatches JSON-RPC call to MCP server                   │
│      translates MCP result → SINGULYAR Observation           │
└──────────────────────────────────────────────────────────────┘
                       ↓ JSON-RPC (stdio/SSE/HTTP)
┌──────────────────────────────────────────────────────────────┐
│  MCP server (filesystem / git / postgres / web-search / ...)  │
└──────────────────────────────────────────────────────────────┘
```

## Files

| File                          | Class / symbol           | Purpose                                                |
| ----------------------------- | ------------------------- | ------------------------------------------------------ |
| `__init__.py`                 | *(package)*               | Re-exports public API                                  |
| `base_adapter.py`             | `MCPAdapter`, `MCP_VERSION` | Abstract bridge + pinned MCP revision (ADR-0008)   |
| `filesystem_adapter.py`       | `FilesystemAdapter`       | Local FS ops via MCP filesystem server                |
| `git_adapter.py`              | `GitAdapter`              | Git ops via MCP git server                            |
| `postgres_adapter.py`         | `PostgresAdapter`         | Postgres ops via MCP postgres server                  |
| `web_search_adapter.py`       | `WebSearchAdapter`        | Web search + URL fetch via MCP web-search server      |
| `registry.py`                 | `MCPCapabilityRegistry`, `default_registry` | Capability lookup used by SINGULYAR planner |
| `__main__.py`                 | *(CLI)*                   | `python -m tooling.agents.mcp {list, verify}`         |
| `tests/test_adapters.py`      | *(unittest)*              | Per-adapter interface + capability field checks       |
| `tests/test_registry.py`      | *(unittest)*              | Registry `register` + `find_compatible` behaviour     |

## Mapping table — MCP server → SINGULYAR Capability → Adapter class

| MCP server        | SINGULYAR operation    | capability_id         | adapter_id       | idempotent? | risk   | Adapter class        |
| ----------------- | ---------------------- | --------------------- | ---------------- | ----------: | ------ | -------------------- |
| `filesystem`      | `create_file`          | `fs-create-file`     | `mcp-filesystem` | yes         | medium | `FilesystemAdapter`  |
| `filesystem`      | `write_file`           | `fs-write-file`       | `mcp-filesystem` | yes         | medium | `FilesystemAdapter`  |
| `filesystem`      | `read_file`            | `fs-read-file`        | `mcp-filesystem` | yes         | low    | `FilesystemAdapter`  |
| `filesystem`      | `delete_file`          | `fs-delete-file`      | `mcp-filesystem` | yes         | high   | `FilesystemAdapter`  |
| `filesystem`      | `list_dir`             | `fs-list-dir`         | `mcp-filesystem` | yes         | low    | `FilesystemAdapter`  |
| `filesystem`      | `append_file`          | `fs-append-file`      | `mcp-filesystem` | **no**      | medium | `FilesystemAdapter`  |
| `git`             | `commit`               | `git-commit`          | `mcp-git`        | **no**      | high   | `GitAdapter`         |
| `git`             | `push`                 | `git-push`            | `mcp-git`        | yes         | high   | `GitAdapter`         |
| `git`             | `create_branch`        | `git-create-branch`   | `mcp-git`        | yes         | medium | `GitAdapter`         |
| `git`             | `checkout`             | `git-checkout`         | `mcp-git`        | yes         | medium | `GitAdapter`         |
| `git`             | `merge`                | `git-merge`            | `mcp-git`        | **no**      | high   | `GitAdapter`         |
| `postgres`        | `execute_query`        | `pg-execute-query`    | `mcp-postgres`   | yes         | low    | `PostgresAdapter`    |
| `postgres`        | `execute_migration`    | `pg-execute-migration` | `mcp-postgres`   | yes         | high   | `PostgresAdapter`    |
| `postgres`        | `upsert_row`           | `pg-upsert-row`       | `mcp-postgres`   | yes         | medium | `PostgresAdapter`    |
| `websearch`       | `search`               | `ws-search`           | `mcp-websearch`  | yes (TTL)   | low    | `WebSearchAdapter`   |
| `websearch`       | `fetch_url`            | `ws-fetch-url`        | `mcp-websearch`  | yes         | low    | `WebSearchAdapter`   |

## Idempotency contract

| Operation           | Idempotent? | Why                                                                          |
| ------------------- | ----------: | ---------------------------------------------------------------------------- |
| `create_file`       | yes         | Creating a path that already exists with the same content = no-op            |
| `write_file`        | yes         | Writing the same content twice leaves the file in the same end state         |
| `append_file`       | **no**      | Each call appends bytes; repeated calls accumulate                            |
| `delete_file`       | yes         | Deleting a non-existent path = no-op                                         |
| `git commit`        | **no**      | Each call mints a new commit hash                                            |
| `git push`          | yes         | Pushing a ref whose remote has the same hash = "Everything up-to-date"       |
| `git create_branch`| yes         | Creating a branch that already exists = no-op (deterministic name)          |
| `git checkout`      | yes         | Switching to the same ref = no-op                                            |
| `git merge`         | **no**      | A repeated merge may create a new merge commit if upstream advanced         |
| `execute_query`     | yes         | SELECT does not change state                                                  |
| `execute_migration` | yes         | Version tracking in `schema_migrations` dedupes                              |
| `upsert_row`        | yes         | PK-based upsert with same row = no-op                                         |
| `search`            | yes (TTL)   | Same `(query, time_window)` returns cached results until TTL expires         |
| `fetch_url`         | yes         | Same URL = same content (until source changes)                              |

SINGULYAR EIR **never auto-retries** a non-idempotent capability whose state
is ABSENT — `recover()` routes to `WAITING_FOR_HUMAN` instead of guessing.

## `read_state` contract

Every adapter's `read_state(intent, idempotency_key) → Observation` returns:

| `Observation.status` | Meaning                                          | Kernel action           |
| -------------------- | ------------------------------------------------ | ----------------------- |
| `PRESENT`            | Effect exists under this idempotency key           | Verify value/count       |
| `ABSENT`             | Effect definitely did NOT happen                 | Retry if `cap.idempotent` |
| `UNAVAILABLE`        | Cannot tell (server down, query failed)          | Stay UNKNOWN, no retry   |

Returning `None` is forbidden — it would erase the ABSENT/UNAVAILABLE
distinction that `Runtime.recover()` relies on.

## MCP version pinning policy (ADR-0008)

- `MCP_VERSION = "2026-07-28"` in `base_adapter.py` — the stateless-core
  spec revision every adapter in this package is tested against.
- `python -m tooling.agents.mcp verify` asserts this matches the version
  pinned by ADR-0008.
- Bumping the version requires:
  1. A migration ADR (`docs/adr/NNNN-mcp-update-YYYY-MM.md`) listing what
     changed, which adapters are affected, breaking changes, backward-compat.
  2. Update `MCP_VERSION` here.
  3. Update `ADR_0008_MCP_VERSION` in `__main__.py` (kept in lock-step).
  4. CI gate `mcp-compat-check` (ADR-0008 §3) verifies adapters conform.
- Quarterly review (ADR-0008 §3): check whether MCP spec has changed since
  last bump. If yes — write the migration ADR. If no — close the review.

## How to add a new adapter

1. **Pick the MCP server** (e.g. `mcp-server-slack`).
2. **Subclass `MCPAdapter`** in a new file `slack_adapter.py`:

   ```python
   from .base_adapter import MCPAdapter, Capability

   class SlackAdapter(MCPAdapter):
       adapter_id = "mcp-slack"
       mcp_server = "slack"
       CAPABILITIES = (
           Capability(
               capability_id="slack-send-message",
               operation="send_message",
               adapter_id="mcp-slack",
               risk_ceiling="medium",
               offline=False,
               idempotent=True,    # same (channel, text, ts) = dedupe by Slack
               local_only=False,
               priority=20,
           ),
       )

       def _call_mcp_tool(self, tool_name, args, idempotency_key):
           # Real: dispatch JSON-RPC `tools/call` to the Slack MCP server.
           # Scaffold: simulate in-process.
           ...
   ```

3. **Re-export it** from `tooling/agents/mcp/__init__.py` and add it to
   `ALL_ADAPTER_CLASSES` in `__main__.py`.
4. **Add tests** in `tests/test_adapters.py` (interface, capability fields,
   idempotency semantics).
5. **Run** `python -m tooling.agents.mcp verify` — must exit 0.
6. **Update the mapping table** above.

## Running

```bash
# List all registered capabilities
python -m tooling.agents.mcp list

# Smoke-test every adapter
python -m tooling.agents.mcp verify

# Run unit tests (from repo root)
python -m unittest discover -s tooling/agents/mcp/tests -v
```

## Scaffolds vs. production

These files are **scaffolds**: stdlib only, no PyPI deps. The
`_call_mcp_tool` methods simulate an MCP server in-process so the pattern
is verifiable end-to-end without a real server.

Production migration:
- Replace `_call_mcp_tool` with a real MCP client dispatch
  (`@modelcontextprotocol/sdk` for JS, or a Python MCP client).
- Wire `read_state` to call the server's read-side tool (independent
  verifier — never the same call that `execute` used).
- Cache layer for web search must live between adapter and server.

## References

- ADR-0008 — MCP version pin (this package enforces it)
- ADR-0012 — SINGULYAR EIR as Layer 5 (this package implements §"Интеграционные точки")
- `runtime/src/singulyar_runtime.py` — `Adapter`, `Intent`, `Capability`, `Observation`
- `runtime/schemas/capability.schema.json` — JSON Schema for `Capability`
- [MCP specification][mcp]

[mcp]: https://modelcontextprotocol.io/
