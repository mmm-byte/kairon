"""Registry of plug-in agents, MCP adapters, and IPT templates."""
from __future__ import annotations

from typing import Any, Callable

from aurex.mcp.base import MCPAdapter
from aurex.mcp.simulated import (
    SimulatedBrokerMCP,
    SimulatedMarketDataMCP,
    SimulatedNewsMCP,
)


class Registry:
    """In-memory registries for agents, MCP adapters, and IPT templates."""

    def __init__(self) -> None:
        self._agents: dict[str, Callable[..., Any]] = {}
        self._mcps: dict[str, MCPAdapter] = {
            "aurex.mcp.simulated.SimulatedBrokerMCP": SimulatedBrokerMCP(),
            "aurex.mcp.simulated.SimulatedMarketDataMCP": SimulatedMarketDataMCP(),
            "aurex.mcp.simulated.SimulatedNewsMCP": SimulatedNewsMCP(),
        }
        self._ipt_templates: dict[str, dict] = {}

    # ---- agents ----
    def register_agent(self, name: str, factory: Callable[..., Any]) -> None:
        self._agents[name] = factory

    def get_agent(self, name: str) -> Callable[..., Any]:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self._agents[name]

    @property
    def agent_names(self) -> list[str]:
        return list(self._agents.keys())

    # ---- MCP ----
    def register_mcp(self, key: str, adapter: MCPAdapter) -> None:
        self._mcps[key] = adapter

    def resolve_mcp(self, key: str) -> MCPAdapter:
        if key not in self._mcps:
            raise KeyError(f"MCP '{key}' not registered")
        return self._mcps[key]

    # ---- IPT templates ----
    def register_template(self, name: str, payload: dict) -> None:
        self._ipt_templates[name] = payload

    def get_template(self, name: str) -> dict:
        if name not in self._ipt_templates:
            raise KeyError(f"Template '{name}' not registered")
        return dict(self._ipt_templates[name])

    @property
    def template_names(self) -> list[str]:
        return list(self._ipt_templates.keys())


GLOBAL_REGISTRY = Registry()