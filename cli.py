#!/usr/bin/env python3
"""
kairon/cli.py
Command-line interface for Kairon.
Usage:
  python -m kairon.cli analyze GC=F commodities
  python -m kairon.cli moves --capital 100000
  python -m kairon.cli backtest GC=F --folds 5
  python -m kairon.cli health
  python -m kairon.cli serve [ui|api|scheduler|all]
"""
import sys
import os
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _init():
    from kairon.db.database import init_db
    init_db()


def cmd_health(args):
    from kairon.data.source_status import source_status
    from kairon.config import cfg
    print(f"\n{'─'*50}")
    print(f"  Kairon Health Check")
    print(f"{'─'*50}")
    print(f"  LLM provider:    {cfg.llm_provider} / {cfg.llm_model}")
    print(f"  Database:        {cfg.db_path}")
    print(f"  Portfolio cap:   ${cfg.portfolio_capital:,.0f}")
    print(f"  Tax region:      {cfg.tax_region}")
    print()
    for s in source_status.all_statuses():
        dot = {"healthy": "✓", "degraded": "!", "unavailable": "✗"}.get(s["state"], "?")
        print(f"  [{dot}] {s['display_name']:<35} {s['state']}")
    print()


def cmd_analyze(args):
    from kairon.engine.analyzer import analyze
    print(f"\nAnalysing {args.ticker} / {args.market}...")
    result = analyze(
        ticker=args.ticker,
        market=args.market,
        capital_usd=args.capital,
        regime_override=args.regime,
    )
    print(f"\n{'─'*50}")
    print(f"  {result['asset']} ({result['ticker']}) — {result['decision']}")
    print(f"{'─'*50}")
    print(f"  Composite score: {result['composite_score']:+.3f}")
    print(f"  Confidence:      {result['confidence']*100:.1f}%")
    print(f"  Regime:          {result['macro_regime']}")
    print(f"  Force type:      {result['force_type']}")
    print()
    print("  Agent signals:")
    for ag, sig in result["agent_signals"].items():
        bar_len = int(abs(sig.get("signal", 0)) * 20)
        bar     = "█" * bar_len
        sign    = "+" if sig.get("signal", 0) >= 0 else ""
        print(f"    {ag:<18} {bar:<20} {sign}{sig.get('signal', 0):.3f}")
    print()
    print(f"  Timing:  {result['timing']['urgency']} — {result['timing']['urgency_label']}")
    print(f"  Entry:   {result['timing']['optimal_entry']}")
    if result["timing"]["event_risk"]["level"] != "none":
        print(f"  ⚠ Event risk: {result['timing']['event_risk']['message']}")
    print()
    print(f"  Costs:   ${result['costs']['total_cost_usd']:.2f} ({result['costs']['total_cost_pct']:.2f}%)")
    if result["position"]["viable"]:
        pos = result["position"]
        print(f"  Size:    ${pos['position_usd']:,.0f} ({pos['position_pct']*100:.1f}% of capital)")
        print(f"  Stop:    ${pos['stop_loss_price']:,.2f} (-{pos['stop_loss_pct']*100:.1f}%)")
    print()
    print(f"  AI:  {result['llm_explanation'][:120]}...")
    if args.json:
        print(f"\n{'─'*50}")
        print(json.dumps(result, indent=2, default=str))


def cmd_moves(args):
    from kairon.engine.moves import get_move_recommendations
    print(f"\nGenerating move recommendations (capital: ${args.capital:,.0f})...")
    result = get_move_recommendations(
        capital_usd=args.capital,
        max_results=args.top,
        regime_override=args.regime,
    )
    moves = result.get("moves", [])
    print(f"\n{'─'*50}")
    print(f"  Move Recommendations — {len(moves)} found")
    print(f"  Total net profit: ${result['total_net_profit']:,.2f}")
    print(f"{'─'*50}")
    for m in moves:
        profit_color = "\033[92m" if m["net_profit_usd"] > 0 else "\033[91m"
        reset = "\033[0m"
        print(f"  #{m['rank']} {m['asset']:<20} {m['decision']:<6}"
              f" conf={m['confidence']*100:.0f}%"
              f" net={profit_color}${m['net_profit_usd']:,.2f}{reset}"
              f" [{m.get('urgency','?')}]")
    print()


def cmd_backtest(args):
    from kairon.intelligence.backtester import walk_forward_backtest
    from kairon.data.market_data import ASSETS
    info = ASSETS.get(args.ticker, {"name": args.ticker, "market": "stocks"})
    print(f"\nRunning {args.folds}-fold walk-forward backtest: {info['name']}...")
    result = walk_forward_backtest(
        ticker=args.ticker,
        market=info["market"],
        horizon_days=args.horizon,
        n_folds=args.folds,
    )
    d = result.to_dict()
    grade_sym = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(d["grade"], "⚪")
    print(f"\n{'─'*50}")
    print(f"  Backtest Results — {info['name']}")
    print(f"{'─'*50}")
    print(f"  Grade:        {grade_sym} {d['grade']}")
    print(f"  Accuracy:     {d['accuracy']*100:.1f}% ({d['n_correct']}/{d['n_predictions']})")
    print(f"  Sharpe ratio: {d['sharpe_ratio']:.3f}")
    print(f"  Max drawdown: {d['max_drawdown']*100:.1f}%")
    print(f"  Total return: {d['total_return_pct']:+.1f}%")
    print(f"  Win rate:     {d['win_rate']*100:.1f}%")
    print()
    for f in d.get("folds", []):
        acc = f["accuracy"] * 100
        sym = "✓" if acc >= 60 else "~" if acc >= 50 else "✗"
        print(f"  Fold {f['fold']}: {sym} {acc:.1f}% accuracy | {f['n_predictions']} trades | {f.get('date_start','?')}→{f.get('date_end','?')}")
    if d.get("warnings"):
        print()
        for w in d["warnings"]:
            print(f"  ⚠ {w}")
    print()


def cmd_serve(args):
    mode = args.mode
    if mode in ("ui", "all"):
        print("Starting Streamlit UI on http://localhost:8501 ...")
        if mode == "ui":
            os.execvp("streamlit", ["streamlit", "run", "kairon/ui/app.py"])
            return
    if mode in ("api", "all"):
        print("Starting FastAPI on http://localhost:8000 ...")
        if mode == "api":
            os.execvp("uvicorn", ["uvicorn", "kairon.api.main:app", "--reload", "--port", "8000"])
            return
    if mode in ("scheduler",):
        print("Starting background scheduler ...")
        from kairon.data.scheduler import start_scheduler
        import time
        sched = start_scheduler()
        if sched:
            try:
                while True:
                    time.sleep(5)
            except KeyboardInterrupt:
                sched.shutdown()
        return
    if mode == "all":
        print("Use docker-compose up to run all services together.")
        print("Or run each individually:")
        print("  streamlit run kairon/ui/app.py")
        print("  uvicorn kairon.api.main:app --reload")
        print("  python -m kairon.data.scheduler")


def main():
    parser = argparse.ArgumentParser(
        prog="kairon",
        description="Kairon Financial Intelligence System",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # health
    p_health = sub.add_parser("health", help="System health check")
    p_health.set_defaults(func=cmd_health)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyse a single asset")
    p_analyze.add_argument("ticker", help="Ticker (e.g. GC=F, BTC-USD, AAPL)")
    p_analyze.add_argument("market", nargs="?", default="stocks",
                            help="Market type (stocks/crypto/forex/commodities/bonds/real_estate)")
    p_analyze.add_argument("--capital", type=float, default=20000)
    p_analyze.add_argument("--regime",  default=None, help="Override regime")
    p_analyze.add_argument("--json",    action="store_true", help="Print full JSON output")
    p_analyze.set_defaults(func=cmd_analyze)

    # moves
    p_moves = sub.add_parser("moves", help="Get ranked move recommendations")
    p_moves.add_argument("--capital", type=float, default=100000)
    p_moves.add_argument("--top",     type=int,   default=5)
    p_moves.add_argument("--regime",  default=None)
    p_moves.set_defaults(func=cmd_moves)

    # backtest
    p_bt = sub.add_parser("backtest", help="Run walk-forward backtest")
    p_bt.add_argument("ticker", help="Ticker to backtest")
    p_bt.add_argument("--horizon", type=int, default=5,  help="Signal horizon days")
    p_bt.add_argument("--folds",   type=int, default=5,  help="Number of folds")
    p_bt.set_defaults(func=cmd_backtest)

    # serve
    p_serve = sub.add_parser("serve", help="Start Kairon services")
    p_serve.add_argument("mode", choices=["ui","api","scheduler","all"], default="ui", nargs="?")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    _init()
    args.func(args)


if __name__ == "__main__":
    main()
