"""Sandbox simulation engine."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from aurex.agents.agent import LLMRunner
from aurex.audit.trail import AuditTrail
from aurex.core.primitives import Mode
from aurex.gateway.gateway import MCPGateway
from aurex.ipt.ipt import IPT
from aurex.orchestrator.orchestrator import Orchestrator, OrchestrationResult


@dataclass
class SandboxConfig:
    start_date: str
    end_date: str
    initial_capital: float = 100_000.0
    symbol: str = "AAPL"
    inject_news: bool = True
    seed: int = 42


@dataclass
class SandboxReport:
    config: SandboxConfig
    n_decisions: int = 0
    n_rule_violations: int = 0
    n_guideline_deviations: int = 0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_return_pct: float = 0.0
    timeline: list[dict] = field(default_factory=list)
    suggested_improvements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "config": self.config.__dict__,
            "n_decisions": self.n_decisions,
            "n_rule_violations": self.n_rule_violations,
            "n_guideline_deviations": self.n_guideline_deviations,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_return_pct": self.total_return_pct,
            "timeline": self.timeline,
            "suggested_improvements": self.suggested_improvements,
        }


def _date_range(start: str, end: str) -> list[str]:
    s = datetime.fromisoformat(start)
    e = datetime.fromisoformat(end)
    days: list[str] = []
    cur = s
    while cur <= e:
        days.append(cur.date().isoformat())
        cur += timedelta(days=1)
    return days


def replay_price(path: list[float], day_idx: int) -> float:
    return float(path[day_idx % len(path)])


def run_sandbox(
    *,
    ipt: IPT,
    orchestrator: Orchestrator,
    config: SandboxConfig,
    audit: AuditTrail,
) -> SandboxReport:
    """Replay historical period through the IPT and produce a report."""
    rng = random.Random(config.seed)
    price_path = [100 + i + rng.uniform(-2, 2) for i in range(len(_date_range(config.start_date, config.end_date)))]

    report = SandboxReport(config=config)
    equity_curve: list[float] = [config.initial_capital]
    wins = 0
    losses = 0

    for day_idx, day in enumerate(_date_range(config.start_date, config.end_date)):
        ctx = {
            "symbol": config.symbol,
            "price": replay_price(price_path, day_idx),
            "trade": {
                "symbol": config.symbol,
                "risk_pct": 0.01,
                "holding_period_days": 5,
            },
            "portfolio": {"sector_weights": {"tech": 0.25, "baseline_tech": 0.2}},
            "user_approved": True,
            "ipt_id": ipt.ipt_id,
            "mode": ipt.mode.value,
        }
        if config.inject_news and rng.random() < 0.1:
            ctx["news_spike"] = True

        # Force SANDBOX mode regardless of IPT config
        prev_mode = ipt.mode
        try:
            ipt.mode = Mode.SANDBOX
            res: OrchestrationResult = orchestrator.run(ipt, ctx)
        finally:
            ipt.mode = prev_mode

        report.n_decisions += 1
        blocked = res.gateway_response.get("status") == "BLOCKED"
        if blocked:
            report.n_rule_violations += 1

        # Toy equity update: +0.5% on ACT+EXECUTED, -0.3% on ACT+BLOCKED, 0 otherwise
        gw_status = res.gateway_response.get("status")
        if gw_status == "EXECUTED" or gw_status == "SIMULATED":
            equity_curve.append(equity_curve[-1] * 1.005)
            wins += 1
        elif gw_status == "BLOCKED":
            equity_curve.append(equity_curve[-1] * 0.997)
            losses += 1
        else:
            equity_curve.append(equity_curve[-1])

        report.timeline.append(
            {"day": day, "status": gw_status, "final_action": res.final_action, "price": ctx["price"]}
        )

    peak = max(equity_curve)
    trough = min(equity_curve)
    report.max_drawdown = (peak - trough) / peak if peak else 0.0
    report.total_return_pct = (equity_curve[-1] - config.initial_capital) / config.initial_capital * 100
    decided = wins + losses
    report.win_rate = (wins / decided) if decided else 0.0

    rets = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1]
    ]
    if rets:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / len(rets)
        std = var ** 0.5
        report.sharpe = (mean / std) * (252 ** 0.5) if std else 0.0

    if report.n_rule_violations:
        report.suggested_improvements.append(
            "Reduce rule violations by tightening rule scope or simplifying candidate actions."
        )
    if report.win_rate < 0.5:
        report.suggested_improvements.append(
            "Win rate below 50% — review guideline priorities or tighten risk caps."
        )

    audit.record(
        event_type="sandbox_run",
        ipt_id=ipt.ipt_id,
        actor="sandbox",
        payload=report.to_dict(),
    )
    return report