"""MCP base protocol — abstract + simulated implementations."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MCPRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool: str = ""
    endpoint_group: str = ""
    params: dict = field(default_factory=dict)
    ipt_id: str = ""
    actor: str = ""
    timestamp: str = field(default_factory=_now)


@dataclass
class MCPResponse:
    request_id: str
    ok: bool
    payload: dict
    error: str | None = None
    timestamp: str = field(default_factory=_now)


class MCPAdapter(Protocol):
    """Minimal contract every MCP endpoint must satisfy."""

    name: str
    endpoint_group: str

    def handle(self, request: MCPRequest) -> MCPResponse: ...

    def health(self) -> dict: ...