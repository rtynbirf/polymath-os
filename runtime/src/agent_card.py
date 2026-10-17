"""runtime/src/agent_card.py — Agent Card Protocol (per ADR-0023).

Each Polymath-OS agent publishes an Agent Card describing its identity,
capabilities, decree scope, endpoints, and version. Agent Cards are
the A2A-compatible discovery mechanism — other agents (or external
A2A-compatible clients) can fetch this card to learn what the agent
can do and which decrees apply to it.

This is the Polymath-OS-specific extension to standard A2A Agent Cards:
we add `decree_scope` field so callers know which decrees apply BEFORE
issuing an Intent. Without this, callers would hit DECREE_BLOCK events
unpredictably.

Schema:
  {
    "$schema": "...",
    "id": "singulyar-eir.local",
    "name": "SINGULYAR EIR",
    "description": "...",
    "version": "v0.6",
    "protocol_version": "a2a/1.0 + mcp/1.0",
    "capabilities": ["intent.execute", ...],
    "decree_scope": "all",
    "endpoints": [{"type": "http", "url": "..."}],
    "auth": {"type": "decree", ...},
    "maintainer": "rtynbirf",
    "license": "MIT",
    "homepage": "https://github.com/rtynbirf/polymath-os"
  }
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ID validation: lowercase letters, digits, dots, hyphens. Max 64 chars.
# Examples: "singulyar-eir.local", "polymath-os.browser", "cell65-host.llm"
_AGENT_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9.\-]{0,63}$")

# Recognized transport types for endpoints field.
_VALID_TRANSPORT_TYPES = {"http", "https", "websocket", "webrtc", "stdio", "in-process"}

# Required fields in every Agent Card.
_REQUIRED_FIELDS = {"id", "name", "description", "version", "capabilities", "decree_scope"}

# Optional fields (will be defaulted if missing).
_OPTIONAL_FIELDS = {
    "protocol_version", "endpoints", "auth", "maintainer",
    "license", "homepage", "$schema", "tags",
}


class AgentCardError(RuntimeError):
    """Raised when an Agent Card fails validation (fail-closed per ADR-0006)."""
    pass


@dataclass(frozen=True)
class AgentEndpoint:
    """One transport endpoint on an agent."""
    type: str        # http, https, websocket, webrtc, stdio, in-process
    url: str = ""    # URL or descriptor (e.g., "DATA_CHANNEL:polymath-agent" for webrtc)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentCard:
    """An A2A-compatible Agent Card with Polymath-OS decree_scope extension.

    Per ADR-0023. Frozen dataclass — once created, immutable.
    """
    id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    decree_scope: str = "all"
    protocol_version: str = "a2a/1.0 + mcp/1.0"
    endpoints: List[AgentEndpoint] = field(default_factory=list)
    auth: Dict[str, Any] = field(default_factory=lambda: {"type": "decree"})
    maintainer: str = "polymath-os"
    license: str = "MIT"
    homepage: str = "https://github.com/rtynbirf/polymath-os"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate the card."""
        # Validate id format.
        if not _AGENT_ID_REGEX.match(self.id):
            raise AgentCardError(
                f"Invalid agent id '{self.id}': must match {_AGENT_ID_REGEX.pattern}"
            )
        # Validate required fields are non-empty.
        for f in ("name", "description", "version"):
            v = getattr(self, f)
            if not v or not isinstance(v, str):
                raise AgentCardError(f"Agent Card field '{f}' must be non-empty string")
        # Validate capabilities list.
        if not isinstance(self.capabilities, list) or not self.capabilities:
            raise AgentCardError("capabilities must be a non-empty list")
        for cap in self.capabilities:
            if not isinstance(cap, str) or not cap:
                raise AgentCardError(f"Each capability must be a non-empty string, got: {cap}")
        # Validate decree_scope.
        if not isinstance(self.decree_scope, str) or not self.decree_scope:
            raise AgentCardError(
                f"decree_scope must be non-empty string (use 'all' for global). Got: {self.decree_scope}"
            )
        # Validate endpoints.
        for ep in self.endpoints:
            if ep.type not in _VALID_TRANSPORT_TYPES:
                raise AgentCardError(
                    f"Invalid endpoint type '{ep.type}'. Must be one of: {sorted(_VALID_TRANSPORT_TYPES)}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict (for JSON output)."""
        d = asdict(self)
        # asdict() recurses into AgentEndpoint dataclass too.
        d["endpoints"] = [
            {"type": ep["type"], "url": ep["url"], "metadata": ep.get("metadata", {})}
            for ep in d["endpoints"]
        ]
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """Construct from dict (e.g., parsed JSON)."""
        if not isinstance(data, dict):
            raise AgentCardError(f"Agent Card must be a dict, got: {type(data)}")
        # Check required fields.
        missing = _REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise AgentCardError(f"Agent Card missing required fields: {sorted(missing)}")
        # Check for unknown fields (warn but don't fail).
        unknown = set(data.keys()) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS
        if unknown:
            # Don't fail — forward-compatible with future A2A extensions.
            pass
        # Parse endpoints.
        endpoints: List[AgentEndpoint] = []
        for ep_data in data.get("endpoints", []):
            if not isinstance(ep_data, dict):
                raise AgentCardError(f"Endpoint must be dict, got: {type(ep_data)}")
            endpoints.append(AgentEndpoint(
                type=ep_data.get("type", ""),
                url=ep_data.get("url", ""),
                metadata=ep_data.get("metadata", {}),
            ))
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            capabilities=list(data["capabilities"]),
            decree_scope=data.get("decree_scope", "all"),
            protocol_version=data.get("protocol_version", "a2a/1.0 + mcp/1.0"),
            endpoints=endpoints,
            auth=data.get("auth", {"type": "decree"}),
            maintainer=data.get("maintainer", "polymath-os"),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", "https://github.com/rtynbirf/polymath-os"),
            tags=list(data.get("tags", [])),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AgentCard":
        """Construct from JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AgentCardError(f"Invalid JSON: {e}")
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Path) -> "AgentCard":
        """Construct from a .json file path."""
        path = Path(path)
        if not path.exists():
            raise AgentCardError(f"Agent Card file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_json(f.read())
        except OSError as e:
            raise AgentCardError(f"Cannot read Agent Card file {path}: {e}")

    def save_to_file(self, path: Path) -> None:
        """Save the Agent Card to a .json file (typically `.well-known/agent.json`)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=2))
            f.write("\n")


# Default Agent Cards for the well-known Polymath-OS agents.

SINGULYAR_EIR_CARD = AgentCard(
    id="singulyar-eir.local",
    name="SINGULYAR EIR",
    description="Execution kernel — preserves intent across executor changes; enforces human decrees before policy",
    version="v0.6",
    capabilities=[
        "intent.execute", "intent.recover", "intent.cancel",
        "evidence.query", "decree.check_compliance",
    ],
    decree_scope="all",
    endpoints=[
        AgentEndpoint(type="in-process", url="python:runtime.src.singulyar_runtime.Runtime"),
        AgentEndpoint(type="http", url="http://localhost:7654/agent/singulyar"),
    ],
    auth={"type": "decree", "description": "All requests checked against DecreeLog before execution"},
    tags=["layer-5", "execution-kernel", "decree-enforced"],
)

POLYMATH_OS_BROWSER_CARD = AgentCard(
    id="polymath-os.browser",
    name="Polymath-OS Browser",
    description="Sovereign browser shell — zero corporate dependencies; decree portal UI; intent runtime",
    version="v0.6",
    capabilities=[
        "browser.navigate", "decree.issue", "decree.list",
        "intent.compose", "evidence.view",
    ],
    decree_scope="polymath-os",
    endpoints=[
        AgentEndpoint(type="in-process", url="apps/browser/"),
        AgentEndpoint(type="webrtc", url="DATA_CHANNEL:polymath-browser"),
    ],
    auth={"type": "decree", "description": "All browser actions checked against decrees scope=polymath-os"},
    tags=["layer-2", "browser", "decree-portal"],
)

CELL65_LLM_CARD = AgentCard(
    id="cell65-host.llm",
    name="cell65 LLM",
    description="Self-hosted LLM inference — cell65-host server, zero cloud dependencies, MIT/Apache open-weight models",
    version="v0.4",
    capabilities=[
        "llm.command", "llm.answer", "llm.generate", "llm.check_status",
    ],
    decree_scope="singulyar",
    endpoints=[
        AgentEndpoint(type="http", url="http://cell65.local:8080/v1"),
        AgentEndpoint(type="webrtc", url="DATA_CHANNEL:cell65-llm"),
    ],
    auth={"type": "decree", "description": "LLM requests checked against decrees scope=singulyar before inference"},
    tags=["layer-2", "llm", "self-hosted", "cell65"],
)

ALL_DEFAULT_CARDS: List[AgentCard] = [SINGULYAR_EIR_CARD, POLYMATH_OS_BROWSER_CARD, CELL65_LLM_CARD]
