"""Web search MCP adapter — bridges an MCP web-search server to SINGULYAR EIR.

Маппинг операций::

    SINGULYAR operation   MCP tool          idempotent?   risk
    -------------------   --------------    -----------   ----
    search                websearch_search   yes (cached) low
    fetch_url             websearch_fetch    yes           low

Особое внимание:
  * search — идемпортентен в пределах TTL-окна кэша: одинаковый
    (query, timestamp_window) → одинаковый результат. SINGULYAR передаёт
    idempotency_key = "search:<query_hash>:<timestamp_window>".
    Вне окна кэша результат может отличаться — операция формально
    идемпортентна, но verifier должен учитывать TTL.
  * fetch_url — идемпортентен: запрос того же URL = тот же контент
    (пока источник не меняется). Idempotency_key = "fetch:<url_hash>".

`read_state` проверяет:
  * кэш всё ещё валиден (search: TTL не истёк)
  * URL достижим (fetch_url: HTTP 200)
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

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


# Default cache TTL for search results (seconds). Real impl: configurable.
SEARCH_CACHE_TTL = 300  # 5 minutes


def _query_idempotency_key(query: str, timestamp_window: int = SEARCH_CACHE_TTL) -> str:
    """Стабильный ключ для search: (query, timestamp_window) → тот же ключ.

    `timestamp_window` — длительность в секундах, в течение которой
    результаты считаются идентичными (например, 5 минут). Окно округляется
    до целого числа, что даёт детерминированный ключ.
    """
    window = int(time.time()) // timestamp_window
    h = hashlib.sha256()
    h.update(query.encode("utf-8"))
    h.update(b"\x00")
    h.update(str(window).encode("utf-8"))
    return f"search:{h.hexdigest()[:16]}"


def _url_idempotency_key(url: str) -> str:
    """Стабильный ключ для fetch_url: URL → ключ. Одинаковый URL → одинаковый результат."""
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"fetch:{h[:16]}"


class WebSearchAdapter(MCPAdapter):
    """Web search + URL fetch through an MCP web-search server (scaffold).

    In-process simulation:
      * `_cache[query] = (results, expiry_ts)`
      * `_pages[url] = body_text`

    Real impl: dispatch JSON-RPC `tools/call` to an MCP web-search server
    (e.g. brave-search MCP, Tavily MCP). Cache layer MUST sit between
    adapter and server so that repeated intents under the same idempotency
    key return the same cached payload.

    Capabilities declared:
      * `ws-search`    (search,    idempotent (within TTL), low)   — read-only
      * `ws-fetch-url` (fetch_url, idempotent,             low)   — read-only
    """

    adapter_id = "mcp-websearch"
    mcp_server = "websearch"

    CAPABILITIES = (
        Capability(
            capability_id="ws-search",
            operation="search",
            adapter_id="mcp-websearch",
            risk_ceiling="low",   # read-only external call
            offline=False,        # requires network
            idempotent=True,      # within TTL window — see _query_idempotency_key
            local_only=False,
            priority=10,
        ),
        Capability(
            capability_id="ws-fetch-url",
            operation="fetch_url",
            adapter_id="mcp-websearch",
            risk_ceiling="low",
            offline=False,
            idempotent=True,      # fetching same URL = same content (until source changes)
            local_only=False,
            priority=10,
        ),
    )

    def __init__(self, *, mcp_endpoint: Optional[str] = None, available: bool = True,
                 cache_ttl: int = SEARCH_CACHE_TTL):
        super().__init__(mcp_endpoint=mcp_endpoint, available=available)
        # In-process simulation of the MCP web-search server's cache.
        self._cache: Dict[str, tuple] = {}  # query → (results, expiry_ts)
        self._pages: Dict[str, str] = {}    # url → body
        self._fetched: Dict[str, str] = {} # idempotency_key → url
        self.cache_ttl = cache_ttl

    # -- MCP tool dispatch (stub) -----------------------------------------
    def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        # tool_name = f"websearch_{operation}" → strip the prefix once.
        op = tool_name.split("_", 1)[1] if "_" in tool_name else tool_name
        if op == "search":
            return self._do_search(arguments, idempotency_key)
        if op == "fetch_url":
            return self._do_fetch(arguments, idempotency_key)
        raise NotExecuted(f"unknown websearch operation: {op!r}")

    def _do_search(self, args: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        query = args.get("query")
        if not query:
            raise NotExecuted("search: 'query' argument required")
        now = time.time()
        cached = self._cache.get(query)
        if cached and cached[1] > now:
            return {"query": query, "results": cached[0], "cached": True}
        # Simulated results — deterministic for the same query string.
        results = [
            {"url": f"https://example.com/{i}/{abs(hash(query)) & 0xFFFF}",
             "title": f"Result {i} for {query}",
             "snippet": f"Snippet {i} for {query}"}
            for i in range(1, 4)
        ]
        self._cache[query] = (results, now + self.cache_ttl)
        return {"query": query, "results": results, "cached": False}

    def _do_fetch(self, args: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        url = args.get("url")
        if not url:
            raise NotExecuted("fetch_url: 'url' argument required")
        # Simulated fetch — deterministic content per URL.
        if url not in self._pages:
            self._pages[url] = f"<html><body>Simulated content for {url}</body></html>"
        self._fetched[idempotency_key] = url
        return {"url": url, "status": 200, "body": self._pages[url], "bytes": len(self._pages[url])}

    # -- read_state: independent verifier-side query ----------------------
    def read_state(self, intent: Intent, idempotency_key: str) -> Observation:
        if not self.available:
            return Observation(UNAVAILABLE)
        op = intent.operation
        if op == "search":
            query = intent.payload.get("query")
            if not query:
                return Observation(UNAVAILABLE)
            cached = self._cache.get(query)
            if not cached:
                return Observation(ABSENT, {"query": query}, 0)
            results, expiry = cached
            if expiry <= time.time():
                # Cache expired — result is stale, treat as ABSENT (verifier FAILs).
                return Observation(ABSENT, {"query": query, "expired": True}, 0)
            return Observation(PRESENT, {"query": query, "results": results}, 1)
        if op == "fetch_url":
            url = self._fetched.get(idempotency_key) or intent.payload.get("url")
            if not url:
                return Observation(UNAVAILABLE)
            if url not in self._pages:
                # URL was never successfully fetched — ABSENT.
                return Observation(ABSENT, {"url": url}, 0)
            return Observation(
                PRESENT,
                {"url": url, "status": 200, "body": self._pages[url]},
                1,
            )
        return Observation(UNAVAILABLE)
