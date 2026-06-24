# CapitalFlow — Agent Design Specification
## How Each Agent Thinks, What It Reads, What It Outputs

---

# Agent 1: Technical Analyst

## Personality
Quantitative, precise, skeptical of narratives. Believes price is truth.
Motto: "The chart already knows what the news will say tomorrow."

## Inputs
- Full OHLCV history for the asset (minimum 200 days)
- 25 computed technical indicators
- Comparable assets in the same market (for relative strength)

## Reasoning Process
```
1. Trend identification
   - Is price above or below SMA 50 and SMA 200?
   - Are the moving averages aligned (SMA10 > SMA20 > SMA50)?
   - What is the angle of the trend?

2. Momentum assessment
   - RSI: overbought (>70), oversold (<30), or neutral?
   - MACD: histogram expanding or contracting?
   - Rate of change over 10, 20, 60 days

3. Volatility context
   - ATR: expanding (increasing volatility) or contracting?
   - Bollinger Band width: squeeze or expansion?
   - Where is price within the Bollinger Bands?

4. Volume confirmation
   - Is volume increasing on up days? (bullish confirmation)
   - Is volume increasing on down days? (bearish confirmation)
   - OBV trend: accumulation or distribution?

5. Key levels
   - Nearest support and resistance
   - 52-week high and low
   - Prior pivot points
```

## Output Format
```json
{
  "signal": 0.72,         // -1.0 to +1.0
  "direction": "UP",
  "confidence": 0.68,
  "key_levels": {
    "support": 2810.0,
    "resistance": 2880.0,
    "current": 2847.3
  },
  "key_indicators": {
    "rsi": 62.4,
    "macd_direction": "bullish",
    "trend": "bullish",
    "volume_confirmation": true
  },
  "reasoning": "Price trending above all moving averages with RSI at 62 — strong but not overbought. MACD histogram expanding. Volume confirming the move. Key resistance at 2880."
}
```

---

# Agent 2: Fundamental Analyst

## Personality
Patient, value-oriented, skeptical of momentum. Focuses on intrinsic value.
Motto: "Price is what you pay. Value is what you get."

## Inputs (varies by market)

**For Stocks:**
- P/E ratio vs sector average and historical average
- Revenue and earnings growth rate (trailing and forward)
- Debt/equity ratio
- Free cash flow yield
- Analyst consensus and recent revisions
- Insider buying/selling activity

**For Forex:**
- Interest rate differential (country A rate minus country B rate)
- Inflation differential
- Current account balance
- GDP growth differential
- Political stability index

**For Commodities:**
- Supply/demand balance (inventory levels)
- Production data (OPEC for oil, USDA for grains, mining reports for metals)
- Seasonal demand patterns
- Cost of production (floor price)

**For Bonds:**
- Real yield (nominal yield minus inflation expectations)
- Credit spread vs benchmark
- Duration risk (sensitivity to rate changes)
- Issuer credit quality

**For Crypto:**
- Network activity (active addresses, transaction count)
- Mining/validator economics
- On-chain supply (coins moved vs dormant)
- Development activity (GitHub commits)

**For REITs:**
- Funds from Operations (FFO) yield
- Net Asset Value (NAV) premium/discount
- Occupancy rates
- Lease expiration schedule

## Output Format
```json
{
  "signal": 0.45,
  "valuation": "fair_value",  // undervalued | fair_value | overvalued
  "confidence": 0.55,
  "key_metrics": {
    "pe_ratio": 22.4,
    "pe_vs_sector": "below_average",
    "growth_rate": 0.12
  },
  "reasoning": "Trading at slight discount to sector P/E despite above-average growth. Earnings beat 3 of last 4 quarters. Slight concern: rising debt/equity.",
  "horizon": "medium_term"    // fundamental value takes time to realize
}
```

---

# Agent 3: News Analyst

## Personality
Contrarian, skeptical, reads between the lines. Knows that markets often
react irrationally to news and then correct.
Motto: "The first reaction to news is often wrong."

## Inputs
- GDELT events for asset keywords (last 72 hours)
- NewsAPI headlines (last 72 hours)
- Scheduled economic calendar (earnings, FOMC, CPI release dates)
- Social sentiment (Reddit r/stocks, r/wallstreetbets, crypto subreddits)

## Five-Dimension News Scoring

### Dimension 1: Surprise Factor
```
Expected event (FOMC meeting, earnings call):
  → Market has already partially priced this in
  → Only the SURPRISE element matters
  → Calculate: Actual vs consensus estimate

Unexpected event (war, CEO resignation, natural disaster):
  → Full impact not yet priced
  → Time to full pricing: minutes (crypto), hours (forex), days (stocks)

Surprise score: -1.0 (very negative surprise) to +1.0 (very positive surprise)
```

### Dimension 2: Source Credibility
```
Tier 1 (0.95 weight): Central bank statement, SEC filing, earnings release
Tier 2 (0.80 weight): Reuters, AP, Bloomberg, FT, WSJ
Tier 3 (0.60 weight): Established financial media (CNBC, Forbes)
Tier 4 (0.30 weight): Blogs, social media
Tier 5 (0.10 weight): Anonymous sources, unverified claims
```

### Dimension 3: Geographic Reach
```
Local news (one country, one language): 0.3 weight
Regional news (continent, 2-3 languages): 0.6 weight
Global news (major wire services, 5+ languages): 1.0 weight

GDELT NumMentions as proxy for reach:
  < 10 mentions: local
  10-100 mentions: regional
  > 100 mentions: global
```

### Dimension 4: Market Phase Adjustment
```
Bull market: negative news discounted (-30% impact)
Bear market: negative news amplified (+40% impact)
Transition: full impact

Current regime from Macro Agent adjusts final score.
```

### Dimension 5: Time Decay
```
News impact decays exponentially after initial reaction:
  0-1 hour:   100% impact
  1-6 hours:  70% impact
  6-24 hours: 40% impact
  1-3 days:   20% impact
  3-7 days:   5% impact

For slow-moving fundamentals (policy changes, secular trends):
  Impact can persist for weeks — override time decay
```

## Output Format
```json
{
  "signal": -0.3,
  "direction": "DOWN",
  "confidence": 0.60,
  "event_type": "scheduled",      // scheduled | unscheduled
  "surprise_factor": -0.4,
  "top_stories": [
    {
      "headline": "Fed signals rate hold...",
      "source_tier": 1,
      "sentiment": -0.2,
      "reach": "global",
      "published_hours_ago": 3
    }
  ],
  "gdelt_tone_72h": -0.8,
  "social_sentiment": 0.2,
  "upcoming_events": ["FOMC minutes Thursday", "CPI Friday"],
  "reasoning": "FOMC tone more hawkish than expected. Gold typically struggles when rate cut expectations fade. However, social sentiment remains constructive — retail investors not selling yet."
}
```

---

# Agent 4: Macro Agent

## Personality
Big-picture thinker. Models the global economy as an interconnected system.
Motto: "Individual asset performance is downstream of macro regime."

## Inputs
- FRED macro indicators (updated when new data released)
- Central bank statements (Fed, ECB, BoJ, BoE, PBoC, RBA)
- Government bond yields (yield curve shape)
- US Dollar Index (DXY)
- VIX (volatility index — fear gauge)
- Credit spreads (investment grade vs high yield)

## Macro Regime Classification

The Macro Agent classifies the current global regime into one of six states:

### Regime 1: Risk-On (Goldilocks)
**Conditions:** Low VIX (<20), positive economic growth, moderate inflation, stable rates
**Asset implication:**
- Favor: Equities, crypto, high-yield bonds, REITs
- Avoid: Long-duration government bonds, gold (unless hedging)
**Historical examples:** 2017, 2019, 2021 (mid-year)

### Regime 2: Risk-Off (Flight to Safety)
**Conditions:** Rising VIX (>25), economic uncertainty, geopolitical stress
**Asset implication:**
- Favor: US Treasuries, gold, Swiss franc, Japanese yen
- Avoid: Equities, crypto, high-yield bonds, emerging market currencies
**Historical examples:** 2008, 2020 (March), 2022 (Q1)

### Regime 3: Inflationary
**Conditions:** CPI rising, commodities surging, rate hike expectations
**Asset implication:**
- Favor: Commodities (oil, gold, food), TIPS, energy stocks, real estate
- Avoid: Long-duration bonds, growth stocks (high valuation)
**Historical examples:** 2021-2022

### Regime 4: Deflationary
**Conditions:** Falling prices, economic slowdown, rate cut expectations
**Asset implication:**
- Favor: Long-duration government bonds, utilities
- Avoid: Commodities, banks
**Historical examples:** 2015 (briefly), 2019 concerns

### Regime 5: Stagflationary
**Conditions:** Slow growth + high inflation simultaneously (worst case)
**Asset implication:**
- Favor: Physical gold, energy commodities, short-duration TIPS
- Avoid: Everything else — this is the hardest regime
**Historical examples:** 1970s, 2022 (partial)

### Regime 6: Crisis Mode
**Conditions:** VIX > 35, correlation spike, credit markets seizing
**Asset implication:**
- Favor: Cash, short-term government bonds, gold
- All other allocations: REDUCE
**Trigger for capital preservation mode across entire system**

## Yield Curve Interpretation
```
Normal (2Y yield < 10Y yield): 
  → Economy healthy, growth expected
  → Favor equities and risk assets

Flat (2Y yield ≈ 10Y yield):
  → Uncertainty, slowdown possible
  → Reduce risk, favor quality

Inverted (2Y yield > 10Y yield):
  → Recession warning (80% historical accuracy)
  → Begin shifting to defensive assets
  → This signal typically leads recession by 6-18 months
```

## Output Format
```json
{
  "regime": "Risk-Off",
  "confidence": 0.72,
  "regime_duration_days": 12,
  "yield_curve": "flattening",
  "vix": 24.3,
  "dxy": 104.1,
  "fed_rate": 4.75,
  "rate_trajectory": "hold",    // hike | hold | cut | uncertain
  "inflation_trend": "falling",
  "growth_trend": "slowing",
  "favorable_markets": ["bonds", "commodities"],
  "unfavorable_markets": ["crypto", "growth_stocks"],
  "key_upcoming_events": [
    {"event": "FOMC meeting", "date": "2026-03-19", "importance": "high"},
    {"event": "CPI release", "date": "2026-03-12", "importance": "high"}
  ],
  "reasoning": "VIX elevated at 24.3 but not crisis level. Yield curve flattening suggests growth concerns. Fed on hold. Risk-Off regime favors defensive positioning. Gold and short-duration bonds are preferred."
}
```

---

# Agent 5: Cross-Market Contagion Agent

## Personality
Systems thinker. Sees markets as a network, not isolated instruments.
Motto: "What happens in Tokyo at 9am affects New York at 9:30am."

## Inputs
- Real-time price data for all 6 markets across 30+ assets
- Time-zone schedule (which markets are open right now)
- Historical correlation matrices (normal + crisis regimes)
- GDELT geographic event data

## Core Algorithm: Time-Zone Information Cascade

```python
# Current time determines which markets are open
# Each open market is an "information node"

def compute_cascade_signals(current_utc_time, market_data):
    signals = {}

    # Asia session (00:00 - 08:00 UTC)
    if is_asia_session(current_utc_time):
        nikkei_move = get_move("Nikkei 225")
        shanghai_move = get_move("Shanghai Composite")

        # Nikkei up → signal for European auto stocks
        if nikkei_move > 0.01:
            signals["european_auto_stocks"] = +0.3 * nikkei_move

        # Shanghai down → signal for copper, iron ore
        if shanghai_move < -0.01:
            signals["copper"] = -0.4 * abs(shanghai_move)
            signals["iron_ore"] = -0.5 * abs(shanghai_move)

    # European session (07:00 - 16:00 UTC)
    if is_european_session(current_utc_time):
        eurusd_move = get_move("EUR/USD")
        dax_move = get_move("DAX")

        # EUR/USD move → signal for European exporters
        if abs(eurusd_move) > 0.003:
            signals["european_exporters"] = -0.5 * eurusd_move

    # ... etc for US session

    return signals
```

## Output Format
```json
{
  "cascade_signals": [
    {
      "source_market": "Asia/Shanghai",
      "source_event": "Shanghai Composite -1.8%",
      "target_asset": "Copper",
      "predicted_impact": -0.9,
      "confidence": 0.71,
      "expected_timing": "2-4 hours (London open)",
      "mechanism": "China manufacturing demand proxy"
    }
  ],
  "correlation_regime": "elevated",
  "current_correlations": {
    "SPX_BTC": 0.72,
    "Gold_USD": -0.45,
    "Oil_Stocks": 0.38
  },
  "contagion_alert": false,
  "reasoning": "Shanghai weakness is a leading indicator for copper and industrial metals. European miners (Rio Tinto, BHP) will likely open lower. Watch London Metal Exchange copper fix at 10:30 UTC."
}
```

---

# Agent 6 & 7: Bull/Bear Researchers

## Design Philosophy
Based on TradingAgents (Xiao et al., 2025) and FinMem (Yu et al., 2023).
Structured debate forces the system to explicitly model uncertainty.

## The Debate Protocol

**Round 1:**
- Bull: Makes the strongest possible case for the trade
- Bear: Makes the strongest possible case against

**Round 2 (if configured):**
- Bull: Responds to Bear's strongest arguments
- Bear: Responds to Bull's strongest arguments

**Round 3 (optional deep analysis):**
- Both acknowledge the strongest counterpoint
- Both estimate what would change their mind

**Synthesis:**
- Trader Agent reads full debate
- Identifies the top 2-3 unresolved disagreements
- These become the key risks in the final recommendation

## What Bull Researcher Considers
```
- Technical signals pointing up
- Positive news catalyst
- Fundamental undervaluation
- Favorable macro regime
- Historical precedent for this setup
- Sentiment: are most people bearish? (contrarian bullish signal)
- Institutional positioning: are smart money flows going in?
```

## What Bear Researcher Considers
```
- Technical signals pointing down or warning
- Negative news catalyst or upcoming risk
- Fundamental overvaluation
- Unfavorable macro regime for this asset
- Crowded trade risk (everyone already long)
- Transaction costs: is expected return enough?
- Time horizon: is there a better opportunity elsewhere?
- Black swan risks: what could cause a 20%+ drop?
```

## Debate Output Format
```json
{
  "bull_score": 0.65,
  "bear_score": 0.45,
  "consensus": "moderately_bullish",
  "key_disagreements": [
    "Fed timing: Bull sees cut by June, Bear says December",
    "Valuation: Bull sees fair value, Bear sees 15% overvaluation"
  ],
  "conditions_for_bull_capitulation": [
    "CPI above 3.5% on Friday",
    "Break below $2,800 support"
  ],
  "conditions_for_bear_capitulation": [
    "Fed signals earlier cut",
    "China stimulus announcement"
  ],
  "debate_quality": "high",   // low | medium | high
  "recommendation": "proceed_with_caution"
}
```

---

# Agent 8: Trader Agent

## Role
Final decision maker. Synthesizes everything into an actionable recommendation.
Has accountability — its decisions are recorded in the knowledge base.

## Inputs
- All 5 analyst reports
- Bull/Bear debate summary
- Knowledge base historical context
- Cost calculation (from Cost Engine)
- Position sizing (from Risk Manager)

## Decision Framework

```
Step 1: Weighted signal aggregation
  Technical:      30% weight (most reliable short-term)
  Fundamental:    20% weight (most reliable long-term)
  News:           20% weight (highest variance, time-sensitive)
  Macro:          20% weight (regime context)
  Cross-Market:   10% weight (additional signal)

Step 2: Knowledge base adjustment
  If historical accuracy in this situation > 70%: boost confidence +10%
  If historical accuracy in this situation < 40%: reduce confidence -15%

Step 3: Debate adjustment
  If Bull/Bear disagreement is high: reduce confidence -10%
  If both sides agree: boost confidence +10%

Step 4: Net profit check
  If net profit (after all costs) < minimum threshold: REJECT
  If net profit is marginal (< 0.5%): HOLD, wait for better setup

Step 5: Final decision
  BUY/ENTER: composite score > 0.6, net profit > threshold
  HOLD: composite score 0.4-0.6, or marginal net profit
  SELL/AVOID: composite score < 0.4, or negative net profit
```

## Output Format
```json
{
  "decision": "BUY",
  "asset": "Gold",
  "market": "commodities",
  "signal_score": 0.68,
  "confidence": 0.72,
  "horizon": "5 days",
  "entry_price": 2847.30,
  "stop_loss": 2798.00,
  "take_profit": 2920.00,
  "position_usd": 25000,
  "expected_gross_return_pct": 2.5,
  "expected_gross_return_usd": 625,
  "total_costs_usd": 87.50,
  "net_profit_usd": 537.50,
  "net_profit_pct": 2.15,
  "key_risks": [
    "CPI Friday could change Fed outlook",
    "DXY strength could cap Gold upside"
  ],
  "knowledge_base_precedent": "In 6/7 similar situations, Gold rose avg +1.8% in 5 days",
  "llm_explanation": "Gold has a clear technical setup with RSI at 62 and MACD expanding. The macro regime is Risk-Off, historically Gold's strongest environment. News sentiment shows rising geopolitical tension which acts as a safe-haven catalyst. The main risk is Friday's CPI — if above 3.5%, rate cut expectations would fade and Gold could struggle. We recommend a position with a stop below the 2800 support level."
}
```

---

*Agent Design Specification — CapitalFlow Intelligence System*
*Version 1.0, March 2026*
