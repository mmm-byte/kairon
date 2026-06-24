"""
kairon/agents/agents.py
All 8 Kairon agents implemented. Each is a self-contained class.
Context dict passed to each agent contains all pre-fetched data —
no agent fetches its own data (separation of concerns).

Context keys:
  ticker, asset, market, indicators, macro, news_signal,
  ohlcv_df, regime, kb_context, capital_usd, vix
"""
import math
import logging
from typing import Optional

from kairon.agents.base_agent import BaseAgent, AgentSignal, _direction, _confidence_from_score
from kairon.data.indicators import score_technical

logger = logging.getLogger("kairon.agents")


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1: Technical Analyst
# ─────────────────────────────────────────────────────────────────────────────
class TechnicalAnalyst(BaseAgent):
    name = "technical"

    def _analyze(self, ctx: dict) -> AgentSignal:
        ind = ctx.get("indicators", {})
        market = ctx.get("market", "stocks")
        asset  = ctx.get("asset", "Unknown")

        score = score_technical(ind, market)

        # Key levels from OHLCV
        df = ctx.get("ohlcv_df")
        support = resistance = None
        if df is not None and not df.empty:
            recent = df.tail(60)
            support    = round(float(recent["low"].min()), 4)
            resistance = round(float(recent["high"].max()), 4)

        rsi  = ind.get("rsi")
        macd = ind.get("macd")
        trend = ind.get("trend", "neutral")
        vol_ratio = ind.get("vol_ratio")
        bb_pos = ind.get("bb_pos")

        # Build reasoning
        parts = []
        if trend in ("bullish", "mixed_bullish"):
            parts.append(f"Price above key MAs ({trend})")
        elif trend in ("bearish", "mixed_bearish"):
            parts.append(f"Price below key MAs ({trend})")

        if rsi is not None:
            if rsi > 70:  parts.append(f"RSI overbought at {rsi:.0f}")
            elif rsi < 30: parts.append(f"RSI oversold at {rsi:.0f} — bounce potential")
            else:          parts.append(f"RSI neutral at {rsi:.0f}")

        if macd is not None:
            macd_dir = "bullish" if macd > 0 else "bearish"
            parts.append(f"MACD {macd_dir} ({macd:+.3f})")

        if vol_ratio is not None:
            if vol_ratio > 1.3:
                parts.append(f"Volume confirming ({vol_ratio:.1f}x avg)")
            elif vol_ratio < 0.7:
                parts.append(f"Low volume ({vol_ratio:.1f}x avg) — weak conviction")

        if bb_pos is not None:
            if bb_pos > 0.85:  parts.append("Near Bollinger upper band")
            elif bb_pos < 0.15: parts.append("Near Bollinger lower band")

        reasoning = f"{asset} Technical: " + ". ".join(parts) + f". Score: {score:+.2f}."
        if support and resistance:
            reasoning += f" Support ${support:,.2f} | Resistance ${resistance:,.2f}."

        return AgentSignal(
            agent_name="technical",
            signal=score,
            direction=_direction(score),
            confidence=_confidence_from_score(score),
            reasoning=reasoning,
            raw_data={
                "key_levels": {"support": support, "resistance": resistance,
                               "current": ind.get("close")},
                "rsi": rsi, "trend": trend,
                "macd_direction": "bullish" if (macd or 0) > 0 else "bearish",
                "volume_confirmation": bool(vol_ratio and vol_ratio > 1.3),
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 2: Fundamental Analyst
# ─────────────────────────────────────────────────────────────────────────────
class FundamentalAnalyst(BaseAgent):
    name = "fundamental"

    def _analyze(self, ctx: dict) -> AgentSignal:
        market = ctx.get("market", "stocks")
        asset  = ctx.get("asset", "Unknown")
        macro  = ctx.get("macro", {})
        ind    = ctx.get("indicators", {})

        score = 0.0
        valuation = "fair_value"
        parts = []

        if market == "stocks":
            # Use macro + price momentum as proxy for fundamentals
            ret_20d = ind.get("return_20d") or 0
            z_score = ind.get("z_score_20") or 0
            if ret_20d > 0.05 and z_score < 1.5:
                score += 0.3; parts.append("Positive 20d momentum without extreme overextension")
            elif z_score > 2.0:
                score -= 0.25; valuation = "overvalued"; parts.append("Price extended >2 std devs above mean")
            elif z_score < -1.5:
                score += 0.25; valuation = "undervalued"; parts.append("Price below mean — value opportunity")

        elif market == "commodities":
            real_yield = macro.get("real_yield_10y") or 1.9
            regime     = ctx.get("regime", {}).get("regime", "Risk-On")
            if real_yield < 1.0:
                score += 0.35; parts.append(f"Real yield low ({real_yield:.2f}%) — gold attractive")
            elif real_yield > 2.5:
                score -= 0.25; parts.append(f"Real yield high ({real_yield:.2f}%) — gold headwind")
            if "gold" in asset.lower() and regime in ("Risk-Off", "Crisis", "Stagflationary"):
                score += 0.25; parts.append(f"Safe haven regime ({regime}) historically bullish for gold")

        elif market == "crypto":
            ret_5d  = ind.get("return_5d") or 0
            z_score = ind.get("z_score_20") or 0
            if z_score < 0 and ret_5d > -0.05:
                score += 0.20; valuation = "undervalued"; parts.append("Below 20d mean — potential value entry")
            elif z_score > 2.5:
                score -= 0.30; valuation = "overvalued"; parts.append("Significantly extended — overvalued risk")
            parts.append("On-chain metrics tracked but no live data source (network demand proxy used)")

        elif market == "bonds":
            real_yield = macro.get("real_yield_10y") or 1.9
            yield_curve = macro.get("yield_curve", "normal")
            if real_yield > 2.0:
                score += 0.30; parts.append(f"Real yield {real_yield:.2f}% attractive for bonds")
            if yield_curve == "inverted":
                score += 0.20; parts.append("Inverted curve → bonds likely to gain as rates cut")
            elif yield_curve == "normal":
                score -= 0.10; parts.append("Normal curve — bonds less attractive vs equities")

        elif market == "forex":
            fed = macro.get("fed_rate") or 4.33
            ecb = macro.get("ecb_rate") or 3.25
            diff = fed - ecb
            if diff > 1.0:
                score += 0.25; parts.append(f"USD rate premium +{diff:.2f}% vs EUR → USD strong")
            elif diff < 0:
                score -= 0.20; parts.append(f"USD rate discount {diff:.2f}% → USD weak")

        elif market == "real_estate":
            yield_10y = macro.get("yield_10y") or 4.21
            if yield_10y > 4.5:
                score -= 0.30; parts.append(f"10Y yield {yield_10y:.2f}% compresses cap rates")
            else:
                score += 0.20; parts.append(f"10Y yield {yield_10y:.2f}% supports REIT valuations")

        score = max(-1.0, min(1.0, score))
        reasoning = (f"{asset} Fundamental ({market}): " + ". ".join(parts) +
                     f" Valuation: {valuation}. Score: {score:+.2f}.")

        return AgentSignal(
            agent_name="fundamental",
            signal=score,
            direction=_direction(score),
            confidence=_confidence_from_score(score) * 0.85,  # fundamentals less certain short-term
            reasoning=reasoning,
            raw_data={"valuation": valuation, "horizon": "medium_term"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 3: News Analyst
# ─────────────────────────────────────────────────────────────────────────────
class NewsAnalyst(BaseAgent):
    name = "news"

    def _analyze(self, ctx: dict) -> AgentSignal:
        news   = ctx.get("news_signal", {})
        asset  = ctx.get("asset", "Unknown")
        regime = ctx.get("regime", {}).get("regime", "Risk-On")

        raw_signal   = news.get("signal", 0.0)
        confidence   = news.get("confidence", 0.0)
        n_sources    = news.get("n_sources", 0)
        n_outlets    = news.get("n_outlets", 0)
        gdelt_tone   = news.get("gdelt_tone_72h", 0.0)
        gdelt_mentions = news.get("gdelt_mentions", 0)
        top_headlines  = news.get("top_headlines", [])
        label          = news.get("sentiment_label", "neutral")

        # Phase adjustment (Document 04, Dimension 4)
        signal = raw_signal
        if regime == "Risk-Off":
            if signal < 0:
                signal *= 1.4   # negative news amplified in bear/risk-off
            else:
                signal *= 0.8   # positive news discounted
        elif regime == "Risk-On":
            if signal < 0:
                signal *= 0.7   # negative news discounted in bull
            else:
                signal *= 1.1

        signal = max(-1.0, min(1.0, signal))

        parts = [f"Multi-source sentiment: {label} ({raw_signal:+.3f})"]
        parts.append(f"Sources: {n_sources} articles from {n_outlets} outlets")
        if gdelt_mentions > 0:
            parts.append(f"GDELT: {gdelt_mentions} mentions, tone {gdelt_tone:+.1f}")
        if top_headlines:
            h = top_headlines[0]
            tier_label = "Tier-1" if h.get("tier", 0) >= 0.80 else "Tier-2"
            parts.append(f"Top headline ({tier_label}): \"{h['headline'][:80]}\"")
        parts.append(f"Phase-adjusted signal: {signal:+.3f} (regime: {regime})")

        return AgentSignal(
            agent_name="news",
            signal=round(signal, 4),
            direction=_direction(signal),
            confidence=min(0.90, max(0.30, confidence)),
            reasoning=f"{asset} News: " + ". ".join(parts) + ".",
            raw_data={
                "raw_signal":      raw_signal,
                "gdelt_tone_72h":  gdelt_tone,
                "gdelt_mentions":  gdelt_mentions,
                "n_sources":       n_sources,
                "top_headlines":   top_headlines[:5],
                "sentiment_label": label,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 4: Macro Agent
# ─────────────────────────────────────────────────────────────────────────────
class MacroAgent(BaseAgent):
    name = "macro"

    # Per-market favorability in each regime (from Document 04)
    REGIME_MARKET_SCORES = {
        "Risk-On":       {"stocks": 0.7, "crypto": 0.6, "real_estate": 0.5,
                          "bonds": -0.3, "commodities": 0.1, "forex": 0.2},
        "Risk-Off":      {"bonds": 0.7, "commodities": 0.6, "forex": 0.2,
                          "stocks": -0.4, "crypto": -0.5, "real_estate": -0.2},
        "Inflationary":  {"commodities": 0.8, "real_estate": 0.4,
                          "bonds": -0.6, "stocks": 0.1, "crypto": 0.2, "forex": 0.1},
        "Deflationary":  {"bonds": 0.7, "stocks": -0.2,
                          "commodities": -0.4, "crypto": -0.3, "real_estate": -0.2, "forex": 0.1},
        "Stagflationary":{"commodities": 0.5, "bonds": -0.3,
                          "stocks": -0.4, "crypto": -0.5, "real_estate": -0.2, "forex": 0.0},
        "Crisis":        {"bonds": 0.8, "commodities": 0.5, "forex": 0.3,
                          "stocks": -0.7, "crypto": -0.8, "real_estate": -0.5},
    }

    def _analyze(self, ctx: dict) -> AgentSignal:
        macro  = ctx.get("macro", {})
        regime = ctx.get("regime", {})
        market = ctx.get("market", "stocks")
        asset  = ctx.get("asset", "Unknown")

        regime_name = regime.get("regime", "Risk-On")
        regime_conf = regime.get("confidence", 0.5)
        regime_reasoning = regime.get("reasoning", "")

        market_score = self.REGIME_MARKET_SCORES.get(regime_name, {}).get(market, 0.0)

        vix       = macro.get("vix") or 14.2
        dxy       = macro.get("dxy") or 103.9
        yc        = macro.get("yield_curve", "normal")
        real_yield = macro.get("real_yield_10y") or 1.9
        fed       = macro.get("fed_rate") or 4.33

        parts = [f"Regime: {regime_name} (confidence {regime_conf:.0%})"]
        parts.append(f"VIX={vix:.1f} | DXY={dxy:.1f} | Yield curve={yc}")
        parts.append(f"Real yield 10Y={real_yield:.2f}% | Fed={fed:.2f}%")
        parts.append(f"{market} is {'favored' if market_score > 0 else 'unfavored'} in {regime_name}")
        if regime_reasoning:
            parts.append(regime_reasoning)

        score = max(-1.0, min(1.0, market_score))

        return AgentSignal(
            agent_name="macro",
            signal=round(score, 4),
            direction=_direction(score),
            confidence=min(0.90, regime_conf * 0.9),
            reasoning=f"{asset} Macro: " + ". ".join(parts) + f". Score: {score:+.2f}.",
            raw_data={
                "regime":        regime_name,
                "vix":           vix,
                "dxy":           dxy,
                "yield_curve":   yc,
                "fed_rate":      fed,
                "real_yield_10y": real_yield,
                "rate_trajectory": "hold",
                "favorable_markets":   regime.get("favorable_markets", []),
                "unfavorable_markets": regime.get("unfavorable_markets", []),
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 5: Cross-Market Contagion Agent
# ─────────────────────────────────────────────────────────────────────────────
class CrossMarketAgent(BaseAgent):
    name = "cross_market"

    # Influence weights from Document 06
    CROSS_INFLUENCE = {
        "DXY": {
            "commodities": -0.68,  # strong inverse (gold, oil priced in USD)
            "crypto":      -0.25,
            "bonds":        0.20,
            "stocks":       0.10,
        },
        "VIX": {
            "commodities":  0.55,  # fear → safe haven
            "bonds":        0.65,  # fear → treasury demand
            "crypto":      -0.45,  # fear → crypto sell-off
            "stocks":      -0.80,  # definitional inverse
        },
        "SPX": {
            "crypto":       0.40,
            "real_estate":  0.35,
            "commodities":  0.20,
            "bonds":       -0.45,
        },
    }

    # Static correlation matrices by regime (Document 06)
    CORRELATIONS = {
        "Risk-On":  {"SPX_BTC": 0.35, "SPX_Gold": -0.20, "Gold_DXY": -0.68, "BTC_ETH": 0.85},
        "Risk-Off": {"SPX_BTC": 0.65, "SPX_Gold": -0.55, "Gold_DXY": -0.30, "BTC_ETH": 0.92},
        "Crisis":   {"SPX_BTC": 0.88, "SPX_Gold": -0.70, "Gold_DXY":  0.45, "BTC_ETH": 0.95},
        "Inflationary": {"SPX_BTC": 0.40, "SPX_Gold": -0.10, "Gold_DXY": -0.55, "BTC_ETH": 0.80},
    }

    def _analyze(self, ctx: dict) -> AgentSignal:
        market  = ctx.get("market", "stocks")
        asset   = ctx.get("asset", "Unknown")
        macro   = ctx.get("macro", {})
        regime  = ctx.get("regime", {}).get("regime", "Risk-On")

        vix = macro.get("vix") or 14.2
        dxy = macro.get("dxy") or 103.9
        dxy_5d = ctx.get("indicators", {}).get("return_5d") or 0  # using target asset's 5d for proxy

        score = 0.0
        cascade_signals = []
        parts = []

        # DXY influence
        dxy_influence = self.CROSS_INFLUENCE["DXY"].get(market, 0.0)
        # Normalize DXY change: if DXY > 105 (strong dollar), treat as negative
        dxy_signal = -0.5 if dxy > 105 else (0.3 if dxy < 102 else 0.0)
        dxy_contribution = dxy_influence * dxy_signal
        score += dxy_contribution
        if abs(dxy_contribution) > 0.05:
            direction = "headwind" if dxy_contribution < 0 else "tailwind"
            parts.append(f"DXY={dxy:.1f} → {direction} for {market} ({dxy_contribution:+.2f})")
            cascade_signals.append({
                "source_market": "Forex/DXY",
                "source_event": f"DXY at {dxy:.1f}",
                "target_asset": asset,
                "predicted_impact": round(dxy_contribution, 3),
                "confidence": 0.65,
                "mechanism": "Dollar pricing effect on commodity/crypto markets",
            })

        # VIX influence
        vix_influence = self.CROSS_INFLUENCE["VIX"].get(market, 0.0)
        vix_signal = (vix - 18) / 20  # normalized; 0 at VIX=18, +1 at VIX=38
        vix_contribution = vix_influence * max(-1, min(1, vix_signal))
        score += vix_contribution
        if abs(vix_contribution) > 0.05:
            parts.append(f"VIX={vix:.1f} → {vix_contribution:+.2f} influence on {market}")

        # Regime correlation context
        corr = self.CORRELATIONS.get(regime, self.CORRELATIONS["Risk-On"])
        if market == "commodities":
            parts.append(f"Gold/DXY correlation in {regime}: {corr.get('Gold_DXY', -0.68):.2f}")
        elif market == "crypto":
            parts.append(f"BTC/ETH correlation in {regime}: {corr.get('BTC_ETH', 0.85):.2f}")
            parts.append(f"SPX/BTC correlation in {regime}: {corr.get('SPX_BTC', 0.35):.2f}")

        score = max(-1.0, min(1.0, score))
        corr_regime = "elevated" if regime in ("Risk-Off", "Crisis") else "normal"
        reasoning = (f"{asset} Cross-Market ({regime}): " + ". ".join(parts) +
                     f". Correlation regime: {corr_regime}. Score: {score:+.2f}.")

        return AgentSignal(
            agent_name="cross_market",
            signal=round(score, 4),
            direction=_direction(score),
            confidence=_confidence_from_score(score) * 0.80,
            reasoning=reasoning,
            raw_data={
                "cascade_signals":    cascade_signals,
                "correlation_regime": corr_regime,
                "current_correlations": corr,
                "contagion_alert":    regime == "Crisis",
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENTS 6 & 7: Bull and Bear Researchers + Debate
# ─────────────────────────────────────────────────────────────────────────────
class BullResearcher(BaseAgent):
    name = "bull"

    def _analyze(self, ctx: dict) -> AgentSignal:
        signals = ctx.get("analyst_signals", {})
        asset   = ctx.get("asset", "Unknown")
        macro   = ctx.get("macro", {})
        regime  = ctx.get("regime", {}).get("regime", "Risk-On")

        score  = 0.0
        points = []

        tech  = signals.get("technical", {}).get("signal", 0)
        fund  = signals.get("fundamental", {}).get("signal", 0)
        news  = signals.get("news", {}).get("signal", 0)
        mac   = signals.get("macro", {}).get("signal", 0)
        cross = signals.get("cross_market", {}).get("signal", 0)

        # Bull: emphasise positive signals
        if tech > 0.3:
            score += tech * 0.4
            rsi = ctx.get("indicators", {}).get("rsi")
            rsi_str = f", RSI at {rsi:.0f}" if rsi else ""
            points.append(f"Technical breakout confirmed{rsi_str} — momentum is building")
        if fund > 0.2:
            score += fund * 0.25
            points.append("Fundamentals support entry — asset appears fairly/undervalued")
        if news > 0.1:
            score += news * 0.20
            points.append(f"News sentiment positive from {ctx.get('news_signal',{}).get('n_outlets',0)} outlets")
        if mac > 0.3:
            score += mac * 0.25
            points.append(f"Macro regime ({regime}) historically strong for {ctx.get('market')}")

        # Contrarian angle: if sentiment is very negative, that's a bull signal
        if news < -0.5:
            score += 0.15
            points.append("Extreme bearish sentiment — contrarian buy signal possible")

        # KB precedent boost
        kb = ctx.get("kb_context", {})
        kb_acc = kb.get("accuracy", 0.5)
        if kb_acc > 0.70:
            score += 0.10
            points.append(f"KB shows {kb_acc:.0%} accuracy in similar setups — history supports")

        score = max(0.0, min(1.0, score))
        argument = (f"BULL CASE for {asset}: " +
                    " | ".join(points) if points else "No strong bull catalysts identified.")

        return AgentSignal(
            agent_name="bull",
            signal=round(score, 4),
            direction="UP",
            confidence=round(score * 0.9, 3),
            reasoning=argument,
        )


class BearResearcher(BaseAgent):
    name = "bear"

    def _analyze(self, ctx: dict) -> AgentSignal:
        signals = ctx.get("analyst_signals", {})
        asset   = ctx.get("asset", "Unknown")
        macro   = ctx.get("macro", {})
        ind     = ctx.get("indicators", {})
        regime  = ctx.get("regime", {}).get("regime", "Risk-On")

        score  = 0.0
        points = []

        tech  = signals.get("technical", {}).get("signal", 0)
        fund  = signals.get("fundamental", {}).get("signal", 0)
        news  = signals.get("news", {}).get("signal", 0)
        mac   = signals.get("macro", {}).get("signal", 0)

        # Bear: emphasise risks and negatives
        if tech < -0.2:
            score += abs(tech) * 0.35
            points.append("Technical picture is bearish — price failing to hold key MAs")
        if fund < -0.2:
            score += abs(fund) * 0.25
            points.append("Fundamentals look stretched — risk of mean reversion")
        if news < -0.2:
            score += abs(news) * 0.20
            points.append("News sentiment is negative — headwinds from media coverage")

        # Overbought RSI = bear risk
        rsi = ind.get("rsi")
        if rsi and rsi > 70:
            score += 0.20
            points.append(f"RSI overbought at {rsi:.0f} — reversal risk elevated")

        # High VIX = systemic risk
        vix = macro.get("vix") or 14.2
        if vix > 25:
            score += 0.15
            points.append(f"Elevated VIX={vix:.1f} — uncertainty is high")

        # Regime risk
        if regime in ("Stagflationary", "Crisis"):
            score += 0.25
            points.append(f"{regime} regime is historically difficult for most assets")

        # Cost drag
        costs = ctx.get("costs", {})
        total_cost_pct = costs.get("total_cost_pct", 0)
        if total_cost_pct > 0.8:
            score += 0.10
            points.append(f"Transaction costs high ({total_cost_pct:.2f}%) — hurdle rate elevated")

        score = max(0.0, min(1.0, score))
        argument = (f"BEAR CASE for {asset}: " +
                    " | ".join(points) if points else "No major bear risks identified.")

        return AgentSignal(
            agent_name="bear",
            signal=round(score, 4),
            direction="DOWN",
            confidence=round(score * 0.85, 3),
            reasoning=argument,
        )


def run_bull_bear_debate(ctx: dict) -> dict:
    """
    Orchestrates the full Bull/Bear debate and returns a synthesis.
    Implements Document 04 debate protocol (1 round by default).
    """
    bull_sig = BullResearcher().run(ctx)
    bear_sig = BearResearcher().run(ctx)

    bull_score = bull_sig.signal
    bear_score = bear_sig.signal
    gap        = bull_score - bear_score

    if gap > 0.3:
        consensus = "strongly_bullish"
        recommendation = "proceed"
    elif gap > 0.1:
        consensus = "moderately_bullish"
        recommendation = "proceed_with_caution"
    elif gap < -0.3:
        consensus = "strongly_bearish"
        recommendation = "avoid"
    elif gap < -0.1:
        consensus = "moderately_bearish"
        recommendation = "avoid"
    else:
        consensus = "neutral"
        recommendation = "hold"

    # Quality: higher when both sides have strong arguments
    avg_confidence = (bull_sig.confidence + bear_sig.confidence) / 2
    quality = "high" if avg_confidence > 0.65 else ("medium" if avg_confidence > 0.40 else "low")

    ind   = ctx.get("indicators", {})
    macro = ctx.get("macro", {})
    asset = ctx.get("asset", "Unknown")
    rsi   = ind.get("rsi")
    vix   = macro.get("vix") or 14.2

    disagreements = []
    if abs(bull_score - bear_score) > 0.2:
        disagreements.append("Signal strength: Bull and Bear significantly disagree on current setup")
    if rsi and rsi > 65:
        disagreements.append(f"RSI ({rsi:.0f}): Bull sees momentum, Bear sees overbought")
    if vix > 20:
        disagreements.append(f"VIX ({vix:.0f}): elevated uncertainty, timing disagreement")

    bull_cap = []
    bear_cap = []
    macro_snap = ctx.get("macro", {})
    if macro_snap.get("real_yield_10y", 0) < 1.5:
        bear_cap.append("Real yields rise above 2% — opportunity cost increases")
    bull_cap.append("Signal reverses below key technical support")
    bear_cap.append("Macro regime shifts to Risk-On — bear thesis collapses")

    return {
        "bull_score":  round(bull_score, 4),
        "bear_score":  round(bear_score, 4),
        "bull_argument": bull_sig.reasoning,
        "bear_argument": bear_sig.reasoning,
        "consensus":   consensus,
        "recommendation": recommendation,
        "debate_quality": quality,
        "key_disagreements": disagreements,
        "conditions_for_bull_capitulation": bull_cap,
        "conditions_for_bear_capitulation": bear_cap,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 8: Trader Agent (Synthesiser)
# ─────────────────────────────────────────────────────────────────────────────
class TraderAgent(BaseAgent):
    name = "trader"

    # Base weights from Document 21 (authoritative source)
    BASE_WEIGHTS = {
        "technical":    0.30,
        "fundamental":  0.20,
        "news":         0.20,
        "macro":        0.20,
        "cross_market": 0.10,
    }

    # Regime multipliers from AGENT_DESIGN.md
    REGIME_MULTIPLIERS = {
        "Crisis":       {"technical": 0.4, "news": 1.8, "macro": 1.6},
        "Inflationary": {"fundamental": 0.6, "macro": 1.6, "news": 1.4},
        "Risk-Off":     {"technical": 0.7, "macro": 1.4, "news": 1.5},
        "Risk-On":      {"technical": 1.3, "fundamental": 1.4, "news": 0.7},
    }

    # Market-type weight adjustments (Document 04)
    MARKET_WEIGHT_ADJUSTMENTS = {
        "stocks":      {"technical": 1.05, "fundamental": 1.10},
        "crypto":      {"technical": 1.25, "news": 1.30, "fundamental": 0.50},
        "forex":       {"macro": 1.35, "news": 1.10, "technical": 0.75},
        "commodities": {"news": 1.30, "fundamental": 1.10, "macro": 0.90},
        "bonds":       {"macro": 1.50, "fundamental": 1.20, "technical": 0.55},
        "real_estate": {"fundamental": 1.20, "macro": 1.10},
    }

    def _analyze(self, ctx: dict) -> AgentSignal:
        signals  = ctx.get("analyst_signals", {})
        debate   = ctx.get("debate", {})
        kb       = ctx.get("kb_context", {})
        market   = ctx.get("market", "stocks")
        asset    = ctx.get("asset", "Unknown")
        regime   = ctx.get("regime", {}).get("regime", "Risk-On")
        costs    = ctx.get("costs", {})

        # ── Step 1: Weighted signal aggregation ───────────────────────────
        regime_mults  = self.REGIME_MULTIPLIERS.get(regime, {})
        market_mults  = self.MARKET_WEIGHT_ADJUSTMENTS.get(market, {})

        weighted_sum  = 0.0
        total_weight  = 0.0
        for agent, base_w in self.BASE_WEIGHTS.items():
            sig = signals.get(agent, {})
            if not sig:
                continue
            score = sig.get("signal", 0.0)
            rm = regime_mults.get(agent, 1.0)
            mm = market_mults.get(agent, 1.0)
            w  = base_w * rm * mm
            weighted_sum += score * w
            total_weight += w

        composite = weighted_sum / total_weight if total_weight > 0 else 0.0

        # ── Step 2: KB adjustment ─────────────────────────────────────────
        kb_accuracy = kb.get("accuracy", 0.5)
        if kb_accuracy > 0.70:
            composite *= 1.10
        elif kb_accuracy < 0.40:
            composite *= 0.90
        composite = max(-1.0, min(1.0, composite))

        # ── Step 3: Debate adjustment ──────────────────────────────────────
        bull_s  = debate.get("bull_score", 0.5)
        bear_s  = debate.get("bear_score", 0.5)
        gap     = abs(bull_s - bear_s)
        if gap < 0.1:
            composite *= 1.10   # both agree = boost
        elif gap > 0.4:
            composite *= 0.90   # strong disagreement = reduce

        # ── Step 4: Final confidence ───────────────────────────────────────
        avg_agent_confidence = sum(
            s.get("confidence", 0.5)
            for s in signals.values() if s
        ) / max(1, len(signals))

        kb_n = kb.get("n_similar", 0)
        kb_str = f"KB: {kb.get('n_correct',0)}/{kb_n} similar correct" if kb_n > 0 else "KB: building..."

        confidence = (
            avg_agent_confidence * 0.60 +
            (kb_accuracy if kb_n > 0 else 0.50) * 0.25 +
            (0.60 if gap < 0.2 else 0.40) * 0.15
        )
        confidence = max(0.30, min(0.95, confidence))

        # ── Step 5: Decision thresholds ───────────────────────────────────
        total_cost_pct = costs.get("total_cost_pct", 0.5)
        net_return_pct = abs(composite) * 3.0  # rough expected 3% gross per signal unit
        net_profit_pct = net_return_pct - total_cost_pct / 100

        if composite > 0.60 and net_profit_pct > 0.005:
            decision = "BUY"
        elif composite < -0.40 or net_profit_pct < 0:
            decision = "AVOID"
        else:
            decision = "HOLD"

        parts = [
            f"Composite score: {composite:+.3f} ({decision})",
            f"Agent agreement: {'high' if gap < 0.2 else 'low'} (bull-bear gap {gap:.2f})",
            f"KB confidence: {kb_str}",
            f"Net profit after costs: {net_profit_pct:.2%}",
        ]

        # Force type classification
        macro_sig  = signals.get("macro", {}).get("signal", 0)
        news_sig   = signals.get("news", {}).get("signal", 0)
        tech_sig   = signals.get("technical", {}).get("signal", 0)
        if abs(macro_sig) > abs(tech_sig) and abs(macro_sig) > abs(news_sig):
            force_type = "macro_shift"
        elif abs(news_sig) > abs(tech_sig):
            force_type = "news_catalyst"
        else:
            force_type = "technical_breakout"

        return AgentSignal(
            agent_name="trader",
            signal=round(composite, 4),
            direction=_direction(composite),
            confidence=round(confidence, 3),
            reasoning=" | ".join(parts),
            raw_data={
                "decision":          decision,
                "force_type":        force_type,
                "composite_score":   round(composite, 4),
                "net_profit_pct":    round(net_profit_pct, 4),
                "debate_consensus":  debate.get("consensus", "neutral"),
                "kb_precedent":      kb.get("precedent_text", "No KB history yet"),
                "key_risks":         debate.get("key_disagreements", []),
            },
        )
