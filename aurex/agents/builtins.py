"""Built-in agents. Plug-and-play via the same RuleFirstAgent base."""
from __future__ import annotations

from aurex.agents.agent import LLMRunner, RuleFirstAgent


def technical_agent(ipt, llm: LLMRunner) -> RuleFirstAgent:
    return RuleFirstAgent(
        name="TechnicalAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules if ipt.rule_store else [],
        guidelines_provider=lambda: ipt.rule_store.guidelines if ipt.rule_store else [],
        action_factory=lambda ctx: {"tool": "analyze_technicals", "params": {"symbol": ctx.get("symbol")}},
    )


def fundamental_agent(ipt, llm: LLMRunner) -> RuleFirstAgent:
    return RuleFirstAgent(
        name="FundamentalAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules if ipt.rule_store else [],
        guidelines_provider=lambda: ipt.rule_store.guidelines if ipt.rule_store else [],
        action_factory=lambda ctx: {"tool": "fetch_fundamentals", "params": {"symbol": ctx.get("symbol")}},
    )


def news_agent(ipt, llm: LLMRunner) -> RuleFirstAgent:
    return RuleFirstAgent(
        name="NewsAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules if ipt.rule_store else [],
        guidelines_provider=lambda: ipt.rule_store.guidelines if ipt.rule_store else [],
        action_factory=lambda ctx: {"tool": "fetch_news", "params": {"symbol": ctx.get("symbol")}},
    )


def risk_agent(ipt, llm: LLMRunner) -> RuleFirstAgent:
    return RuleFirstAgent(
        name="RiskAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules if ipt.rule_store else [],
        guidelines_provider=lambda: ipt.rule_store.guidelines if ipt.rule_store else [],
        action_factory=lambda ctx: {"tool": "size_position", "params": {"symbol": ctx.get("symbol"), "risk_pct": 0.01}},
    )


def trader_agent(ipt, llm: LLMRunner) -> RuleFirstAgent:
    return RuleFirstAgent(
        name="TraderAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules if ipt.rule_store else [],
        guidelines_provider=lambda: ipt.rule_store.guidelines if ipt.rule_store else [],
        action_factory=lambda ctx: {"tool": "place_order", "params": {"symbol": ctx.get("symbol")}},
    )


BUILTIN_AGENTS = {
    "TechnicalAgent": technical_agent,
    "FundamentalAgent": fundamental_agent,
    "NewsAgent": news_agent,
    "RiskAgent": risk_agent,
    "TraderAgent": trader_agent,
}