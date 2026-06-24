"""Aurex CLI — manage IPTs, run sandbox, view audit log."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def cmd_load_ipt(args):
    from aurex.audit.trail import AuditTrail
    from aurex.gateway.gateway import MCPGateway
    from aurex.ipt.ipt import load_ipt

    ipt = load_ipt(Path(args.ipt_root))
    ipt.start_hot_reload()
    print(f"Loaded {ipt.ipt_id} (mode={ipt.mode.value}, rules={len(ipt.rule_store.rules)}, guidelines={len(ipt.rule_store.guidelines)})")
    audit = AuditTrail(args.audit)
    audit.record(event_type="ipt_loaded", ipt_id=ipt.ipt_id, actor="cli", payload={"root": str(args.ipt_root)})
    return ipt, audit


def cmd_sandbox(args):
    from datetime import datetime, timedelta
    from aurex.audit.trail import AuditTrail
    from aurex.gateway.gateway import MCPGateway
    from aurex.ipt.ipt import load_ipt
    from aurex.orchestrator.orchestrator import Orchestrator
    from aurex.sandbox.engine import SandboxConfig, run_sandbox

    ipt = load_ipt(Path(args.ipt_root))
    audit = AuditTrail(args.audit)
    gw = MCPGateway(audit)
    orch = Orchestrator(audit=audit, gateway=gw)
    end = datetime.now().date().isoformat()
    start = (datetime.now() - timedelta(days=args.days)).date().isoformat()
    report = run_sandbox(
        ipt=ipt,
        orchestrator=orch,
        config=SandboxConfig(start_date=start, end_date=end, initial_capital=args.capital, symbol=args.symbol),
        audit=audit,
    )
    print(json.dumps(report.to_dict(), indent=2, default=str))


def cmd_audit(args):
    from aurex.audit.trail import AuditTrail
    audit = AuditTrail(args.audit)
    if args.format == "csv":
        print(audit.export_csv())
    else:
        print(json.dumps(audit.export_json(), indent=2))


def cmd_test(args):
    from aurex.tests.smoke import run_all
    sys.exit(0 if run_all() else 1)


def main():
    p = argparse.ArgumentParser(prog="aurex", description="Aurex Agent Governance Platform")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("load-ipt", help="Load and validate an IPT")
    p1.add_argument("ipt_root")
    p1.add_argument("--audit", default="aurex-audit.jsonl")
    p1.set_defaults(func=cmd_load_ipt)

    p2 = sub.add_parser("sandbox", help="Run a sandbox replay")
    p2.add_argument("ipt_root")
    p2.add_argument("--days", type=int, default=10)
    p2.add_argument("--capital", type=float, default=100_000)
    p2.add_argument("--symbol", default="AAPL")
    p2.add_argument("--audit", default="aurex-audit.jsonl")
    p2.set_defaults(func=cmd_sandbox)

    p3 = sub.add_parser("audit", help="View audit log")
    p3.add_argument("--audit", default="aurex-audit.jsonl")
    p3.add_argument("--format", choices=["json", "csv"], default="json")
    p3.set_defaults(func=cmd_audit)

    p4 = sub.add_parser("test", help="Run smoke tests")
    p4.set_defaults(func=cmd_test)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()