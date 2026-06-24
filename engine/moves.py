"""
kairon/engine/moves.py
Move recommendation engine. Ranks all opportunities by net profit.
Implements Document 07/08 allocation engine — the output of GET /api/moves.
"""
import logging
from typing import Optional

from kairon.data.market_data import ASSETS
from kairon.engine.analyzer import analyze
from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit
from kairon.config import cfg

logger = logging.getLogger("kairon.moves")

# Which assets to analyse for move recommendations
WATCHLIST = {
    "GC=F":    ("Gold",         "commodities"),
    "BTC-USD": ("Bitcoin",      "crypto"),
    "ETH-USD": ("Ethereum",     "crypto"),
    "SPY":     ("S&P 500 ETF",  "stocks"),
    "QQQ":     ("NASDAQ ETF",   "stocks"),
    "AAPL":    ("Apple",        "stocks"),
    "EURUSD=X":("EUR/USD",      "forex"),
    "TLT":     ("20Y Bonds ETF","bonds"),
    "CL=F":    ("Crude Oil",    "commodities"),
    "VNQ":     ("REIT ETF",     "real_estate"),
}


def get_move_recommendations(
    capital_usd: float = 100_000.0,
    from_market: str = "stocks",
    holding_days: int = 0,
    unrealized_gain_pct: float = 0.0,
    regime_override: Optional[str] = None,
    min_confidence: float = 0.50,
    max_results: int = 5,
) -> dict:
    """
    Analyse all watchlist assets and return ranked recommendations.
    Only assets with positive net profit after all costs are included.
    """
    per_position = capital_usd * cfg.max_position_pct
    candidates = []

    for ticker, (name, market) in WATCHLIST.items():
        try:
            pred = analyze(
                ticker=ticker,
                market=market,
                capital_usd=per_position,
                from_market=from_market,
                holding_days=holding_days,
                unrealized_gain_pct=unrealized_gain_pct,
                regime_override=regime_override,
            )

            if pred["confidence"] < min_confidence:
                continue
            if pred["decision"] not in ("BUY", "HOLD"):
                continue
            if not pred["position"]["viable"]:
                continue

            net = pred["net_profit_projected"]
            if net <= 0:
                continue

            candidates.append({
                "rank":            0,
                "prediction_id":   pred["prediction_id"],
                "asset":           name,
                "ticker":          ticker,
                "market":          market,
                "decision":        pred["decision"],
                "signal":          pred["signal"],
                "confidence":      pred["confidence"],
                "composite_score": pred["composite_score"],
                "force_type":      pred["force_type"],
                "horizon_days":    pred["horizon_days"],
                "entry_price":     pred["entry_price"],
                "capital_usd":     per_position,
                # Costs
                "costs":           pred["costs"],
                # Position
                "position":        pred["position"],
                "net_profit_usd":  round(net, 2),
                "net_profit_pct":  round(net / per_position * 100, 3),
                # Signals
                "agent_signals":   pred["agent_signals"],
                "debate":          pred["debate"],
                "kb_context":      pred["kb_context"],
                # Explanation
                "llm_explanation": pred["llm_explanation"],
                "key_risks":       pred["key_risks"],
                "urgency":         _urgency_label(pred["composite_score"], pred["force_type"]),
                # Data quality
                "stale_data":      pred["stale_data"],
                "macro_regime":    pred["macro_regime"],
            })
        except Exception as e:
            logger.warning(f"Failed to analyse {ticker}: {e}")

    # Sort by net profit descending
    candidates.sort(key=lambda x: x["net_profit_usd"], reverse=True)

    for i, c in enumerate(candidates[:max_results]):
        c["rank"] = i + 1

    total_net = sum(c["net_profit_usd"] for c in candidates[:max_results])
    total_cap = sum(c["capital_usd"]    for c in candidates[:max_results])

    return {
        "moves":              candidates[:max_results],
        "total_count":        len(candidates),
        "total_net_profit":   round(total_net, 2),
        "total_capital_required": round(total_cap, 2),
        "available_capital":  capital_usd,
        "generated_at":       __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


def _urgency_label(composite: float, force_type: str) -> str:
    if abs(composite) > 0.7 and force_type == "news_catalyst":
        return "IMMEDIATE"
    if abs(composite) > 0.6:
        return "SHORT"
    if force_type == "macro_shift":
        return "MEDIUM"
    return "PATIENT"
