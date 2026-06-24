# Document 04 — Agent Specifications
## Every Agent — Inputs, Logic, Outputs, Weights

---

## Overview: The 8-Agent Team

| Agent | Role | Primary Input | Output Type |
|-------|------|--------------|-------------|
| Technical Analyst | Pattern recognition on price data | OHLCV + 25 indicators | Signal score -1 to +1 |
| Fundamental Analyst | Intrinsic value vs current price | Financials, macro ratios | Signal score -1 to +1 |
| News Analyst | Translate events into market signals | GDELT, NewsAPI, central banks | Signal score + event classification |
| Macro Agent | Global economic regime + context | FRED, yield curve, VIX | Regime label + signal score |
| Cross-Market Agent | Contagion and time-zone effects | All markets simultaneously | Influence map + signal |
| Bull Researcher | Strongest case FOR the trade | All analyst outputs | Argument text + score |
| Bear Researcher | Strongest case AGAINST the trade | All analyst outputs | Argument text + score |
| Trader Agent | Final decision synthesis | All of the above + KB | Decision + confidence |

---

## Agent 1: Technical Analyst

### Personality
Quantitative, data-driven, skeptical of narratives. Believes price action already reflects all known information.

### Inputs
- 20+ years of OHLCV for the target asset
- 25 computed technical indicators (see full list below)
- Comparable assets in same market class (relative strength)

### The 25 Technical Indicators

| Indicator | Calculation | Signal |
|-----------|------------|--------|
| SMA 10 | 10-day simple moving average | Trend direction |
| SMA 20 | 20-day simple moving average | Medium trend |
| SMA 50 | 50-day simple moving average | Long trend |
| EMA 12 | 12-day exponential MA | MACD input |
| EMA 26 | 26-day exponential MA | MACD input |
| MACD | EMA12 - EMA26 | Momentum direction |
| MACD Signal | 9-day EMA of MACD | Entry/exit timing |
| MACD Histogram | MACD - Signal | Momentum strength |
| RSI (14) | Relative Strength Index | Overbought/oversold |
| BB Upper | SMA20 + 2×std | Resistance |
| BB Lower | SMA20 - 2×std | Support |
| BB Width | (Upper-Lower)/SMA20 | Volatility |
| BB Position | (Close-Lower)/(Upper-Lower) | Price in range |
| ATR (14) | Average True Range | Volatility absolute |
| ATR % | ATR / Close | Volatility relative |
| Volume SMA 20 | 20-day avg volume | Normal volume |
| Volume Ratio | Current/SMA20 | Volume confirmation |
| OBV | Cumulative vol×sign(return) | Accumulation/distribution |
| Return 1D | 1-day price change | Short momentum |
| Return 5D | 5-day price change | Week momentum |
| Return 20D | 20-day price change | Month momentum |
| Momentum 10 | Close/Close[10] - 1 | 10-day momentum |
| Z-Score 20 | (Close-SMA20)/std20 | Mean reversion signal |
| Close/Open | (Close-Open)/Open | Day strength |
| High/Low % | (High-Low)/Close | Intraday range |

### Scoring Logic
```python
def score_technical(indicators, market_type):
    score = 0.0

    # Trend (30% weight)
    if indicators['sma_10'] > indicators['sma_20'] > indicators['sma_50']:
        score += 0.30  # Fully aligned bullish
    elif indicators['sma_10'] < indicators['sma_20'] < indicators['sma_50']:
        score -= 0.30  # Fully aligned bearish
    else:
        score += 0.10 * (1 if indicators['close'] > indicators['sma_50'] else -1)

    # Momentum (25% weight)
    rsi = indicators['rsi']
    if 40 < rsi < 70:   score += 0.25 * (rsi - 55) / 15   # Healthy momentum
    elif rsi >= 75:      score -= 0.15   # Overbought warning
    elif rsi <= 25:      score += 0.15   # Oversold bounce potential

    # MACD (20% weight)
    if indicators['macd_hist'] > 0 and indicators['macd'] > 0:
        score += 0.20
    elif indicators['macd_hist'] < 0 and indicators['macd'] < 0:
        score -= 0.20

    # Volume confirmation (15% weight)
    if indicators['vol_ratio'] > 1.3 and indicators['return_1d'] > 0:
        score += 0.15   # High volume on up day = bullish confirmation
    elif indicators['vol_ratio'] > 1.3 and indicators['return_1d'] < 0:
        score -= 0.15   # High volume on down day = bearish confirmation

    # Bollinger position (10% weight)
    bb = indicators['bb_pos']
    if 0.3 < bb < 0.7: score += 0.0    # Neutral zone
    elif bb > 0.85:     score -= 0.10  # Near upper band — fade signal
    elif bb < 0.15:     score += 0.10  # Near lower band — bounce potential

    # Market-specific adjustments
    if market_type == 'crypto':
        score *= 0.85  # Technical less reliable for crypto (higher noise)
    elif market_type == 'bonds':
        score *= 0.70  # Bonds driven by macro, not chart patterns

    return max(-1.0, min(1.0, score))
```

### Output
```json
{
  "signal": 0.72,
  "direction": "UP",
  "confidence": 0.68,
  "key_indicators": {
    "rsi": 61.4,
    "macd_direction": "bullish",
    "trend": "fully_aligned_bullish",
    "volume_confirmation": true
  },
  "support_level": 2810.0,
  "resistance_level": 2880.0,
  "reasoning": "Price trending above all MAs. RSI at 61 — strong not overbought. MACD histogram expanding day 4. Volume confirming up moves."
}
```

---

## Agent 2: Fundamental Analyst

### Inputs by market type

**Stocks:** P/E ratio, revenue growth, earnings surprises, debt/equity, FCF yield, analyst consensus
**Forex:** Interest rate differential, inflation differential, GDP growth differential, current account
**Commodities:** Inventory levels, production data, seasonal demand, cost of production (floor price)
**Bonds:** Real yield, credit spread, duration, issuer quality
**Crypto:** Active addresses, transaction volume, miner revenue, developer activity (GitHub)
**REITs:** FFO yield, NAV premium/discount, occupancy rates, cap rates

### Key Scoring Factors
```python
FUNDAMENTAL_WEIGHTS = {
    "stocks":      {"valuation": 0.35, "growth": 0.35, "quality": 0.30},
    "forex":       {"rate_diff": 0.40, "inflation": 0.30, "growth": 0.30},
    "commodities": {"supply_demand": 0.50, "inventory": 0.30, "seasonal": 0.20},
    "bonds":       {"real_yield": 0.45, "credit": 0.35, "duration": 0.20},
    "crypto":      {"on_chain": 0.50, "network": 0.30, "sentiment": 0.20},
    "real_estate": {"yield": 0.40, "nav": 0.35, "occupancy": 0.25},
}
```

---

## Agent 3: News Analyst

### Five-Dimension Scoring

**Dimension 1 — Surprise Factor** (was this expected?)
- Scheduled event (earnings, FOMC): Only the delta from consensus matters
- Unscheduled event (war, CEO resignation): Full impact not priced in

**Dimension 2 — Source Credibility**
- Tier 1 (0.95): Central bank, SEC filing, official government release
- Tier 2 (0.80): Reuters, AP, Bloomberg, Financial Times, WSJ
- Tier 3 (0.60): CNBC, Forbes, established financial media
- Tier 4 (0.30): Blogs, social media, unverified claims

**Dimension 3 — Geographic Reach (from GDELT)**
- < 10 mentions: local news (0.3 weight)
- 10-100 mentions: regional (0.6 weight)
- > 100 mentions: global (1.0 weight)

**Dimension 4 — Market Phase Adjustment**
- Bull market: negative news discounted by 30%
- Bear market: negative news amplified by 40%
- Current phase from Macro Agent

**Dimension 5 — Time Decay**
```
0-1 hours:   100% impact
1-6 hours:   70% impact
6-24 hours:  40% impact
1-3 days:    20% impact
3-7 days:    5% impact
```

### Scheduled Events Calendar
The News Analyst tracks a calendar of upcoming events that will generate news:
- Fed FOMC meetings (8 per year)
- ECB, BoJ, BoE rate decisions
- CPI, PPI, PCE releases
- GDP releases (quarterly)
- Earnings seasons (quarterly)
- OPEC meetings
- USDA crop reports
- Non-Farm Payroll (monthly)

2-3 days before each event: reduce confidence in current signals (pending uncertainty).
After each event: re-run full analysis immediately.

---

## Agent 4: Macro Agent

### 6 Macro Regimes

| Regime | Conditions | Favored Assets | Avoid |
|--------|-----------|----------------|-------|
| Risk-On (Calm) | VIX < 20, growth positive, inflation moderate | Stocks, Crypto, REITs | Long bonds, Gold |
| Risk-Off (Fear) | VIX > 22, uncertainty rising | US Treasuries, Gold, USD | Stocks, Crypto, EM currencies |
| Inflationary | CPI > 3.5%, rising | Commodities, TIPS, Energy stocks | Long-duration bonds, Growth stocks |
| Deflationary | CPI < 1%, falling | Long-duration bonds, Utilities | Commodities, Banks |
| Stagflationary | High inflation + slow growth | Short-duration TIPS, Energy | Almost everything |
| Crisis | VIX > 35, correlation spike | USD cash, Short-term Treasuries, Gold | All risk assets |

### Yield Curve Interpretation
```
Normal  (2Y < 10Y):    Economy healthy → favor risk assets
Flat    (2Y ≈ 10Y):    Uncertainty → reduce risk
Inverted(2Y > 10Y):    Recession warning → shift to defensive
                        (80% historical accuracy, 6-18 months lead time)
```

### Central Bank Stance Classification
After reading central bank statements:
```
Hawkish:   Rate hike likely → AVOID bonds, growth stocks; FAVOR USD, value stocks
Neutral:   Hold expected → slight risk-on if economy healthy
Dovish:    Rate cut likely → FAVOR bonds, growth stocks; AVOID USD
Pivot:     Policy direction changing → HIGHEST IMPACT signal
```

---

## Agent 5: Cross-Market Contagion Agent

### Time-Zone Cascade Model

```
Hour 0  (00:00 UTC): Tokyo opens
  → Nikkei direction signals European auto, tech
  → USD/JPY movement signals risk sentiment for Asia session
  → Watch: Sony, Toyota, Softbank as proxies

Hour 2  (02:00 UTC): Shanghai/Shenzhen opens
  → CSI 300 direction signals copper, iron ore, rare earths
  → CNY/USD signals China capital flow direction
  → Watch: any commodity with China demand exposure

Hour 7  (07:00 UTC): Frankfurt/Zurich opens
  → DAX signals European manufacturing health
  → EUR/USD volume spikes (peak liquidity begins)
  → German 10Y Bund yield signals European bond market

Hour 8  (08:00 UTC): London opens (PEAK FOREX VOLUME)
  → London Metal Exchange gold fix (10:30 UTC) sets global gold price
  → FTSE 100 signals European equity sentiment
  → GBP/USD signals Brexit/UK economy sentiment

Hour 14 (14:00 UTC): New York opens (PEAK EQUITY VOLUME)
  → S&P 500 first 30 min sets global risk appetite for the day
  → VIX opening level signals fear gauge
  → DXY movement affects ALL dollar-denominated commodities

Hour 21 (21:00 UTC): US close, crypto takes over
  → BTC/ETH volume often increases
  → Low-volume period — watch for manipulation risk
  → Asian futures begin reacting to US close
```

### Dynamic Correlation Matrix
Updated daily. Separate matrices for:
- Normal regime
- Fear regime
- Crisis regime (correlations spike to 0.8-0.95)

```python
CORRELATION_REGIMES = {
    "normal": {
        ("SPX", "BTC"):  0.35,  ("SPX", "Gold"):  -0.20,
        ("SPX", "Oil"):  0.30,  ("Gold", "USD"):  -0.45,
        ("BTC", "ETH"):  0.85,  ("Oil", "CAD"):   0.55,
    },
    "fear": {
        ("SPX", "BTC"):  0.65,  ("SPX", "Gold"):  -0.55,
        ("SPX", "Oil"):  0.55,  ("Gold", "USD"):  -0.30,
    },
    "crisis": {
        ("SPX", "BTC"):  0.88,  ("SPX", "Gold"):  -0.70,
        ("SPX", "Oil"):  0.82,  # Everything crashes together
    },
}
```

---

## Agent 6 & 7: Bull Researcher + Bear Researcher

### Debate Protocol (based on TradingAgents, Xiao et al. 2025)

```
Round 1:
  Bull → strongest case for the trade
  Bear → strongest case against

Round 2 (if configured, default off for speed):
  Bull → respond to Bear's strongest argument
  Bear → respond to Bull's strongest argument

Synthesis:
  Identify top 2-3 unresolved disagreements
  These become the "key risks" in the final recommendation
```

### What Bull Researcher Looks For
- Technical signals pointing up
- Positive news catalyst
- Fundamental undervaluation
- Favorable macro regime
- Historical KB precedent supporting the trade
- Contrarian signal: is everyone already bearish? (potential reversal)

### What Bear Researcher Looks For
- Technical warning signals (divergences, overbought)
- Negative upcoming events (earnings risk, CPI risk)
- Fundamental overvaluation
- Unfavorable macro regime
- Crowded trade risk (everyone already long)
- Whether expected return exceeds costs (net profit test)

### Debate Output
```json
{
  "bull_score": 0.68,
  "bear_score": 0.42,
  "consensus": "moderately_bullish",
  "debate_quality": "high",
  "key_disagreements": [
    "Fed timing: Bull sees cut Q2, Bear says Q4",
    "DXY trajectory: Bull says 103, Bear says 106"
  ],
  "bull_capitulation_conditions": ["CPI above 3.5%", "Break below $2,800"],
  "bear_capitulation_conditions": ["Fed signals earlier cut", "China stimulus"],
  "recommendation": "proceed_with_caution"
}
```

---

## Agent 8: Trader Agent

### Aggregation Formula

```python
def aggregate_signals(signals, regime, kb_context, debate):
    # Base weights (market-type adjusted)
    base_weights = {
        "technical":    {"stocks": 0.30, "crypto": 0.38, "forex": 0.18,
                          "commodities": 0.22, "bonds": 0.12, "real_estate": 0.22},
        "fundamental":  {"stocks": 0.28, "crypto": 0.10, "forex": 0.22,
                          "commodities": 0.25, "bonds": 0.28, "real_estate": 0.28},
        "news":         {"stocks": 0.20, "crypto": 0.28, "forex": 0.25,
                          "commodities": 0.28, "bonds": 0.22, "real_estate": 0.18},
        "macro":        {"stocks": 0.15, "crypto": 0.12, "forex": 0.28,
                          "commodities": 0.18, "bonds": 0.30, "real_estate": 0.22},
        "cross_market": {"stocks": 0.07, "crypto": 0.12, "forex": 0.07,
                          "commodities": 0.07, "bonds": 0.08, "real_estate": 0.10},
    }

    # Regime multipliers
    regime_mult = {
        "crisis":    {"technical": 0.4, "news": 1.8, "macro": 1.6},
        "inflation": {"fundamental": 0.6, "macro": 1.6, "news": 1.4},
        "fear":      {"technical": 0.7, "macro": 1.4, "news": 1.5},
        "calm":      {"technical": 1.3, "fundamental": 1.4, "news": 0.7},
    }

    # Compute weighted sum
    market = signals["market"]
    weighted_sum = 0
    for agent, score in signals["agent_scores"].items():
        w = base_weights[agent][market]
        m = regime_mult.get(regime, {}).get(agent, 1.0)
        weighted_sum += score * w * m

    # Knowledge base adjustment
    kb_accuracy = kb_context.get("historical_accuracy", 0.5)
    if kb_accuracy > 0.70:   weighted_sum *= 1.10
    elif kb_accuracy < 0.40: weighted_sum *= 0.90

    # Agreement bonus
    directions = [1 if s > 0 else -1 for s in signals["agent_scores"].values()]
    agreement = abs(sum(directions)) / len(directions)
    if agreement > 0.8:   weighted_sum *= (1 + 0.10 * agreement)
    elif agreement < 0.3: weighted_sum *= 0.92  # Heavy disagreement penalty

    # Bull/Bear debate adjustment
    if debate["debate_quality"] == "high":
        bull_bear_gap = debate["bull_score"] - debate["bear_score"]
        weighted_sum += bull_bear_gap * 0.05

    return max(-1.0, min(1.0, weighted_sum))
```

### Decision Thresholds
```
> +0.65 :  STRONG BUY  — maximum conviction, full Kelly position
+0.45 to +0.65: BUY — proceed with standard position
+0.25 to +0.45: WEAK BUY — smaller position, tighter stop
-0.25 to +0.25: HOLD/NEUTRAL — no action recommended
-0.45 to -0.25: WEAK AVOID — reduce existing position
< -0.45: AVOID/SELL — clear signal to exit or not enter
```

---

## Agent Weight Summary by Market

| Agent | Stocks | Crypto | Forex | Commodities | Bonds | Real Estate |
|-------|--------|--------|-------|-------------|-------|-------------|
| Technical | 30% | 38% | 18% | 22% | 12% | 22% |
| Fundamental | 28% | 10% | 22% | 25% | 28% | 28% |
| News | 20% | 28% | 25% | 28% | 22% | 18% |
| Macro | 15% | 12% | 28% | 18% | 30% | 22% |
| Cross-Market | 7% | 12% | 7% | 7% | 8% | 10% |

These weights shift dynamically based on regime — see Document 06 for the full weight matrix.

---

*Document 04 — Agent Specifications*
*Requires approval before proceeding to build*
