"""Orchestrator: runs the agent pipeline, aggregates, applies rule & guideline filters, dispatches to gateway."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable

from aurex.agents.agent import RuleFirstAgent, output_to_dict
from aurex.agents.builtins import BUILTIN_AGENTS
from aurex.audit.trail import AuditTrail
from aurex.core.primitives import (
    AgentOutput,
    DecisionType,
    GatewayRequest,
    Mode,
)
from aurex.gateway.gateway import MCPGateway
from aurex.ipt.ipt import IPT
from aurex.rules.engine import evaluate_rules, to_checks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OrchestrationResult:
    ipt_id: str
    mode: str
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    rule_evaluations: list[dict] = field(default_factory=list)
    final_action: dict = field(default_factory=dict)
    gateway_response: dict = field(default_factory=dict)
    explanation: str = ""
    timestamp: str = field(default_factory=_now)


class Orchestrator:
    """Loads IPT context → runs agents → applies filters → dispatches via gateway."""

    def __init__(
        self,
        *,
        audit: AuditTrail,
        gateway: MCPGateway,
        agent_pipeline: Iterable[str] = (
            "TechnicalAgent",
            "FundamentalAgent",
            "NewsAgent",
            "RiskAgent",
            "TraderAgent",
        ),
        agent_factory: Callable[[str, IPT], RuleFirstAgent] | None = None,
    ) -> None:
        self.audit = audit
        self.gateway = gateway
        self.pipeline = list(agent_pipeline)
        self.agent_factory = agent_factory or self._default_factory

    @staticmethod
    def _default_factory(name: str, ipt: IPT) -> RuleFirstAgent:
        from aurex.agents.agent import LLMRunner
        if name not in BUILTIN_AGENTS:
            raise KeyError(f"Agent '{name}' not in builtins")
        return BUILTIN_AGENTS[name](ipt, LLMRunner())

    def run(self, ipt: IPT, context: dict) -> OrchestrationResult:
        result = OrchestrationResult(ipt_id=ipt.ipt_id, mode=ipt.mode.value)
        outputs: list[AgentOutput] = []

        for name in self.pipeline:
            agent = self.agent_factory(name, ipt)
            out = agent.run(ipt.ipt_id, ipt.mode.value, context)
            outputs.append(out)
            self.audit.record(
                event_type="agent_decision",
                ipt_id=ipt.ipt_id,
                actor=agent.name,
                payload=output_to_dict(out),
            )

        result.agent_outputs = outputs

        # ---- Aggregate: last ABSTAIN wins; otherwise the last ACT ----
        last_act = next(
            (o for o in reversed(outputs) if o.final_decision.get("type") == DecisionType.ACT.value),
            None,
        )
        final_action = last_act.candidate_action if last_act else {"tool": "noop"}

        # ---- Independent rule re-check at the orchestrator level ----
        ctx = {**context, "ipt_id": ipt.ipt_id, "mode": ipt.mode.value}
        evals = evaluate_rules(ipt.rule_store.rules, ctx) if ipt.rule_store else []
        result.rule_evaluations = [
            {"rule_id": e.rule_id, "complies": e.complies, "reason": e.reason} for e in evals
        ]
        violations = [e for e in evals if not e.complies]
        if violations:
            result.final_action = {"tool": "noop"}
            result.explanation = f"BLOCKED at orchestrator: {len(violations)} rule violation(s)."
            self.audit.record(
                event_type="orchestrator_block",
                ipt_id=ipt.ipt_id,
                actor="orchestrator",
                payload={"violations": [v.rule_id for v in violations]},
                tags=["block"],
            )
            return result

        # ---- Dispatch via gateway ----
        gw_req = GatewayRequest(
            ipt_id=ipt.ipt_id,
            agent_name=last_act.agent_name if last_act else "orchestrator",
            mode=Mode(ipt.mode.value),
            action=final_action,
            context={**context, "ipt_id": ipt.ipt_id},
        )
        gw_resp = self.gateway.call(gw_req, ipt)
        result.final_action = final_action
        result.gateway_response = {
            "status": gw_resp.status.value,
            "reason": gw_resp.reason,
            "result": gw_resp.result,
            "logs": gw_resp.logs,
        }
        result.explanation = self._summarize(outputs, result.gateway_response)
        return result

    @staticmethod
    def _summarize(outputs: list[AgentOutput], gw_resp: dict) -> str:
        acted = [o for o in outputs if o.final_decision.get("type") == DecisionType.ACT.value]
        abstained = [o for o in outputs if o.final_decision.get("type") != DecisionType.ACT.value]
        return (
            f"{len(acted)} agent(s) voted ACT, {len(abstained)} ABSTAIN. "
            f"Gateway: {gw_resp.get('status')} — {gw_resp.get('reason')}."
        )