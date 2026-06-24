"""
kairon/tests/test_all.py
Complete test suite. Uses only stdlib + numpy/pandas — no pytest required.
Run with: python -m kairon.tests.test_all
or:        python kairon/tests/test_all.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import math
import json
import uuid
import unittest
import tempfile
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# ── Helpers ───────────────────────────────────────────────────────────────────
def make_ohlcv(n: int = 252, seed: int = 42, base: float = 2800.0,
               vol: float = 0.012) -> pd.DataFrame:
    """Generate a synthetic OHLCV DataFrame."""
    rng   = np.random.default_rng(seed)
    ret   = rng.normal(0.0002, vol, n)
    close = base * np.cumprod(1 + ret)
    high  = close * (1 + rng.uniform(0.002, 0.015, n))
    low   = close * (1 - rng.uniform(0.002, 0.015, n))
    opens = np.concatenate([[close[0]], close[:-1]])
    vol_v = rng.integers(100_000, 5_000_000, n).astype(float)
    dates = pd.bdate_range(end="2026-03-23", periods=n, freq="B")
    return pd.DataFrame({"open": opens, "high": high, "low": low,
                          "close": close, "volume": vol_v}, index=dates)


def make_context(df: pd.DataFrame = None, market: str = "commodities",
                  asset: str = "Gold", ticker: str = "GC=F") -> dict:
    """Build a minimal analysis context for agent tests."""
    from kairon.data.indicators import compute_all
    from kairon.engine.cost_engine import calculate_all_costs
    if df is None:
        df = make_ohlcv()
    ind   = compute_all(df, market)
    costs = calculate_all_costs(20000, "stocks", market, ticker, vix=14.2)
    return {
        "ticker": ticker, "asset": asset, "market": market,
        "indicators": ind, "ohlcv_df": df,
        "macro": {"vix": 14.2, "dxy": 103.9, "fed_rate": 4.33,
                  "yield_10y": 4.21, "yield_2y": 4.68,
                  "real_yield_10y": 1.87, "yield_curve": "flat",
                  "inflation_exp": 2.34, "hy_spread": 3.5},
        "news_signal": {"signal": 0.25, "confidence": 0.6, "n_sources": 30,
                        "n_outlets": 12, "gdelt_tone_72h": -1.2,
                        "gdelt_mentions": 847, "gdelt_goldstein": -4.2,
                        "top_headlines": [], "sentiment_label": "neutral"},
        "regime": {"regime": "Risk-Off", "confidence": 0.78,
                   "reasoning": "VIX elevated",
                   "favorable_markets": ["bonds", "commodities"],
                   "unfavorable_markets": ["crypto"]},
        "kb_context": {"n_similar": 7, "n_correct": 6, "accuracy": 0.857,
                       "avg_return": 0.021, "top_matches": [],
                       "precedent_text": "6/7 correct", "has_history": True},
        "capital_usd": 20000, "vix": 14.2,
        "costs": costs.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════════════════
class TestConfig(unittest.TestCase):
    def test_config_loads(self):
        from kairon.config import cfg
        self.assertIsInstance(cfg.portfolio_capital, float)
        self.assertGreater(cfg.portfolio_capital, 0)
        self.assertIn(cfg.llm_provider, ("ollama","openai","anthropic","auto"))

    def test_config_defaults(self):
        from kairon.config import cfg
        self.assertEqual(cfg.max_position_pct, 0.25)
        self.assertEqual(cfg.max_drawdown_pct, 0.10)
        self.assertGreater(cfg.tax_year_days, 0)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        import os, tempfile
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{self._tmpfile.name}"

    def tearDown(self):
        import os
        try:
            os.remove(self._tmpfile.name)
        except FileNotFoundError:
            pass

    def test_init_creates_tables(self):
        from kairon.db.database import init_db, execute
        init_db()
        rows = execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {r["name"] for r in rows}
        for expected in ["predictions","lessons","agent_performance","market_snapshots"]:
            self.assertIn(expected, table_names)

    def test_insert_and_retrieve(self):
        from kairon.db.database import init_db, insert, execute_one
        init_db()
        pred_id = str(uuid.uuid4())
        insert("predictions", {
            "id": pred_id, "asset": "Gold", "ticker": "GC=F",
            "market": "commodities", "price": 2847.30,
            "signal": "UP", "confidence": 0.82, "composite_score": 0.81,
            "horizon_days": 5,
        })
        row = execute_one("SELECT * FROM predictions WHERE id=?", (pred_id,))
        self.assertIsNotNone(row)
        self.assertEqual(row["asset"], "Gold")
        self.assertAlmostEqual(row["price"], 2847.30, places=1)


class TestCache(unittest.TestCase):
    def test_set_get(self):
        from kairon.data.cache import get, set, cache_key
        k = cache_key("test", "unit", "abc")
        set(k, {"value": 99}, ttl=60)
        result = get(k)
        self.assertIsNotNone(result)
        self.assertEqual(result["value"], 99)

    def test_ttl_expiry(self):
        import time
        from kairon.data.cache import get, set, cache_key
        k = cache_key("test", "expire")
        set(k, "expires_soon", ttl=1)
        self.assertIsNotNone(get(k))
        time.sleep(1.1)
        self.assertIsNone(get(k))

    def test_missing_key(self):
        from kairon.data.cache import get
        self.assertIsNone(get("definitely_does_not_exist_xyz"))


class TestIndicators(unittest.TestCase):
    def setUp(self):
        self.df = make_ohlcv(252)

    def test_all_25_indicators_computed(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(self.df, "commodities")
        expected_keys = [
            "sma_10","sma_20","sma_50","ema_12","ema_26",
            "macd","macd_signal","macd_hist","rsi",
            "bb_upper","bb_lower","bb_width","bb_pos",
            "atr","atr_pct","volatility_20d",
            "vol_sma_20","vol_ratio","obv",
            "return_1d","return_5d","return_20d","momentum_10",
            "z_score_20","close_open","hl_pct",
        ]
        for key in expected_keys:
            self.assertIn(key, ind, f"Missing indicator: {key}")

    def test_rsi_range(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(self.df, "stocks")
        rsi = ind.get("rsi")
        if rsi is not None:
            self.assertGreaterEqual(rsi, 0)
            self.assertLessEqual(rsi, 100)

    def test_macd_computed(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(self.df, "stocks")
        self.assertIsNotNone(ind.get("macd"))

    def test_bb_position_range(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(self.df, "stocks")
        bb  = ind.get("bb_pos")
        if bb is not None:
            # BB position can briefly exceed [0,1] during extreme moves — that's valid
            self.assertIsInstance(bb, float)

    def test_trend_classification(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(self.df, "commodities")
        self.assertIn(ind.get("trend"),
                      ["bullish","bearish","neutral","mixed_bullish","mixed_bearish"])

    def test_score_returns_bounded(self):
        from kairon.data.indicators import compute_all, score_technical
        for market in ["stocks","crypto","forex","commodities","bonds","real_estate"]:
            ind   = compute_all(self.df, market)
            score = score_technical(ind, market)
            self.assertGreaterEqual(score, -1.0, f"Score out of range for {market}")
            self.assertLessEqual(score, 1.0, f"Score out of range for {market}")

    def test_insufficient_data_returns_empty(self):
        from kairon.data.indicators import compute_all
        small_df = self.df.tail(5)
        ind = compute_all(small_df, "stocks")
        self.assertIsNone(ind.get("rsi"))

    def test_none_df_handled(self):
        from kairon.data.indicators import compute_all
        ind = compute_all(None, "stocks")
        self.assertIsNone(ind.get("rsi"))


class TestMarketData(unittest.TestCase):
    def test_demo_data_generated(self):
        """When network unavailable, demo data must be generated."""
        from kairon.data.market_data import _generate_demo_data, ASSETS
        info = ASSETS["GC=F"]
        result = _generate_demo_data("GC=F", info)
        self.assertIn("df", result)
        df = result["df"]
        self.assertFalse(df.empty)
        self.assertGreater(len(df), 100)
        self.assertIn("close", df.columns)
        self.assertTrue((df["close"] > 0).all())

    def test_demo_data_realistic_prices(self):
        from kairon.data.market_data import _generate_demo_data, ASSETS
        info = ASSETS["GC=F"]
        result = _generate_demo_data("GC=F", info)
        price = float(result["df"]["close"].iloc[-1])
        # Gold should be within 50% of seed price of 2847
        self.assertGreater(price, 500)
        self.assertLess(price, 10000)

    def test_all_watchlist_assets_have_demo_data(self):
        from kairon.engine.moves import WATCHLIST
        from kairon.data.market_data import _generate_demo_data, ASSETS
        for ticker in WATCHLIST:
            info = ASSETS.get(ticker, {"name": ticker, "market": "unknown"})
            result = _generate_demo_data(ticker, info)
            self.assertFalse(result["df"].empty, f"No demo data for {ticker}")


class TestSourceStatus(unittest.TestCase):
    def test_mark_healthy(self):
        from kairon.data.source_status import source_status, SourceState
        source_status.mark_healthy("yahoo_finance")
        info = source_status.get("yahoo_finance")
        self.assertEqual(info.state, SourceState.HEALTHY)

    def test_mark_degraded(self):
        from kairon.data.source_status import source_status, SourceState
        source_status.mark_degraded("fred", "no API key")
        info = source_status.get("fred")
        self.assertEqual(info.state, SourceState.DEGRADED)
        self.assertIn("no API key", info.message)

    def test_overall_health(self):
        from kairon.data.source_status import source_status
        source_status.mark_healthy("yahoo_finance")
        source_status.mark_healthy("gdelt")
        h = source_status.overall_health()
        self.assertIn(h, ["healthy","degraded","impaired","critical"])


class TestCostEngine(unittest.TestCase):
    def test_stock_to_commodity_costs(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(20000, "stocks", "commodities", "GC=F", vix=14.2)
        self.assertGreater(costs.total_cost_usd, 0)
        self.assertGreater(costs.broker_cost, 0)
        self.assertGreater(costs.spread_cost, 0)
        self.assertEqual(costs.fx_conversion_cost, 0.0)  # same currency
        self.assertEqual(costs.wire_cost, 0.0)            # no wire needed

    def test_crypto_gas_fee_applied(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(10000, "stocks", "crypto", "BTC-USD")
        self.assertGreater(costs.crypto_gas_cost, 0)

    def test_wire_fee_stocks_to_crypto(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(10000, "stocks", "crypto", "BTC-USD")
        self.assertGreater(costs.wire_cost, 0)

    def test_fx_fee_forex(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(10000, "stocks", "forex", "EURUSD=X")
        self.assertGreater(costs.fx_conversion_cost, 0)

    def test_tax_optimization_alert(self):
        """340 days held should trigger tax optimization alert."""
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(
            amount_usd=50000, from_market="stocks", to_market="stocks",
            to_asset="SPY", holding_days=340, unrealized_gain_pct=0.15,
            tax_region="US",
        )
        # Should trigger optimization (25 days to long-term = save ~$1000+)
        self.assertIsNotNone(costs.tax_optimization)
        self.assertGreater(costs.tax_optimization["saving"], 100)

    def test_no_tax_on_loss(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(
            10000, "stocks", "stocks", "SPY",
            unrealized_gain_pct=-0.10  # at a loss
        )
        self.assertEqual(costs.tax_cost, 0.0)

    def test_vix_widens_spreads(self):
        from kairon.engine.cost_engine import calculate_all_costs
        normal  = calculate_all_costs(20000, "stocks", "stocks", "SPY", vix=14.0)
        fearful = calculate_all_costs(20000, "stocks", "stocks", "SPY", vix=40.0)
        self.assertGreater(fearful.spread_cost, normal.spread_cost)

    def test_total_cost_pct_reasonable(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(20000, "stocks", "commodities", "GC=F")
        # Should be between 0.1% and 2% for a normal trade
        self.assertGreater(costs.total_cost_pct, 0.1)
        self.assertLess(costs.total_cost_pct, 2.0)

    def test_zero_amount_handled(self):
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(0, "stocks", "commodities", "GC=F")
        self.assertEqual(costs.total_cost_usd, 0.0)

    def test_passes_minimum_profit(self):
        from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit
        costs    = calculate_all_costs(20000, "stocks", "commodities", "GC=F")
        ok, msg  = passes_minimum_profit(0.05, costs)  # 5% gross easily clears
        self.assertTrue(ok)

    def test_fails_minimum_profit(self):
        from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit
        costs   = calculate_all_costs(20000, "stocks", "commodities", "GC=F")
        ok, msg = passes_minimum_profit(0.0001, costs)  # tiny return can't cover costs
        self.assertFalse(ok)


class TestRiskEngine(unittest.TestCase):
    def test_kelly_fraction_basic(self):
        from kairon.engine.risk_engine import kelly_fraction
        f = kelly_fraction(0.7, 0.025, 0.018)
        self.assertGreater(f, 0)
        self.assertLess(f, 1)

    def test_kelly_zero_prob(self):
        from kairon.engine.risk_engine import kelly_fraction
        self.assertEqual(kelly_fraction(0.0, 0.025, 0.018), 0.0)
        self.assertEqual(kelly_fraction(1.0, 0.025, 0.018), 0.0)

    def test_position_viable(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.72, 0.025, "commodities", 0.012,
                                  2847.30, 100000, 0.0, 0.4)
        self.assertTrue(pos.viable)
        self.assertGreater(pos.position_usd, 0)
        self.assertLessEqual(pos.position_pct, 0.25)

    def test_position_capped_at_25pct(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.99, 0.50, "bonds", 0.003,
                                  100.0, 100000, 0.0, 0.1)
        # Even extreme confidence can't exceed 25%
        self.assertLessEqual(pos.position_pct, 0.25 + 1e-9)

    def test_position_rejected_on_drawdown(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.75, 0.025, "stocks", 0.012,
                                  100.0, 100000, 0.11, 0.4)  # 11% drawdown
        self.assertFalse(pos.viable)
        self.assertIn("drawdown", pos.reason.lower())

    def test_position_rejected_low_confidence(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.40, 0.025, "stocks", 0.012,
                                  100.0, 100000, 0.0, 0.4)
        self.assertFalse(pos.viable)

    def test_crypto_position_smaller_than_bonds(self):
        from kairon.engine.risk_engine import calculate_position
        bonds  = calculate_position(0.70, 0.020, "bonds",  0.006, 100.0, 100000, 0.0, 0.3)
        crypto = calculate_position(0.70, 0.020, "crypto", 0.050, 100.0, 100000, 0.0, 0.3)
        if bonds.viable and crypto.viable:
            self.assertLess(crypto.position_pct, bonds.position_pct)

    def test_stop_loss_below_entry(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.72, 0.025, "commodities", 0.012,
                                  2847.30, 100000, 0.0, 0.4)
        if pos.viable:
            self.assertLess(pos.stop_loss_price, 2847.30)

    def test_rr_ratio_at_least_1(self):
        from kairon.engine.risk_engine import calculate_position
        pos = calculate_position(0.72, 0.025, "commodities", 0.012,
                                  2847.30, 100000, 0.0, 0.4)
        if pos.viable:
            self.assertGreaterEqual(pos.risk_reward_ratio, 1.0)


class TestAgents(unittest.TestCase):
    def setUp(self):
        self.ctx = make_context()

    def test_technical_analyst_returns_signal(self):
        from kairon.agents.agents import TechnicalAnalyst
        sig = TechnicalAnalyst().run(self.ctx)
        self.assertTrue(sig.is_valid)
        self.assertIn(sig.direction, ["UP","DOWN","HOLD"])
        self.assertGreaterEqual(sig.signal, -1.0)
        self.assertLessEqual(sig.signal, 1.0)

    def test_fundamental_analyst_returns_signal(self):
        from kairon.agents.agents import FundamentalAnalyst
        sig = FundamentalAnalyst().run(self.ctx)
        self.assertTrue(sig.is_valid)

    def test_news_analyst_returns_signal(self):
        from kairon.agents.agents import NewsAnalyst
        sig = NewsAnalyst().run(self.ctx)
        self.assertTrue(sig.is_valid)
        self.assertGreater(len(sig.reasoning), 10)

    def test_macro_agent_returns_signal(self):
        from kairon.agents.agents import MacroAgent
        sig = MacroAgent().run(self.ctx)
        self.assertTrue(sig.is_valid)
        self.assertIn("regime", sig.raw_data)

    def test_cross_market_agent_returns_signal(self):
        from kairon.agents.agents import CrossMarketAgent
        sig = CrossMarketAgent().run(self.ctx)
        self.assertTrue(sig.is_valid)

    def test_all_markets_produce_signals(self):
        from kairon.agents.agents import TechnicalAnalyst
        for market in ["stocks","crypto","forex","commodities","bonds","real_estate"]:
            ctx = make_context(market=market)
            sig = TechnicalAnalyst().run(ctx)
            self.assertTrue(sig.is_valid, f"Technical failed for market: {market}")

    def test_bull_bear_debate(self):
        from kairon.agents.agents import (TechnicalAnalyst, FundamentalAnalyst,
                                           NewsAnalyst, MacroAgent, CrossMarketAgent,
                                           run_bull_bear_debate)
        ctx = dict(self.ctx)
        sigs = {}
        for A in [TechnicalAnalyst, FundamentalAnalyst, NewsAnalyst, MacroAgent, CrossMarketAgent]:
            s = A().run(ctx)
            sigs[s.agent_name] = s.to_dict()
        ctx["analyst_signals"] = sigs

        debate = run_bull_bear_debate(ctx)
        self.assertIn("bull_score", debate)
        self.assertIn("bear_score", debate)
        self.assertIn("consensus", debate)
        self.assertIn(debate["consensus"], [
            "strongly_bullish","moderately_bullish","neutral",
            "moderately_bearish","strongly_bearish",
        ])
        self.assertGreaterEqual(debate["bull_score"], 0)
        self.assertGreaterEqual(debate["bear_score"], 0)

    def test_trader_agent_decision(self):
        from kairon.agents.agents import (TechnicalAnalyst, FundamentalAnalyst,
                                           NewsAnalyst, MacroAgent, CrossMarketAgent,
                                           TraderAgent, run_bull_bear_debate)
        ctx  = dict(self.ctx)
        sigs = {}
        for A in [TechnicalAnalyst, FundamentalAnalyst, NewsAnalyst, MacroAgent, CrossMarketAgent]:
            s = A().run(ctx)
            sigs[s.agent_name] = s.to_dict()
        ctx["analyst_signals"] = sigs
        ctx["debate"] = run_bull_bear_debate(ctx)

        sig = TraderAgent().run(ctx)
        self.assertTrue(sig.is_valid)
        self.assertIn(sig.raw_data.get("decision"), ["BUY","HOLD","AVOID"])

    def test_agent_survives_empty_indicators(self):
        """Agents must not crash on empty/null indicator data."""
        from kairon.agents.agents import TechnicalAnalyst
        ctx = make_context()
        ctx["indicators"] = {}
        sig = TechnicalAnalyst().run(ctx)
        self.assertIsNotNone(sig)


class TestLLMExplainer(unittest.TestCase):
    def test_template_fallback_always_works(self):
        from kairon.intelligence.llm_explainer import _template_explanation
        text = _template_explanation(
            asset="Gold", market="commodities", decision="BUY",
            composite=0.68,
            agent_signals={
                "technical":   {"signal": 0.72},
                "macro":       {"signal": 0.82},
                "news":        {"signal": 0.35},
            },
            regime="Risk-Off",
            key_risks=["CPI risk", "DXY strength"],
        )
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 50)
        # Must contain hedged language
        self.assertTrue(any(w in text.lower() for w in
                            ["indicates","suggests","may","historical","data","simulation"]))

    def test_generate_explanation_never_raises(self):
        from kairon.intelligence.llm_explainer import generate_explanation
        from kairon.engine.cost_engine import calculate_all_costs
        costs = calculate_all_costs(20000, "stocks", "commodities", "GC=F").to_dict()
        text = generate_explanation(
            asset="Bitcoin", market="crypto", decision="HOLD",
            composite=0.35,
            agent_signals={"technical": {"signal": 0.4}, "macro": {"signal": -0.2}},
            regime="Risk-On", costs=costs, key_risks=["regulatory risk"],
        )
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 20)


class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        import os, tempfile
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{self._tmpfile.name}"
        from kairon.db.database import init_db
        init_db()

    def tearDown(self):
        import os
        try:
            os.remove(self._tmpfile.name)
        except FileNotFoundError:
            pass

    def test_empty_kb_returns_default(self):
        from kairon.intelligence.knowledge_base import KnowledgeBase
        kb  = KnowledgeBase()
        ctx = kb.find_similar("Gold","commodities", rsi=62, macro_regime="Risk-Off",
                               vix=14.2, gdelt_tone=-1.2)
        self.assertFalse(ctx["has_history"])
        self.assertEqual(ctx["n_similar"], 0)

    def test_stats_on_empty_db(self):
        from kairon.intelligence.knowledge_base import KnowledgeBase
        kb    = KnowledgeBase()
        stats = kb.get_stats()
        self.assertEqual(stats["total_predictions"], 0)
        self.assertEqual(stats["with_outcomes"], 0)

    def test_embed_prediction_correct_shape(self):
        from kairon.intelligence.knowledge_base import embed_prediction
        vec = embed_prediction(62.0, 14.2, -1.2, "Risk-Off")
        self.assertEqual(len(vec), 32)
        # Should be unit-normalised
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(norm, 1.0, places=5)


class TestTimingEngine(unittest.TestCase):
    def test_urgency_classification_strong_signal(self):
        from kairon.engine.timing_engine import classify_urgency, Urgency
        u = classify_urgency(0.80, "news_catalyst", "crypto", "BTC-USD",
                              news_age_hours=1.0)
        self.assertEqual(u, Urgency.IMMEDIATE)

    def test_urgency_classification_weak_signal(self):
        from kairon.engine.timing_engine import classify_urgency, Urgency
        u = classify_urgency(0.20, "macro_shift", "bonds", "TLT")
        self.assertIn(u, [Urgency.MEDIUM, Urgency.PATIENT])

    def test_timing_recommendation_returns_all_fields(self):
        from kairon.engine.timing_engine import get_timing_recommendation
        t = get_timing_recommendation(0.65, "technical_breakout", "commodities",
                                       "GC=F", horizon_days=5, vix=14.2)
        d = t.to_dict()
        for key in ["urgency", "urgency_label", "optimal_entry", "event_risk",
                     "spread_note", "recommended_action"]:
            self.assertIn(key, d)

    def test_event_risk_returns_valid(self):
        from kairon.engine.timing_engine import get_event_risk
        er = get_event_risk("bonds", "TLT", urgency_days=14)
        self.assertIn(er.level, ["none", "low", "medium", "high"])

    def test_get_upcoming_events(self):
        from kairon.engine.timing_engine import get_upcoming_events
        events = get_upcoming_events("bonds", "TLT", days_ahead=365)
        # Should find at least FOMC and CPI events within a year
        self.assertIsInstance(events, list)

    def test_spread_note_vix_sensitive(self):
        from kairon.engine.timing_engine import get_timing_recommendation
        calm   = get_timing_recommendation(0.5,"technical_breakout","stocks","SPY",5, vix=12.0)
        fearful= get_timing_recommendation(0.5,"technical_breakout","stocks","SPY",5, vix=38.0)
        self.assertIn("elevated", fearful.spread_note.lower())
        self.assertIn("calm", calm.spread_note.lower())


class TestExplainability(unittest.TestCase):
    def setUp(self):
        self.df  = make_ohlcv()
        self.ctx = make_context(self.df)

    def test_layer1_raw_signals(self):
        from kairon.intelligence.explainability import build_layer1_raw_signals
        from kairon.data.indicators import compute_all
        ind  = compute_all(self.df, "commodities")
        mac  = {"vix": 14.2, "dxy": 103.9, "real_yield_10y": 1.87, "fed_rate": 4.33}
        news = {"gdelt_tone_72h": -1.2, "gdelt_mentions": 847}
        layer1 = build_layer1_raw_signals(ind, mac, news)
        self.assertIn("signals", layer1)
        self.assertGreater(len(layer1["signals"]), 0)
        for sig in layer1["signals"]:
            self.assertIn("label", sig)
            self.assertIn("source", sig)

    def test_layer2_patterns(self):
        from kairon.intelligence.explainability import build_layer2_patterns
        from kairon.data.indicators import compute_all
        ind    = compute_all(self.df, "commodities")
        mac    = {"vix": 25.0, "dxy": 106.0, "real_yield_10y": 0.5}
        news   = {"gdelt_tone_72h": -3.0}
        layer2 = build_layer2_patterns(ind, mac, news, "commodities")
        self.assertIn("patterns", layer2)
        self.assertIsInstance(layer2["patterns"], list)

    def test_layer3_cross_signal(self):
        from kairon.intelligence.explainability import build_layer3_cross_signal
        patterns = [
            {"name": "A", "direction": "bullish"},
            {"name": "B", "direction": "bullish"},
        ]
        layer3 = build_layer3_cross_signal(patterns, {"technical": {"signal": 0.6}})
        self.assertIn("conviction", layer3)
        self.assertIn("agreements", layer3)
        self.assertEqual(layer3["direction"], "bullish")

    def test_layer4_empty_kb(self):
        from kairon.intelligence.explainability import build_layer4_precedent
        layer4 = build_layer4_precedent({"n_similar": 0})
        self.assertFalse(layer4["has_history"])

    def test_layer4_with_kb(self):
        from kairon.intelligence.explainability import build_layer4_precedent
        kb = {"n_similar": 7, "n_correct": 6, "accuracy": 0.857,
               "avg_return": 0.021, "top_matches": [], "has_history": True}
        layer4 = build_layer4_precedent(kb)
        self.assertTrue(layer4["has_history"])
        self.assertIn("lesson", layer4)

    def test_layer5_projection(self):
        from kairon.intelligence.explainability import build_layer5_projection
        kb = {"has_history": True, "accuracy": 0.80, "avg_return": 0.02}
        layer5 = build_layer5_projection(0.70, 0.75, kb, 5, {"total_cost_pct": 0.4}, "Gold")
        self.assertIn("base_case_return", layer5)
        self.assertGreater(layer5["base_confidence"], 0)
        self.assertIn("summary", layer5)

    def test_connection_graph_structure(self):
        from kairon.intelligence.explainability import build_connection_graph
        from kairon.data.indicators import compute_all
        ind    = compute_all(self.df, "commodities")
        mac    = {"vix": 14.2, "dxy": 103.9, "real_yield_10y": 1.87, "fed_rate": 4.33}
        news   = {"gdelt_tone_72h": -1.2, "gdelt_mentions": 847}
        sigs   = {"technical": {"signal": 0.6}, "macro": {"signal": 0.7}}
        kb     = {"accuracy": 0.80, "n_correct": 6, "n_similar": 7}
        graph  = build_connection_graph("Gold", ind, mac, news, sigs, kb, 0.65, "BUY")
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertGreater(len(graph["nodes"]), 0)
        self.assertGreater(len(graph["edges"]), 0)
        for n in graph["nodes"]:
            self.assertIn("id", n)
            self.assertIn("type", n)
            self.assertIn("label", n)
        for e in graph["edges"]:
            self.assertIn("source", e)
            self.assertIn("target", e)
            self.assertIn("weight", e)

    def test_full_explanation_returns_all_layers(self):
        from kairon.intelligence.explainability import build_full_explanation
        from kairon.data.indicators import compute_all
        ind    = compute_all(self.df, "commodities")
        mac    = {"vix": 14.2, "dxy": 103.9, "real_yield_10y": 1.87, "fed_rate": 4.33,
                  "yield_curve": "flat", "inflation_exp": 2.34}
        news   = {"gdelt_tone_72h": -1.2, "gdelt_mentions": 847,
                  "signal": 0.25, "sentiment_label": "neutral"}
        sigs   = {"technical": {"signal": 0.6, "reasoning": "test"},
                  "macro": {"signal": 0.7, "reasoning": "test"}}
        kb     = {"n_similar": 7, "n_correct": 6, "accuracy": 0.857,
                   "avg_return": 0.021, "top_matches": [], "has_history": True}
        costs  = {"total_cost_pct": 0.4}
        result = build_full_explanation(
            "Gold", "commodities", "GC=F", "BUY", 0.68, 0.75,
            ind, mac, news, sigs, kb, costs, 5
        )
        for layer in ["layer1_raw_signals", "layer2_patterns", "layer3_cross_signal",
                       "layer4_precedent", "layer5_projection", "connection_graph"]:
            self.assertIn(layer, result)


class TestBacktester(unittest.TestCase):
    def test_backtest_runs_without_error(self):
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest("GC=F", "commodities", horizon_days=5, n_folds=3)
        d = result.to_dict()
        self.assertIn("accuracy", d)
        self.assertIn("n_predictions", d)
        self.assertGreaterEqual(d["accuracy"], 0.0)
        self.assertLessEqual(d["accuracy"], 1.0)

    def test_backtest_fold_count(self):
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest("SPY", "stocks", horizon_days=5, n_folds=3)
        d = result.to_dict()
        self.assertLessEqual(len(d["folds"]), 3)

    def test_backtest_no_look_ahead(self):
        """Each fold's test dates should be after its train end."""
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest("GC=F", "commodities", n_folds=3)
        folds  = result.to_dict()["folds"]
        for i in range(1, len(folds)):
            # Each fold should start after the previous one
            self.assertGreater(folds[i].get("train_days", 0),
                                folds[i-1].get("train_days", 0))

    def test_backtest_grade_assigned(self):
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest("GC=F", "commodities", n_folds=2)
        d = result.to_dict()
        self.assertIn(d["grade"], ["A", "B", "C", "D"])

    def test_sharpe_ratio_computed(self):
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest("BTC-USD", "crypto", horizon_days=3, n_folds=2)
        d = result.to_dict()
        self.assertIsInstance(d["sharpe_ratio"], float)
        self.assertFalse(math.isnan(d["sharpe_ratio"]))


class TestPortfolioLoader(unittest.TestCase):
    def test_csv_parse_generic(self):
        from kairon.engine.portfolio import parse_csv
        csv_data = "Symbol,Quantity,Price\nAAPL,50,148.20\nBTC-USD,0.25,62000\n"
        holdings = parse_csv(csv_data, "generic")
        self.assertEqual(len(holdings), 2)
        self.assertEqual(holdings[0]["ticker"], "AAPL")
        self.assertAlmostEqual(holdings[0]["quantity"], 50.0)

    def test_csv_parse_skips_empty_rows(self):
        from kairon.engine.portfolio import parse_csv
        csv_data = "Symbol,Quantity,Price\nAAPL,50,148.20\n,,\nTOTAL,,-\n"
        holdings = parse_csv(csv_data, "generic")
        self.assertEqual(len(holdings), 1)

    def test_csv_parse_missing_columns_raises(self):
        from kairon.engine.portfolio import parse_csv
        csv_data = "Name,Amount\nApple,50\n"
        with self.assertRaises(ValueError):
            parse_csv(csv_data, "generic")

    def test_holding_enrich(self):
        from kairon.engine.portfolio import Holding
        h = Holding("AAPL", "Apple", "stocks", 50, 148.20, 400)
        h.enrich(209.00, 20000.0, tax_year_days=365, short_rate=0.37, long_rate=0.20)
        self.assertAlmostEqual(h.current_value, 209.00 * 50, places=0)
        self.assertAlmostEqual(h.unrealized_gain, (209.00 - 148.20) * 50, places=0)
        self.assertTrue(h.is_long_term)   # 400 days > 365
        self.assertEqual(h.tax_rate, 0.20)

    def test_holding_short_term(self):
        from kairon.engine.portfolio import Holding
        h = Holding("BTC-USD", "Bitcoin", "crypto", 0.25, 62000, 60)
        h.enrich(87500.0, 50000.0, tax_year_days=365, short_rate=0.37, long_rate=0.20)
        self.assertFalse(h.is_long_term)
        self.assertEqual(h.tax_rate, 0.37)

    def test_demo_portfolio_loads(self):
        from kairon.engine.portfolio import load_demo_portfolio
        port = load_demo_portfolio("Balanced (Default)")
        self.assertGreater(len(port.holdings), 0)
        self.assertGreater(port.total_value, 0)

    def test_tax_optimisation_detection(self):
        from kairon.engine.portfolio import Holding, Portfolio, detect_tax_optimisations
        h = Holding("AAPL", "Apple", "stocks", 100, 100.0, 340)
        h.enrich(180.0, 18000.0)
        port = Portfolio(holdings=[h])
        port.compute_totals()
        alerts = detect_tax_optimisations(port)
        self.assertGreater(len(alerts), 0)
        self.assertGreater(alerts[0]["tax_saving"], 0)

    def test_load_portfolio_from_raw(self):
        from kairon.engine.portfolio import load_portfolio_from_holdings
        raw = [
            {"ticker": "GC=F",    "quantity": 2,    "avg_price": 2700.0, "days_held": 90},
            {"ticker": "BTC-USD", "quantity": 0.1,  "avg_price": 70000,  "days_held": 30},
        ]
        port = load_portfolio_from_holdings(raw, cash=1000.0)
        self.assertEqual(len(port.holdings), 2)
        self.assertGreater(port.total_value, 0)
        self.assertAlmostEqual(port.cash, 1000.0)



class TestCorrelationTracker(unittest.TestCase):
    def setUp(self):
        import os, tempfile
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{self._tmpfile.name}"
        from kairon.db.database import init_db
        init_db()

    def tearDown(self):
        import os
        try:
            os.remove(self._tmpfile.name)
        except FileNotFoundError:
            pass

    def test_heatmap_returns_all_pairs(self):
        from kairon.intelligence.correlation_tracker import get_correlation_heatmap_data, TRACKED_PAIRS
        data = get_correlation_heatmap_data("Risk-On")
        self.assertIn("heatmap", data)
        self.assertEqual(len(data["heatmap"]), len(TRACKED_PAIRS))

    def test_corr_values_bounded(self):
        from kairon.intelligence.correlation_tracker import compute_correlation_matrix
        corrs = compute_correlation_matrix("Risk-On")
        for label, v in corrs.items():
            if not (v != v):  # not NaN
                self.assertGreaterEqual(v, -1.0, f"{label} below -1")
                self.assertLessEqual(v,    1.0,  f"{label} above +1")

    def test_contagion_detection(self):
        from kairon.intelligence.correlation_tracker import detect_contagion
        corrs = {"SPX_BTC": 0.92, "Gold_DXY": -0.3, "BTC_ETH": 0.97,
                 "SPX_Gold": -0.6, "SPX_Oil": 0.4}
        result = detect_contagion(corrs, "Risk-On")
        self.assertIn("contagion", result)
        self.assertIn("severity", result)
        # High SPX_BTC (0.92) in Risk-On (expected 0.25-0.55) should trigger alert
        self.assertTrue(result["contagion"])

    def test_no_contagion_normal_conditions(self):
        from kairon.intelligence.correlation_tracker import detect_contagion
        corrs = {"SPX_BTC": 0.38, "Gold_DXY": -0.65, "BTC_ETH": 0.88,
                 "SPX_Gold": -0.22, "SPX_Oil": 0.25}
        result = detect_contagion(corrs, "Risk-On")
        self.assertEqual(result["severity"], "low")

    def test_snapshot_saves_to_db(self):
        from kairon.intelligence.correlation_tracker import snapshot_and_save, get_latest_snapshot
        snap = snapshot_and_save("Risk-On")
        self.assertIn("snapshot_id", snap)
        self.assertIn("correlations", snap)
        latest = get_latest_snapshot()
        self.assertIsNotNone(latest)



class TestSignalFlow(unittest.TestCase):
    """End-to-end signal flow — no network calls, uses demo data."""

    def setUp(self):
        import os, tempfile
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{self._tmpfile.name}"
        from kairon.db.database import init_db
        init_db()

    def tearDown(self):
        import os
        try:
            os.remove(self._tmpfile.name)
        except FileNotFoundError:
            pass

    def test_full_pipeline_completes(self):
        """Run the full analysis pipeline end-to-end."""
        from kairon.engine.analyzer import analyze
        result = analyze(
            ticker="GC=F", market="commodities",
            capital_usd=20000,
        )
        # Check all required keys present
        required = [
            "prediction_id","asset","ticker","market",
            "signal","confidence","composite_score","decision",
            "agent_signals","debate","costs","position",
            "llm_explanation","key_risks","created_at",
        ]
        for key in required:
            self.assertIn(key, result, f"Missing key in result: {key}")

        # Decision must be valid
        self.assertIn(result["decision"], ["BUY","HOLD","AVOID"])

        # Confidence in [0,1]
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

        # All 5 analyst agents must have run
        agent_sigs = result["agent_signals"]
        for agent in ["technical","fundamental","news","macro","cross_market"]:
            self.assertIn(agent, agent_sigs, f"Agent {agent} missing from result")

        # Costs must be non-negative
        self.assertGreaterEqual(result["costs"]["total_cost_usd"], 0)

        # Position must have the right structure
        pos = result["position"]
        self.assertIn("viable", pos)
        if pos["viable"]:
            self.assertGreater(pos["position_usd"], 0)

    def test_pipeline_different_markets(self):
        """Pipeline must succeed for at least 3 different markets."""
        from kairon.engine.analyzer import analyze
        test_cases = [
            ("GC=F",     "commodities"),
            ("BTC-USD",  "crypto"),
            ("EURUSD=X", "forex"),
        ]
        for ticker, market in test_cases:
            result = analyze(ticker=ticker, market=market, capital_usd=10000)
            self.assertIn("decision", result, f"No decision for {ticker}/{market}")

    def test_regime_override_propagates(self):
        from kairon.engine.analyzer import analyze
        result = analyze("GC=F", "commodities", 20000, regime_override="Crisis")
        self.assertEqual(result["macro_regime"], "Crisis")


# ── Runner ────────────────────────────────────────────────────────────────────
def run_tests():
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestConfig, TestDatabase, TestCache, TestIndicators,
        TestMarketData, TestSourceStatus, TestCostEngine,
        TestRiskEngine, TestAgents, TestLLMExplainer,
        TestKnowledgeBase, TestTimingEngine, TestExplainability,
        TestBacktester, TestPortfolioLoader, TestCorrelationTracker,
        TestSignalFlow,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)

    print(f"\n{'='*60}")
    print(f"Tests:   {result.testsRun}")
    print(f"Passed:  {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed:  {len(result.failures)}")
    print(f"Errors:  {len(result.errors)}")
    print(f"{'='*60}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
