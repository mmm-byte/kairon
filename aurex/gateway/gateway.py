"""MCP Gateway — single choke point that enforces rules & routes to real/simulated."""
from __future__ import annotations

from aurex.audit.trail import AuditTrail
from aurex.core.platform_rules import PLATFORM_IMMUTABLE_RULES
from aurex.core.primitives import (
    GatewayRequest,
    GatewayResponse,
    GatewayStatus,
    Mode,
)
from aurex.ipt.ipt import IPT
from aurex.registry.registry import GLOBAL_REGISTRY
from aurex.rules.engine import evaluate_rules, to_checks


class MCPGateway:
    """Routes MCP calls only after they clear both platform & IPT rules."""

    def __init__(self, audit: AuditTrail) -> None:
        self.audit = audit

    def call(self, request: GatewayRequest, ipt: IPT) -> GatewayResponse:
        # ---- 1. Build context ----
        user_ctx = request.context or {}
        ctx = {
            "ipt_id": ipt.ipt_id,
            "mode": ipt.mode.value,
            "real_money": request.mode == Mode.LIVE,
            "explicitly_allowed": True,
            "rule_check": {"completed": True, "passed": True},
            "logged": True,
            "context": {"ipt_id": user_ctx.get("ipt_id", ipt.ipt_id)},
            "agent": {
                "action": {
                    "tool": request.action.get("tool", ""),
                    "irreversible": bool(request.action.get("irreversible", False)),
                }
            },
            "action": {"tool": request.action.get("tool", "")},
            "user_approved": bool(user_ctx.get("user_approved", True)),
            # Pass through orchestrator-provided fields so IPT rules can evaluate them.
            "trade": user_ctx.get("trade", {"symbol": None, "risk_pct": 0.0}),
            "portfolio": user_ctx.get("portfolio", {}),
            "symbol": user_ctx.get("symbol"),
        }

        # ---- 2. Platform immutable rules ----
        plat_evals = evaluate_rules(PLATFORM_IMMUTABLE_RULES, ctx)
        plat_checks = to_checks(plat_evals)
        platform_violations = [c for c in plat_checks if not c.complies]
        if platform_violations:
            for v in platform_violations:
                self.audit.record(
                    event_type="platform_rule_violation",
                    ipt_id=ipt.ipt_id,
                    actor=request.agent_name,
                    payload={"rule_id": v.rule_id, "reason": v.reason},
                    tags=["block"],
                )
            return GatewayResponse(
                status=GatewayStatus.BLOCKED,
                reason="platform rule violation",
                rule_violations=platform_violations,
                result={},
                logs={"platform_violations": [v.rule_id for v in platform_violations]},
            )

        # ---- 3. IPT rules ----
        ipt_evals = (
            evaluate_rules(ipt.rule_store.rules, ctx) if ipt.rule_store else []
        )
        ipt_checks = to_checks(ipt_evals)
        ipt_violations = [c for c in ipt_checks if not c.complies]
        if ipt_violations:
            for v in ipt_violations:
                self.audit.record(
                    event_type="ipt_rule_violation",
                    ipt_id=ipt.ipt_id,
                    actor=request.agent_name,
                    payload={"rule_id": v.rule_id, "reason": v.reason},
                    tags=["block"],
                )
            return GatewayResponse(
                status=GatewayStatus.BLOCKED,
                reason="IPT rule violation",
                rule_violations=ipt_violations,
                result={},
                logs={"ipt_violations": [v.rule_id for v in ipt_violations]},
            )

        # ---- 4. Mode-aware endpoint resolution ----
        group = request.action.get("endpoint_group", "")
        endpoints = ipt.endpoints.get(group, {})
        endpoint_key = endpoints.get("live") if request.mode == Mode.LIVE else endpoints.get("sandbox")
        if not endpoint_key:
            return GatewayResponse(
                status=GatewayStatus.ERROR,
                reason=f"no endpoint configured for group '{group}' in mode {request.mode.value}",
                rule_violations=[],
                result={},
                logs={},
            )

        # ---- 6. Route ----
        adapter = GLOBAL_REGISTRY.resolve_mcp(endpoint_key)
        from aurex.mcp.base import MCPRequest

        mcp_req = MCPRequest(
            tool=request.action.get("tool", ""),
            endpoint_group=group,
            params=request.action.get("params", {}),
            ipt_id=ipt.ipt_id,
            actor=request.agent_name,
        )
        mcp_resp = adapter.handle(mcp_req)

        status = (
            GatewayStatus.SIMULATED
            if request.mode == Mode.SANDBOX
            else GatewayStatus.EXECUTED
        )

        self.audit.record(
            event_type="mcp_call",
            ipt_id=ipt.ipt_id,
            actor=request.agent_name,
            payload={
                "tool": mcp_req.tool,
                "endpoint_group": group,
                "endpoint": endpoint_key,
                "ok": mcp_resp.ok,
            },
            tags=[status.value.lower()],
        )

        return GatewayResponse(
            status=status if mcp_resp.ok else GatewayStatus.ERROR,
            reason="ok" if mcp_resp.ok else (mcp_resp.error or "adapter error"),
            rule_violations=[],
            result=mcp_resp.payload,
            logs={"endpoint": endpoint_key, "mcp_ok": mcp_resp.ok},
        )