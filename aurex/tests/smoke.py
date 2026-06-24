"""Smoke tests — exercise every Aurex layer end-to-end."""
from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from aurex.agents.agent import LLMRunner
from aurex.audit.trail import AuditTrail
from aurex.core.platform_rules import PLATFORM_IMMUTABLE_RULES
from aurex.core.primitives import Mode
from aurex.gateway.gateway import MCPGateway
from aurex.ipt.ipt import IPT, load_ipt
from aurex.orchestrator.orchestrator import Orchestrator
from aurex.rules.dsl import evaluate
from aurex.rules.engine import evaluate_rules
from aurex.sandbox.engine import SandboxConfig, run_sandbox


IPT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "IPT-01"


def _ipt(tmp: Path) -> IPT:
    dest = tmp / "IPT-01"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(IPT_FIXTURE, dest)
    return load_ipt(dest)


def test_dsl_evaluator():
    assert evaluate({"EQ": [{"FIELD": "x"}, 1]}, {"x": 1}) is True
    assert evaluate({"LTE": [{"FIELD": "trade.risk_pct"}, 0.02]}, {"trade": {"risk_pct": 0.01}}) is True
    assert evaluate({"AND": [{"EQ": [{"FIELD": "a"}, 1]}, {"EQ": [{"FIELD": "b"}, 2]}]}, {"a": 1, "b": 3}) is False
    assert evaluate({"IMPLIES": [{"EQ": [{"FIELD": "p"}, 1]}, {"EQ": [{"FIELD": "q"}, 2]}]}, {"p": 2, "q": 2}) is True
    print("✓ dsl")


def test_platform_immutable_rules_present():
    ids = {r.id for r in PLATFORM_IMMUTABLE_RULES}
    assert "PLAT_NO_REAL_MONEY_IN_SANDBOX" in ids
    assert "PLAT_DENY_BY_DEFAULT" in ids
    assert all(r.immutable for r in PLATFORM_IMMUTABLE_RULES)
    print("✓ platform rules")


def test_ipt_loads_with_rules_and_guidelines(tmp: Path):
    ipt = _ipt(tmp)
    assert ipt.ipt_id == "IPT-01"
    assert ipt.mode == Mode.SANDBOX
    assert any(r.id == "RISK_MAX_PER_TRADE" for r in ipt.rule_store.rules)
    assert any(g.id == "PREF_TECH_TILT" for g in ipt.rule_store.guidelines)
    print("✓ ipt load")


def test_rule_engine_blocks_oversized_trade(tmp: Path):
    ipt = _ipt(tmp)
    ctx = {"trade": {"symbol": "AAPL", "risk_pct": 0.10}, "ipt_id": ipt.ipt_id, "mode": "SANDBOX"}
    evals = evaluate_rules(ipt.rule_store.rules, ctx)
    risk = next(e for e in evals if e.rule_id == "RISK_MAX_PER_TRADE")
    assert risk.complies is False
    print("✓ rule engine blocks oversized trade")


def test_rule_engine_blocks_leveraged_etf(tmp: Path):
    ipt = _ipt(tmp)
    ctx = {"trade": {"symbol": "TQQQ", "risk_pct": 0.01}, "ipt_id": ipt.ipt_id, "mode": "SANDBOX"}
    evals = evaluate_rules(ipt.rule_store.rules, ctx)
    lev = next(e for e in evals if e.rule_id == "NO_LEVERAGED_ETF")
    assert lev.complies is False
    print("✓ rule engine blocks leveraged ETF")


def test_gateway_blocks_real_money_in_sandbox(tmp: Path):
    ipt = _ipt(tmp)
    audit = AuditTrail(tmp / "audit.jsonl")
    gw = MCPGateway(audit)
    from aurex.core.primitives import GatewayRequest

    # Force an endpoint config that *claims* a real broker exists
    ipt.endpoints["BROKER"] = {
        "sandbox": "aurex.mcp.simulated.SimulatedBrokerMCP",
        "live": "aurex.mcp.simulated.SimulatedBrokerMCP",  # pretend there's a real one
    }

    # 1) In SANDBOX, the call must NOT execute live
    req = GatewayRequest(
        ipt_id=ipt.ipt_id,
        agent_name="TraderAgent",
        mode=Mode.SANDBOX,
        action={"tool": "place_order", "endpoint_group": "BROKER", "params": {"symbol": "AAPL", "qty": 1}},
        context={"trade": {"symbol": "AAPL", "risk_pct": 0.01}, "user_approved": True},
    )
    resp = gw.call(req, ipt)
    assert resp.status.value == "SIMULATED", f"expected SIMULATED in SANDBOX, got {resp.status.value}"

    # 2) In SANDBOX, asking for an explicitly live endpoint key (without an "sandbox" key)
    #    must be blocked or errored.
    ipt.endpoints["BROKER"] = {"live": "aurex.mcp.simulated.SimulatedBrokerMCP"}
    resp2 = gw.call(req, ipt)
    assert resp2.status.value in ("BLOCKED", "ERROR"), f"expected BLOCKED/ERROR, got {resp2.status.value}"
    print("✓ gateway routes sandbox safely")


def test_platform_rule_no_real_money_in_sandbox():
    """Even a tampered IPT cannot make a real-money call while mode=SANDBOX."""
    from aurex.core.primitives import Mode
    from aurex.ipt.ipt import IPT
    ipt = IPT(ipt_id="IPT-99", name="tampered", mode=Mode.SANDBOX)
    ipt.endpoints = {"BROKER": {"live": "aurex.mcp.simulated.SimulatedBrokerMCP"}}
    audit = AuditTrail(Path(tempfile.gettempdir()) / "tampered-audit.jsonl")
    gw = MCPGateway(audit)
    from aurex.core.primitives import GatewayRequest
    req = GatewayRequest(
        ipt_id="IPT-99",
        agent_name="TraderAgent",
        mode=Mode.SANDBOX,
        context={"trade": {"symbol": "AAPL", "risk_pct": 0.01}, "user_approved": True},
        action={"tool": "place_order", "endpoint_group": "BROKER", "params": {"symbol": "AAPL", "qty": 1}},
    )
    resp = gw.call(req, ipt)
    assert resp.status.value in ("BLOCKED", "ERROR"), f"platform rule should block, got {resp.status.value}"
    print("✓ platform rule blocks real-money in sandbox")


def test_orchestrator_runs_full_pipeline(tmp: Path):
    ipt = _ipt(tmp)
    audit = AuditTrail(tmp / "audit.jsonl")
    gw = MCPGateway(audit)
    orch = Orchestrator(audit=audit, gateway=gw)

    from aurex.agents.agent import LLMRunner
    # Force a TraderAgent ACT via a custom LLM runner
    def fake_llm(system, payload):
        if "TraderAgent" in system or "noop" in str(payload):
            return json.dumps({
                "allowed_action_space_reasoning": "fake",
                "candidate_action": {"tool": "place_order", "endpoint_group": "BROKER",
                                     "params": {"symbol": "AAPL", "qty": 1}},
                "rule_check_self_assessment": {"complies": True, "violated_rules": []},
                "guideline_alignment": {},
                "final_decision": {"type": "ACT", "reason": "fake"},
            })
        return json.dumps({
            "allowed_action_space_reasoning": "ok",
            "candidate_action": {"tool": "noop"},
            "rule_check_self_assessment": {"complies": True, "violated_rules": []},
            "guideline_alignment": {},
            "final_decision": {"type": "ACT", "reason": "vote yes"},
        })

    from aurex.agents.builtins import BUILTIN_AGENTS
    def factory(name, ipt_):
        return BUILTIN_AGENTS[name](ipt_, LLMRunner(fake_llm))

    orch = Orchestrator(audit=audit, gateway=gw, agent_factory=factory)
    ctx = {
        "symbol": "AAPL", "trade": {"symbol": "AAPL", "risk_pct": 0.01, "holding_period_days": 5},
        "portfolio": {"sector_weights": {"tech": 0.3, "baseline_tech": 0.2}},
        "user_approved": True, "ipt_id": ipt.ipt_id, "mode": ipt.mode.value,
    }
    res = orch.run(ipt, ctx)
    assert res.gateway_response["status"] in ("SIMULATED", "EXECUTED")
    assert any(e.event_type == "agent_decision" for e in audit.read_all())
    print("✓ orchestrator pipeline")


def test_sandbox_runs_replay(tmp: Path):
    ipt = _ipt(tmp)
    audit = AuditTrail(tmp / "audit.jsonl")
    gw = MCPGateway(audit)
    orch = Orchestrator(audit=audit, gateway=gw)
    start = (datetime.now() - timedelta(days=10)).date().isoformat()
    end = datetime.now().date().isoformat()
    report = run_sandbox(
        ipt=ipt,
        orchestrator=orch,
        config=SandboxConfig(start_date=start, end_date=end, initial_capital=100_000, symbol="AAPL"),
        audit=audit,
    )
    assert report.n_decisions >= 5
    assert "sharpe" in report.to_dict()
    print("✓ sandbox replay")


def test_audit_trail_round_trip(tmp: Path):
    audit = AuditTrail(tmp / "audit.jsonl")
    audit.record(event_type="test", ipt_id="IPT-01", actor="me", payload={"x": 1})
    events = audit.read_all()
    assert len(events) == 1
    assert events[0].payload == {"x": 1}
    assert "event_id" in events[0].to_json()
    print("✓ audit trail")


def run_all() -> bool:
    import traceback
    tests = [
        ("dsl", lambda tmp: test_dsl_evaluator()),
        ("platform_rules", lambda tmp: test_platform_immutable_rules_present()),
        ("platform_no_real_money", lambda tmp: test_platform_rule_no_real_money_in_sandbox()),
        ("ipt_load", test_ipt_loads_with_rules_and_guidelines),
        ("block_oversized", test_rule_engine_blocks_oversized_trade),
        ("block_leveraged", test_rule_engine_blocks_leveraged_etf),
        ("gateway_sandbox_safe", test_gateway_blocks_real_money_in_sandbox),
        ("orchestrator", test_orchestrator_runs_full_pipeline),
        ("sandbox_replay", test_sandbox_runs_replay),
        ("audit_roundtrip", test_audit_trail_round_trip),
    ]
    for name, fn in tests:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            try:
                fn(tmp)
            except Exception as e:
                traceback.print_exc()
                print(f"\n✗ FAIL [{name}]: {type(e).__name__}: {e}")
                return False
    print("\n✅ All Aurex smoke tests passed.")
    return True
    print("\n✅ All Aurex smoke tests passed.")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all() else 1)