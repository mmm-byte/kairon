"""
kairon/engine/analyzer.py
Master orchestrator: assembles data context, runs all 8 agents,
applies cost/risk engines, saves to DB, returns full prediction dict.
This is what the API calls. One function: analyze(ticker, market, capital).
"""
import uuid
import logging
import concurrent.futures
from datetime import datetime, timezone
from typing import Optional

from kairon.config import cfg
from kairon.data import market_data as mkt
from kairon.data import indicators as ind_mod
from kairon.data import macro_data as macro_mod
from kairon.data import news_fetcher as news_mod
from kairon.data import cache as cache_mod
from kairon.agents.agents import (
    TechnicalAnalyst, FundamentalAnalyst, NewsAnalyst,
    MacroAgent, CrossMarketAgent, TraderAgent, run_bull_bear_debate,
)
from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit
from kairon.engine.risk_engine import calculate_position, PortfolioMonitor
from kairon.intelligence.knowledge_base import KnowledgeBase
from kairon.intelligence.llm_explainer import generate_explanation
from kairon.intelligence.explainability import build_full_explanation
from kairon.engine.timing_engine import get_timing_recommendation
from kairon.db import database as db

logger = logging.getLogger("kairon.analyzer")

# Singleton portfolio monitor and KB
_portfolio_monitor = PortfolioMonitor(cfg.portfolio_capital)
_kb = KnowledgeBase()


def _horizon_for_force(force_type: str) -> int:
    return {"macro_shift": 10, "news_catalyst": 2, "technical_breakout": 5}.get(force_type, 5)


def analyze(
    ticker: str,
    market: str,
    capital_usd: float = 20_000.0,
    from_market: str = "stocks",
    holding_days: int = 0,
    unrealized_gain_pct: float = 0.0,
    regime_override: Optional[str] = None,
) -> dict:
    """
    Full 8-agent analysis pipeline. Returns a complete prediction dict.
    Safe to call concurrently — all state is local to this call.
    """
    pred_id   = str(uuid.uuid4())
    asset_info = mkt.ASSETS.get(ticker, {"name": ticker, "market": market})
    asset_name = asset_info["name"]

    logger.info(f"Analyzing {asset_name} ({ticker}) | capital=${capital_usd:,.0f}")

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    price_data  = mkt.fetch_ohlcv(ticker, period="1y")
    ohlcv_df    = price_data.get("df")
    indicators  = ind_mod.compute_all(ohlcv_df, market_type=market)
    macro_snap  = macro_mod.get_macro_snapshot()
    news_signal = news_mod.get_news_signal(asset_name)

    if regime_override:
        regime = {"regime": regime_override, "confidence": 0.80,
                  "reasoning": "Manual override by user",
                  "favorable_markets": [], "unfavorable_markets": []}
    else:
        regime = macro_mod.classify_regime(macro_snap)

    current_price = indicators.get("close") or 1.0
    vix           = macro_snap.get("vix") or 14.2

    # ── 2. KB context ─────────────────────────────────────────────────────────
    kb_context = _kb.find_similar(
        asset=asset_name, market=market,
        rsi=indicators.get("rsi"),
        macro_regime=regime["regime"],
        vix=vix,
        gdelt_tone=news_signal.get("gdelt_tone_72h", 0.0),
    )

    # ── 3. Pre-cost estimate for agents ──────────────────────────────────────
    rough_costs = calculate_all_costs(
        amount_usd=capital_usd,
        from_market=from_market,
        to_market=market,
        to_asset=ticker,
        holding_days=holding_days,
        unrealized_gain_pct=unrealized_gain_pct,
        vix=vix,
        tax_region=cfg.tax_region,
    )

    # ── 4. Build shared context ───────────────────────────────────────────────
    ctx = {
        "ticker":      ticker,
        "asset":       asset_name,
        "market":      market,
        "indicators":  indicators,
        "macro":       macro_snap,
        "news_signal": news_signal,
        "ohlcv_df":    ohlcv_df,
        "regime":      regime,
        "kb_context":  kb_context,
        "capital_usd": capital_usd,
        "costs":       rough_costs.to_dict(),
        "vix":         vix,
    }

    # ── 5. Run first 5 agents (can run in parallel) ───────────────────────────
    analyst_agents = [
        TechnicalAnalyst(),
        FundamentalAnalyst(),
        NewsAnalyst(),
        MacroAgent(),
        CrossMarketAgent(),
    ]
    agent_signals: dict[str, dict] = {}

    # Sequential for now (parallel needs asyncio or threads — safe to parallelise later)
    for agent in analyst_agents:
        sig = agent.run(ctx)
        agent_signals[sig.agent_name] = sig.to_dict()

    # ── 6. Bull/Bear debate ───────────────────────────────────────────────────
    ctx["analyst_signals"] = agent_signals
    debate = run_bull_bear_debate(ctx)
    ctx["debate"] = debate

    # ── 7. Trader decision ────────────────────────────────────────────────────
    trader_sig = TraderAgent().run(ctx)
    decision_raw = trader_sig.raw_data.get("decision", "HOLD")
    force_type   = trader_sig.raw_data.get("force_type", "technical_breakout")
    composite    = trader_sig.signal
    confidence   = trader_sig.confidence

    # ── 8. Final cost calculation ─────────────────────────────────────────────
    expected_return_pct = abs(composite) * 0.03   # 3% gross per signal unit (calibrated)
    costs = calculate_all_costs(
        amount_usd=capital_usd,
        from_market=from_market,
        to_market=market,
        to_asset=ticker,
        holding_days=holding_days,
        unrealized_gain_pct=unrealized_gain_pct,
        vix=vix,
        tax_region=cfg.tax_region,
    )

    passes, profit_reason = passes_minimum_profit(expected_return_pct, costs)
    if not passes:
        decision_raw = "HOLD"

    # ── 9. Position sizing ────────────────────────────────────────────────────
    horizon_days = _horizon_for_force(force_type)
    atr_pct = indicators.get("atr_pct") or 0.015
    position = calculate_position(
        win_probability=confidence,
        expected_return=expected_return_pct,
        market=market,
        atr_pct=atr_pct,
        current_price=current_price,
        available_capital=_portfolio_monitor.current_capital,
        current_drawdown=_portfolio_monitor.current_drawdown,
        total_cost_pct=costs.total_cost_pct,
    )

    # ── 10. Timing recommendation ─────────────────────────────────────────────
    timing = get_timing_recommendation(
        composite_score=composite,
        force_type=force_type,
        market=market,
        ticker=ticker,
        horizon_days=horizon_days,
        vix=vix,
    )

    # ── 10b. Full explainability chain ────────────────────────────────────────
    explainability = build_full_explanation(
        asset=asset_name, market=market, ticker=ticker,
        decision=decision_raw, composite=composite,
        confidence=confidence,
        indicators=indicators, macro=macro_snap,
        news=news_signal, agent_signals=agent_signals,
        kb_context=kb_context, costs=costs.to_dict(),
        horizon_days=horizon_days,
    )

    # ── 11. LLM explanation ────────────────────────────────────────────────────
    llm_explanation = generate_explanation(
        asset=asset_name, market=market,
        decision=decision_raw, composite=composite,
        agent_signals=agent_signals,
        regime=regime["regime"],
        costs=costs.to_dict(),
        key_risks=debate.get("key_disagreements", []),
    )

    # ── 11. Assemble full prediction ──────────────────────────────────────────
    net_profit_projected = (
        position.position_usd * expected_return_pct - costs.total_cost_usd
        if position.viable else 0.0
    )

    prediction = {
        "prediction_id":       pred_id,
        "asset":               asset_name,
        "ticker":              ticker,
        "market":              market,
        "signal":              trader_sig.direction,
        "composite_score":     round(composite, 4),
        "confidence":          round(confidence, 3),
        "decision":            decision_raw,
        "force_type":          force_type,
        "horizon_days":        horizon_days,
        "entry_price":         round(current_price, 4),
        # Agent signals
        "agent_signals":       agent_signals,
        # Debate
        "debate":              debate,
        # Macro
        "macro_regime":        regime["regime"],
        "vix":                 vix,
        "dxy":                 macro_snap.get("dxy"),
        "yield_curve":         macro_snap.get("yield_curve"),
        # Costs
        "costs":               costs.to_dict(),
        # Position
        "position":            position.to_dict(),
        "net_profit_projected": round(net_profit_projected, 2),
        # KB
        "kb_context":          kb_context,
        # LLM
        "llm_explanation":     llm_explanation,
        "key_risks":           debate.get("key_disagreements", []),
        # Timing
        "timing":              timing.to_dict(),
        # Explainability
        "explainability":      explainability,
        # Metadata
        "created_at":          datetime.now(timezone.utc).isoformat(),
        "data_source":         price_data.get("source", "unknown"),
        "stale_data":          price_data.get("stale", False),
    }

    # ── 12. Persist to DB ─────────────────────────────────────────────────────
    _save_prediction(pred_id, prediction, indicators, macro_snap, news_signal, costs)

    return prediction


def _save_prediction(pred_id: str, pred: dict, indicators: dict,
                     macro: dict, news: dict, costs) -> None:
    """Persist prediction to SQLite for KB learning."""
    try:
        import json
        row = {
            "id":               pred_id,
            "asset":            pred["asset"],
            "ticker":           pred["ticker"],
            "market":           pred["market"],
            "price":            pred["entry_price"],
            "rsi":              indicators.get("rsi"),
            "macd":             indicators.get("macd"),
            "macd_hist":        indicators.get("macd_hist"),
            "bb_position":      indicators.get("bb_pos"),
            "bb_width":         indicators.get("bb_width"),
            "volatility_20d":   indicators.get("volatility_20d"),
            "volume_ratio":     indicators.get("vol_ratio"),
            "atr_pct":          indicators.get("atr_pct"),
            "momentum_10":      indicators.get("momentum_10"),
            "z_score_20":       indicators.get("z_score_20"),
            "trend":            indicators.get("trend"),
            "macro_regime":     pred["macro_regime"],
            "vix":              macro.get("vix"),
            "dxy":              macro.get("dxy"),
            "fed_rate":         macro.get("fed_rate"),
            "real_yield_10y":   macro.get("real_yield_10y"),
            "yield_curve":      macro.get("yield_curve"),
            "gdelt_tone_72h":   news.get("gdelt_tone_72h"),
            "gdelt_mentions":   news.get("gdelt_mentions"),
            "gdelt_goldstein":  news.get("gdelt_goldstein"),
            "news_impact":      news.get("signal"),
            "n_headlines":      news.get("n_sources"),
            "sentiment_label":  news.get("sentiment_label"),
            "technical_score":  pred["agent_signals"].get("technical", {}).get("signal"),
            "fundamental_score": pred["agent_signals"].get("fundamental", {}).get("signal"),
            "news_score":       pred["agent_signals"].get("news", {}).get("signal"),
            "macro_score":      pred["agent_signals"].get("macro", {}).get("signal"),
            "cross_market_score": pred["agent_signals"].get("cross_market", {}).get("signal"),
            "bull_score":       pred["debate"].get("bull_score"),
            "bear_score":       pred["debate"].get("bear_score"),
            "bull_argument":    pred["debate"].get("bull_argument"),
            "bear_argument":    pred["debate"].get("bear_argument"),
            "trader_reasoning": pred.get("llm_explanation"),
            "key_risks":        json.dumps(pred.get("key_risks", [])),
            "llm_explanation":  pred.get("llm_explanation"),
            "signal":           pred["signal"],
            "confidence":       pred["confidence"],
            "composite_score":  pred["composite_score"],
            "horizon_days":     pred["horizon_days"],
            "force_type":       pred["force_type"],
            "capital_usd":      pred["position"].get("position_usd"),
            "broker_cost":      costs.broker_cost,
            "spread_cost":      costs.spread_cost,
            "slippage_cost":    costs.slippage_cost,
            "fx_cost":          costs.fx_conversion_cost,
            "gas_cost":         costs.crypto_gas_cost,
            "wire_cost":        costs.wire_cost,
            "tax_cost":         costs.tax_cost,
            "total_cost_usd":   costs.total_cost_usd,
            "net_profit_projected": pred["net_profit_projected"],
            "position_usd":     pred["position"].get("position_usd"),
            "position_pct":     pred["position"].get("position_pct"),
            "stop_loss_pct":    pred["position"].get("stop_loss_pct"),
            "stop_loss_price":  pred["position"].get("stop_loss_price"),
            "take_profit_pct":  pred["position"].get("take_profit_pct"),
            "risk_reward_ratio": pred["position"].get("risk_reward_ratio"),
        }
        db.insert("predictions", row)
        logger.debug(f"Saved prediction {pred_id}")
    except Exception as e:
        logger.error(f"Failed to save prediction: {e}")


def log_user_decision(prediction_id: str, decision: str, notes: str = "",
                       capital_deployed: float = 0.0) -> bool:
    """Log execute/pass decision to the knowledge base."""
    try:
        from datetime import datetime, timezone
        db.execute(
            """UPDATE predictions SET
               user_decision=?, user_decision_at=?, user_notes=?, user_capital_deployed=?
               WHERE id=?""",
            (decision, datetime.now(timezone.utc).isoformat(),
             notes, capital_deployed, prediction_id),
        )
        return True
    except Exception as e:
        logger.error(f"Failed to log decision: {e}")
        return False
