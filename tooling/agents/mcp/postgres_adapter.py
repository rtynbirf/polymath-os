"""Postgres MCP adapter — bridges an MCP postgres server to SINGULYAR EIR.

Маппинг операций::

    SINGULYAR operation   MCP tool              idempotent?   risk
    -------------------   -------------------    -----------   ----
    execute_query          postgres_query        yes (read)    low
    execute_migration      postgres_migrate      yes (version) high
    upsert_row             postgres_upsert       yes (PK)      medium

Особое внимание:
  * execute_query — read-only, идемпортентен по определению (SELECT не меняет состояние).
  * execute_migration — идемпортентен благодаря tracking-таблице schema_migrations:
    повторное применение той же версии = no-op (MCP server видит, что версия уже применена).
    Idempotency_key = "migration_<version>".
  * upsert_row — идемпортентен с PRIMARY KEY: повторный upsert того же (PK, payload)
    оставляет таблицу в том же состоянии. Idempotency_key = "upsert_<table>_<pk>".

`read_state` проверяет:
  * строка существует с ожидаемыми полями (upsert_row)
  * миграция применена (execute_migration: schema_migrations.version присутствует)
  * схема таблицы совпадает с ожидаемой (execute_migration: columns match)
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from .base_adapter import (
    MCPAdapter,
    Capability,
    Intent,
    Observation,
    PRESENT,
    ABSENT,
    UNAVAILABLE,
    NotExecuted,
)


def _migration_idempotency_key(version: str) -> str:
    """Стабильный ключ для миграций: одна версия → один ключ → no-op при повторе."""
    return f"migration:{version}"


def _upsert_idempotency_key(table: str, pk_value: Any) -> str:
    """Стабильный ключ для upsert: тот же PK → тот же ключ → no-op при повторе."""
    h = hashlib.sha256()
    h.update(table.encode("utf-8"))
    h.update(b"\x00")
    h.update(str(pk_value).encode("utf-8"))
    return f"upsert:{h.hexdigest()[:16]}"


class PostgresAdapter(MCPAdapter):
    """Postgres operations through an MCP postgres server (scaffold).

    In-process simulation:
      * `_rows[table][pk] = row_dict`
      * `_migrations: set[str]`  — applied version strings
      * `_schemas[table] = [col_name, ...]`

    Real impl: dispatch JSON-RPC `tools/call` to an MCP postgres server
    (e.g. @modelcontextprotocol/server-postgres) — read-only for queries,
    transactional for migrations/upserts.

    Capabilities declared:
      * `pg-execute-query`     (execute_query,     idempotent, low)    — read-only
      * `pg-execute-migration` (execute_migration, idempotent, high)
      * `pg-upsert-row`        (upsert_row,        idempotent, medium)
    """

    adapter_id = "mcp-postgres"
    mcp_server = "postgres"

    CAPABILITIES = (
        Capability(
            capability_id="pg-execute-query",
            operation="execute_query",
            adapter_id="mcp-postgres",
            risk_ceiling="low",   # read-only
            offline=False,       # requires DB connection
            idempotent=True,     # SELECT is inherently idempotent
            local_only=False,    # DB is remote by default
            priority=5,
        ),
        Capability(
            capability_id="pg-execute-migration",
            operation="execute_migration",
            adapter_id="mcp-postgres",
            risk_ceiling="high",  # schema change
            offline=False,
            idempotent=True,     # version tracking dedupes
            local_only=False,
            priority=30,
        ),
        Capability(
            capability_id="pg-upsert-row",
            operation="upsert_row",
            adapter_id="mcp-postgres",
            risk_ceiling="medium",
            offline=False,
            idempotent=True,     # PK-based upsert is idempotent
            local_only=False,
            priority=15,
        ),
    )

    def __init__(self, *, mcp_endpoint: Optional[str] = None, available: bool = True):
        super().__init__(mcp_endpoint=mcp_endpoint, available=available)
        # In-process simulation of a postgres DB.
        self._rows: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        self._schemas: Dict[str, List[str]] = {}
        self._migrations: set[str] = set()

    # -- MCP tool dispatch (stub) -----------------------------------------
    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        # tool_name = f"postgres_{operation}" → strip the prefix once.
        op = tool_name.split("_", 1)[1] if "_" in tool_name else tool_name
        if op == "execute_query":
            return self._do_query(arguments)
        if op == "execute_migration":
            return self._do_migration(arguments)
        if op == "upsert_row":
            return self._do_upsert(arguments)
        raise NotExecuted(f"unknown postgres operation: {op!r}")

    def _do_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        table = args.get("table")
        if not table:
            raise NotExecuted("query: 'table' argument required")
        rows = list(self._rows.get(table, {}).values())
        # Optional filter by column=value (simulating WHERE).
        filter_col = args.get("filter_column")
        filter_val = args.get("filter_value")
        if filter_col is not None and filter_val is not None:
            rows = [r for r in rows if r.get(filter_col) == filter_val]
        return {"table": table, "rows": rows, "count": len(rows)}

    def _do_migration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        version = args.get("version")
        if not version:
            raise NotExecuted("migration: 'version' argument required")
        if version in self._migrations:
            return {"version": version, "applied": False, "already_applied": True}
        # Apply migration: register columns if provided.
        table = args.get("table")
        columns = args.get("columns")
        if table and columns:
            self._schemas[table] = list(columns)
            self._rows.setdefault(table, {})
        self._migrations.add(version)
        return {"version": version, "applied": True, "already_applied": False}

    def _do_upsert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        table = args.get("table")
        pk_col = args.get("pk_column", "id")
        row = args.get("row")
        if not table or row is None:
            raise NotExecuted("upsert: 'table' and 'row' arguments required")
        if pk_col not in row:
            raise NotExecuted(f"upsert: row missing pk column {pk_col!r}")
        table_rows = self._rows.setdefault(table, {})
        pk_value = row[pk_col]
        existed = pk_value in table_rows
        table_rows[pk_value] = dict(row)
        return {"table": table, "pk": pk_value, "upserted": True, "existed": existed}

    # -- read_state: independent verifier-side query ----------------------
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        if not self.available:
            return Observation(UNAVAILABLE)
        op = intent.operation
        if op == "execute_query":
            # Read-only ops are stateless — the "effect" is the returned result.
            # We can't re-run them as effects, so we report PRESENT only if
            # the adapter has previously executed this exact query under the key.
            if idempotency_key not in self._effects:
                return Observation(ABSENT, None, 0)
            return Observation(PRESENT, dict(self._effects[idempotency_key]), 1)
        if op == "execute_migration":
            version = intent.payload.get("version")
            if not version:
                return Observation(UNAVAILABLE)
            if version not in self._migrations:
                return Observation(ABSENT, {"version": version}, 0)
            # Verify schema matches expected (if expected_columns provided).
            expected_cols = intent.expected.get("columns")
            table = intent.payload.get("table")
            if expected_cols and table:
                actual_cols = self._schemas.get(table, [])
                if actual_cols != list(expected_cols):
                    return Observation(
                        PRESENT,
                        {"version": version, "table": table,
                         "columns": actual_cols, "expected_columns": expected_cols},
                        1,
                    )
            return Observation(PRESENT, {"version": version, "applied": True}, 1)
        if op == "upsert_row":
            table = intent.payload.get("table")
            pk_col = intent.payload.get("pk_column", "id")
            row = intent.payload.get("row")
            if not table or row is None:
                return Observation(UNAVAILABLE)
            pk_value = row.get(pk_col)
            if pk_value is None:
                return Observation(UNAVAILABLE)
            stored = self._rows.get(table, {}).get(pk_value)
            if stored is None:
                return Observation(ABSENT, {"table": table, "pk": pk_value}, 0)
            # Verify row matches expected fields (verifier will compare).
            return Observation(PRESENT, {"table": table, "row": stored}, 1)
        return Observation(UNAVAILABLE)
