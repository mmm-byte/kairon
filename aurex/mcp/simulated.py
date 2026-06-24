"""Simulated MCP adapters. Default for any IPT not yet wired to a real broker."""
from __future__ import annotations

from aurex.mcp.base import MCPAdapter, MCPRequest, MCPResponse


class SimulatedBrokerMCP:
    name = "simulated_broker"
    endpoint_group = "BROKER"

    def handle(self, request: MCPRequest) -> MCPResponse:
        tool = request.tool
        if tool == "place_order":
            return MCPResponse(
                request_id=request.request_id,
                ok=True,
                payload={
                    "simulated": True,
                    "order_id": f"SIM-{request.request_id[:8]}",
                    "status": "filled",
                    "echo": request.params,
                },
            )
        if tool == "cancel_order":
            return MCPResponse(request_id=request.request_id, ok=True, payload={"cancelled": True})
        return MCPResponse(request_id=request.request_id, ok=False, payload={}, error=f"unknown tool '{tool}'")

    def health(self) -> dict:
        return {"ok": True, "mode": "simulated", "latency_ms": 5}


class SimulatedMarketDataMCP:
    name = "simulated_market_data"
    endpoint_group = "MARKET_DATA"

    def handle(self, request: MCPRequest) -> MCPResponse:
        symbol = request.params.get("symbol", "?")
        return MCPResponse(
            request_id=request.request_id,
            ok=True,
            payload={"symbol": symbol, "price": 100.0, "simulated": True},
        )

    def health(self) -> dict:
        return {"ok": True, "mode": "simulated"}


class SimulatedNewsMCP:
    name = "simulated_news"
    endpoint_group = "NEWS"

    def handle(self, request: MCPRequest) -> MCPResponse:
        return MCPResponse(
            request_id=request.request_id,
            ok=True,
            payload={"articles": [], "simulated": True},
        )

    def health(self) -> dict:
        return {"ok": True, "mode": "simulated"}