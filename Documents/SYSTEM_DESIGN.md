# CapitalFlow Intelligence System
## Complete System Design Document
### Version 1.0 — March 2026

---

# Table of Contents

1. [Vision & Scope](#1-vision--scope)
2. [What Makes This Different](#2-what-makes-this-different)
3. [Academic Foundation](#3-academic-foundation)
4. [System Architecture](#4-system-architecture)
5. [Data Layer](#5-data-layer)
6. [Intelligence Layer — Multi-Agent Design](#6-intelligence-layer--multi-agent-design)
7. [Knowledge Base — The Learning Brain](#7-knowledge-base--the-learning-brain)
8. [Global Market Interconnection Model](#8-global-market-interconnection-model)
9. [Prediction Pipeline](#9-prediction-pipeline)
10. [Capital Allocation Engine](#10-capital-allocation-engine)
11. [Transaction Cost Intelligence](#11-transaction-cost-intelligence)
12. [Risk Architecture](#12-risk-architecture)
13. [Build Roadmap — Phase by Phase](#13-build-roadmap--phase-by-phase)
14. [Technology Stack](#14-technology-stack)
15. [Key Papers & References](#15-key-papers--references)

---

# 1. Vision & Scope

## What We Are Building

CapitalFlow is not a prediction model. It is an **intelligence system** that learns how the world's financial markets respond to events — and uses that understanding to recommend where to move money for maximum net profit after every cost.

The core insight driving this system:

> *Markets do not move in isolation. When a factory in China shuts down, commodity prices in the US move. When the European Central Bank raises rates, Asian currency markets react before American ones open. When a war breaks out, money flows from equities into gold and bonds within minutes. A prediction system that does not model these global relationships is fundamentally incomplete.*

This system does three things no existing open-source tool does simultaneously:

1. **Reads the world** — ingests news, geopolitical events, macro announcements, and earnings from every major country before they affect prices
2. **Understands relationships** — models how markets in Asia affect markets in Europe which affect markets in America, with time-zone awareness
3. **Grows smarter** — every prediction it makes, right or wrong, becomes knowledge that improves the next prediction

---

# 2. What Makes This Different

## Comparison to Existing Systems

| Feature | CapitalFlow | TradingAgents (Tauric) | MiroFish | FinGPT | Simple ML Model |
|---------|-------------|------------------------|----------|--------|-----------------|
| Multi-market (6 markets) | Yes | No (stocks only) | No | No | No |
| Global cross-country signals | Yes | No | Partial | No | No |
| News before price reaction | Yes | Partial | Yes | Partial | No |
| Time-zone market sequencing | Yes | No | No | No | No |
| Growing knowledge base | Yes | No | Yes | No | No |
| Full transaction cost model | Yes | No | No | No | No |
| Learns from past predictions | Yes | No | Yes | No | No |
| Multi-agent debate | Yes | Yes | Partial | No | No |
| LLM-agnostic | Yes | Yes | No | No | No |

## The Key Innovation — Knowledge Base That Grows

Unlike every other system, CapitalFlow maintains a **living knowledge base** where:

- Every prediction made is stored with its context (what news existed, what the market looked like)
- Every outcome (was the prediction correct?) is fed back
- Future predictions query this history: "The last 3 times oil news hit like this, gold moved up 2.1% within 48 hours"
- The system gets more accurate over time, not just more confident

This is inspired by MiroFish's GraphRAG approach and ElliottAgents' backtester knowledge base, but applied to multi-market capital allocation rather than single-asset prediction.

---

# 3. Academic Foundation

## The Papers This System Is Built On

### 3.1 Multi-Agent Financial Intelligence

**TradingAgents (Xiao et al., 2025)** — arXiv:2412.20138
The foundational architecture reference. Introduces the concept of specialized analyst agents (fundamental, sentiment, news, technical) that debate before a trader agent makes a decision. CapitalFlow extends this with global market agents and a learning knowledge base.

Key insight adopted: *Separating analysis roles into specialized agents and having them debate produces better decisions than a single model.*

**TradingGPT (Li et al., 2023)** — arXiv:2309.03736
Introduces layered memory architecture for trading agents. Short-term memory for immediate context, medium-term for recent patterns, long-term for historical lessons. CapitalFlow's knowledge base directly implements this three-layer memory model.

**FinMem (Yu et al., 2023)** — arXiv:2311.13743
Extends layered memory with character design — agents have defined personalities (risk-averse analyst vs aggressive trader) that produce more diverse, robust analysis. CapitalFlow uses this for its Bull/Bear researcher agents.

### 3.2 News-to-Market Causality

**GDELT + FinBERT Macro Alpha (2025)** — arXiv:2505.16136
The single most important empirical finding for this project: processing the GDELT worldwide news feed through FinBERT and building daily sentiment indices achieved Sharpe ratios of 5.87 on EUR/USD and 4.65 on USD/JPY over an 8-year out-of-sample period. This proves global news sentiment is a real, exploitable signal.

Key insight adopted: *Use GDELT (free, global, real-time) rather than single-country news APIs. Score mean tone, dispersion, and event impact separately.*

**Unscheduled News & Market Contagion (Zhang et al., 2025)**
Documents how unscheduled news events (wars, pandemics, political crises) create contagion patterns across markets that are fundamentally different from scheduled events (earnings, rate decisions). CapitalFlow distinguishes between scheduled and unscheduled event types.

### 3.3 Global Market Interconnection

**Time-Zone VAR Model (Wu et al., 2024)** — arXiv:2404.04335
Analyzes 36 national equity markets and proves that US market returns significantly predict returns in numerous non-US industrialized markets the next day. The time-zone sequencing (Asia opens first → Europe → Americas) creates a predictable information flow that can be modeled.

Key insight adopted: *Build a directed graph of market influence. Asia → Europe → Americas for equities. Model this sequence explicitly.*

**Market Contagion During Crises** — Research shows that during normal periods, markets have moderate correlation. During crises, correlations spike to near 1.0, destroying diversification. The system must detect regime shifts.

### 3.4 LLM Financial Intelligence

**MarketSenseAI 2.0 (Fatouros et al., 2025)**
Combines RAG with LLM agents to process SEC filings, earnings calls, and institutional reports alongside news and prices. Achieves superior portfolio performance by grounding LLM reasoning in retrievable facts.

Key insight adopted: *RAG over a structured financial knowledge base is more reliable than pure LLM reasoning from training data.*

**Large Investment Model / LIM (Guo & Shum, 2024)**
Foundation model approach: pre-train on vast financial data to learn universal market patterns, then fine-tune for specific assets. Shows that transfer learning from a global financial foundation outperforms asset-specific models.

**Temporal Relational Reasoning (Koa et al., 2024)**
Teaches LLMs to reason about time explicitly: "Given that Event A happened on Day 1 and Event B happened on Day 3, what is likely to happen by Day 7?" This temporal chain-of-thought is the core of CapitalFlow's event impact modeling.

### 3.5 The Honest Counterargument

**Can LLM Strategies Outperform the Market Long-Term? (Li et al., 2025)** — arXiv:2505.07078
Critical finding: most LLM trading backtests suffer from look-ahead bias (using today's S&P constituents to test yesterday's strategy) and survivorship bias. The FINSABER benchmark shows that many impressive LLM results do not hold under rigorous testing.

This paper is essential for building the system correctly — walk-forward validation only, no look-ahead bias, test on assets that existed at the time.

---

# 4. System Architecture

## The Four Intelligence Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: DECISION LAYER                                        │
│  Capital Allocation Engine → Move recommendations with costs   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  LAYER 3: REASONING LAYER                                       │
│  Multi-Agent Debate → Bull/Bear researchers → Trader agent     │
│  Knowledge Base Query → "What happened last time?"             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  LAYER 2: INTELLIGENCE LAYER                                    │
│  Analyst Agents: Technical | Fundamental | News | Macro | Cross│
│  ML Models: LSTM + RandomForest + GradientBoost ensemble       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│  LAYER 1: DATA LAYER                                            │
│  Price data (6 markets) | Global news (GDELT) | Macro (FRED)   │
│  Social sentiment | Earnings | Central bank statements         │
└─────────────────────────────────────────────────────────────────┘
```

## How Information Flows

```
World Event Happens
       │
       ▼
GDELT picks up news from 100+ countries in their language
       │
       ▼
News Analyst Agent: "Japan factory output dropped. Likely causes:
                    supply chain disruption, demand fall, or
                    one-time event?"
       │
       ├──► Knowledge Base Query: "What happened to commodities
       │    the last 5 times Japanese manufacturing fell?"
       │    → "Copper dropped avg 1.2% within 3 days (4/5 times)"
       │
       ▼
Cross-Market Agent: Time-zone sequencing
  "Japan is now closed. Europe opens in 2 hours.
   European copper miners will likely feel this first.
   US markets open 6 hours after that."
       │
       ▼
Technical Analyst: "Copper already showing RSI divergence.
                   BB bands compressing. Breakout likely."
       │
       ▼
Macro Agent: "Fed meeting next week. If copper drops,
              inflation expectations fall → Fed likely
              to stay on hold → dollar strengthens."
       │
       ▼
Bull Researcher ◄──── DEBATE ────► Bear Researcher
"Copper drop = buy     "One factory ≠ structural
 opportunity — short    shift. Hold until we see
 term dip before        PMI data. Too early."
 recovery"
       │
       ▼
Trader Agent: Decision with confidence score
       │
       ▼
Cost Engine: Calculate all transaction costs
       │
       ▼
Risk Manager: Position sizing (Kelly Criterion)
       │
       ▼
Capital Move Recommendation + Knowledge Base Update
```

---

# 5. Data Layer

## 5.1 Market Price Data

### Primary Source: Yahoo Finance (Free, No Key)
- All 6 markets: stocks, crypto, forex, commodities, bonds, real estate
- 30+ years of daily data available
- 1-minute intraday data for the last 60 days

### Secondary Source: Alpha Vantage (Free tier: 25 calls/day)
- Adjusted historical data with corporate actions
- Intraday data at 1m/5m/15m/30m/60m intervals
- Fundamental data (earnings, P/E, revenue)

### Tertiary Source: FRED (Federal Reserve Economic Data — Free)
- Macro indicators: CPI, GDP, unemployment, Fed funds rate
- Yield curve data (critical for bond market prediction)
- International economic data for 180+ countries

## 5.2 Global News — GDELT Project (Free, No Key)

This is the most underused data source in retail financial ML. GDELT monitors news from every country in 65 languages and updates every 15 minutes.

**What GDELT provides:**
- `GoldsteinScale` — quantifies how impactful an event is on a scale of -10 to +10
- `NumMentions` — how many sources picked up the story (proxy for importance)
- `AvgTone` — sentiment of the coverage
- Event location, actor country, event type

**Why this matters for global market prediction:**
A story about political instability in a copper-mining country, reported in Portuguese by Brazilian newspapers and picked up by 200 sources, with a Goldstein score of -6, is a strong signal for copper prices — even before any English-language financial media covers it.

**GDELT API endpoints:**
```
# Recent events (last 15 minutes)
http://api.gdeltproject.org/api/v1/events/query?query=copper+mining&mode=artlist

# Full event stream (updated every 15 min)
http://data.gdeltproject.org/events/YYYYMMDDHHMMSS.export.CSV.zip
```

## 5.3 Financial News — Multiple Sources

| Source | Coverage | Cost | Limit |
|--------|----------|------|-------|
| NewsAPI | English, global | Free | 100/day |
| GDELT | 65 languages, global | Free | Unlimited |
| Alpha Vantage News | Financial-specific | Free | 50/day |
| Reddit (PRAW) | Social sentiment | Free | 60/min |
| SEC EDGAR | US company filings | Free | Unlimited |
| ECB, BoJ, PBoC RSS | Central bank statements | Free | Unlimited |

## 5.4 Data We Collect Per Asset

For each of the 50+ assets across 6 markets, we collect and store:

```
Historical price record:
  - Daily OHLCV going back 20 years (where available)
  - Weekly and monthly aggregates

Technical indicators (computed, not fetched):
  - 25 indicators including RSI, MACD, Bollinger, ATR, OBV, momentum

Fundamental data (for stocks and REITs):
  - P/E ratio, P/B ratio, revenue growth, earnings surprises
  - Analyst consensus and revision history

Macro context at each historical point:
  - What was the Fed funds rate that day?
  - What was CPI, unemployment, GDP growth?
  - What was the yield curve shape?

News sentiment at each historical point:
  - GDELT average tone for relevant keywords, 3 days before
  - NewsAPI headline count and sentiment, 3 days before

Cross-market state:
  - What were the other 5 market categories doing that week?
  - What was the US Dollar Index (DXY)?
  - What was the VIX (fear gauge)?
```

---

# 6. Intelligence Layer — Multi-Agent Design

## The Agent Team

Inspired by TradingAgents (Xiao et al., 2025) but extended for global multi-market scope.

### Agent 1: Technical Analyst
**Role:** Pattern recognition on price data
**Tools:** 25 technical indicators, candlestick pattern detection, support/resistance levels
**Output:** Technical signal score (-1 to +1) with confidence, key price levels

**Specialization by market:**
- Stocks: focuses on volume confirmation, sector rotation
- Crypto: 24/7 markets require different indicator parameters (shorter windows)
- Forex: attention to session opens (London, New York, Tokyo) as key signal times
- Commodities: seasonal patterns (wheat harvests, heating oil demand cycles)
- Bonds: yield curve shape changes as primary signal

### Agent 2: Fundamental Analyst
**Role:** Assess intrinsic value vs current price
**Tools:** FRED macro data, earnings data, P/E ratios, revenue trends
**Output:** Fundamental score (overvalued / fairly valued / undervalued) with reasoning

**What it reads:**
- For stocks: P/E vs sector average, earnings growth, debt levels
- For forex: interest rate differential between countries, inflation differential
- For commodities: supply/demand balance, inventory levels (EIA for oil, USDA for grains)
- For bonds: real yield (nominal yield minus inflation), credit spreads
- For crypto: on-chain metrics (active addresses, transaction volume, miner revenue)
- For REITs: cap rates, vacancy rates, FFO growth

### Agent 3: News Analyst
**Role:** Translate news events into market impact scores
**Tools:** GDELT API, NewsAPI, FinBERT sentiment model
**Output:** News impact score per asset (-1 to +1), event classification, urgency level

**The key insight from research:**
News impact is not uniform. The same negative story has different impact depending on:
1. **Surprise factor** — Was this expected? (earnings: expected vs surprise)
2. **Source credibility** — Central bank statement vs Twitter rumor
3. **Geographic reach** — Local news vs global wire service
4. **Market phase** — Bull market absorbs bad news better than bear market
5. **Time-to-event** — News 3 days before expiry has different impact than 30 days before

The News Analyst scores each of these five dimensions separately.

### Agent 4: Macro Agent
**Role:** Global macroeconomic context and cross-market regime detection
**Tools:** FRED API, central bank feeds (Fed, ECB, BoJ, PBoC, BoE), yield curve data
**Output:** Macro regime classification + cross-market impact map

**Macro regimes detected:**
- Risk-On: equity and crypto favorable, bonds and gold less so
- Risk-Off: bonds and gold favorable, equities and crypto under pressure
- Inflationary: commodities and real assets favorable, long bonds unfavorable
- Deflationary: bonds favorable, commodities and crypto unfavorable
- Stagflationary: most assets unfavorable — cash and short-duration bonds
- Crisis: correlation spike, all assets move together, diversification fails

### Agent 5: Cross-Market Contagion Agent
**Role:** Model how events in one market propagate to others
**Tools:** Time-zone VAR model, correlation matrix, historical contagion database
**Output:** "If [market A] does X, then within [timeframe], [market B] will likely do Y with Z% probability"

**The time-zone sequence:**
```
Tokyo/Shanghai open (Asia session):
  → Sets tone for European commodity miners
  → Forex: JPY and AUD are leading indicators

London/Frankfurt open (European session):
  → Largest forex trading volume globally
  → Sets EUR/USD, GBP/USD for the day

New York open (US session):
  → Largest equity volume globally
  → DXY movement affects all dollar-denominated commodities

After US close:
  → Crypto markets (24/7) often see increased volume
  → Asian futures react to US close
```

### Agent 6: Bull Researcher + Agent 7: Bear Researcher
**Role:** Structured debate to stress-test the analysis
**Design:** Inspired by TradingAgents' researcher team design
**Process:**
1. Bull Researcher builds the strongest possible case for the trade
2. Bear Researcher finds every reason the trade could fail
3. They debate for N rounds (configurable: 1-3 rounds)
4. Debate transcript is summarized and stored in knowledge base
5. The quality of the debate itself is a signal — strong bear counter-arguments reduce confidence

### Agent 8: Trader Agent
**Role:** Synthesizes all analyst reports and debate into a final recommendation
**Process:**
1. Reads all 5 analyst reports
2. Reads debate summary from Bull/Bear researchers
3. Queries knowledge base: "What is the historical success rate of this pattern?"
4. Produces: signal direction, confidence score, time horizon, key risks
5. Passes to Cost Engine and Risk Manager before final output

---

# 7. Knowledge Base — The Learning Brain

## Architecture

The knowledge base is the most important part of the system. It is what makes CapitalFlow get smarter over time instead of making the same mistakes repeatedly.

### What Gets Stored After Every Prediction

```python
prediction_record = {
    # Context at prediction time
    "timestamp":            "2026-03-22T09:30:00Z",
    "asset":                "Gold",
    "market":               "commodities",

    # Full market state snapshot
    "market_state": {
        "price":            2,847.30,
        "rsi":              62.4,
        "macd":             +14.2,
        "bb_position":      0.71,
        "trend":            "bullish",
        "volatility_20d":   0.012,
    },

    # News context
    "news_context": {
        "gdelt_tone_3d":    -1.2,  # slightly negative global tone
        "top_headlines": [
            "Middle East tensions escalate as...",
            "Fed signals possible rate cut at...",
            "Gold demand surges in India ahead of..."
        ],
        "news_impact_score": +0.43,
    },

    # Macro context
    "macro_context": {
        "regime":           "Risk-Off",
        "fed_rate":         4.75,
        "dxy":              103.2,
        "vix":              18.4,
        "yield_curve":      "normal",
    },

    # Cross-market context
    "cross_market": {
        "spx_5d_return":    -1.2,
        "crypto_24h":       -3.1,
        "oil_5d":           +0.8,
        "usd_jpy":          148.2,
    },

    # What the agents decided
    "agent_signals": {
        "technical":        +0.7,
        "fundamental":      +0.5,
        "news":             +0.4,
        "macro":            +0.8,
        "cross_market":     +0.6,
    },
    "bull_argument":        "Fed pivot + geopolitical risk = classic gold setup...",
    "bear_argument":        "Overbought RSI + strong dollar = headwinds...",
    "final_signal":         "UP",
    "confidence":           0.74,
    "predicted_horizon":    "5 days",

    # What actually happened (filled in later)
    "actual_return_5d":     None,  # filled after 5 days
    "prediction_correct":   None,  # filled after 5 days
    "outcome_notes":        None,
}
```

### Storage Technology

**ChromaDB** (vector database) — for semantic similarity search
- Each prediction record is embedded as a vector
- Future predictions can query: "Find the 10 most similar market situations to now"
- Similarity is based on technical state + macro regime + news tone, not just dates

**SQLite / PostgreSQL** — for structured queries
- "What is my accuracy on Gold predictions when RSI > 60 and macro regime = Risk-Off?"
- "How often does a Japanese factory output drop lead to copper falling within 3 days?"
- "What was my average net profit on forex trades in Q1 2026?"

### How the Knowledge Base Is Used During Prediction

When making a new prediction for Gold:

```
1. Compute current market state vector

2. Query ChromaDB: "Find 10 most similar historical situations"
   → Returns: records from Oct 2023, Mar 2024, Nov 2024, Jan 2025...

3. Filter for situations where we have outcomes:
   → 7 of 10 have completed outcomes

4. Compute historical accuracy in this situation:
   → "In 6/7 similar situations, Gold rose within 5 days"
   → Average return: +1.8%
   → Average confidence was correct 86% of the time

5. Inject this into the Trader Agent's prompt:
   "Historical knowledge base shows: in 6 of 7 similar
   situations (Risk-Off regime, RSI 58-66, Fed pivot
   signals), Gold rose avg +1.8% within 5 days."

6. This grounds the LLM's reasoning in actual historical
   outcomes rather than general training knowledge.
```

### Knowledge Base Grows in 3 Ways

**Active learning:** When a prediction is made, the outcome is automatically recorded 5/10/20 days later by a background job that compares predicted direction to actual price movement.

**Manual annotation:** The system flags predictions with unusual outcomes (predicted UP, dropped 5%) and asks the user to annotate: "What did I miss? What context was available that wasn't captured?" These annotations are stored and weighted heavily in future similar situations.

**Cross-asset transfer:** A lesson learned on Gold often applies to Silver. A lesson on Bitcoin sometimes applies to tech stocks. The system maintains an asset similarity graph that transfers relevant lessons across related assets.

---

# 8. Global Market Interconnection Model

## The Time-Zone Chain

Research (Wu et al., 2024) confirms a clear information cascade from East to West. CapitalFlow models this explicitly.

```
Hour 0:  Tokyo Stock Exchange opens
         → Watch: Nikkei 225, Topix, USD/JPY
         → Leading signal for: Asian tech, Toyota suppliers,
           Japanese bond market

Hour 1:  Shanghai/Shenzhen opens
         → Watch: Shanghai Composite, CSI 300, CNY/USD
         → Leading signal for: Iron ore, copper, rare earths,
           any company with China revenue exposure

Hour 4:  Hong Kong opens (bridges Asia and West)
         → Watch: Hang Seng
         → Leading signal for: Luxury goods (LVMH), ports,
           shipping companies

Hour 7:  Frankfurt/Zurich opens (European session begins)
         → Watch: DAX, SMI, EUR/USD, Bund yields
         → Largest forex market opens. EUR/USD volume spikes.
         → Germany = proxy for global manufacturing health

Hour 8:  London opens (peak forex volume)
         → Watch: FTSE 100, GBP/USD, LIBOR successor rates
         → London sets commodity prices for the day
           (London Metal Exchange, gold fix at 10:30 AM London)

Hour 14: New York opens (equity dominance begins)
         → Watch: S&P 500, NASDAQ, VIX, US 10Y yield
         → Most important session for global risk appetite
         → DXY movement affects ALL dollar-denominated assets

Hour 18: US session closes, crypto takes over
         → Watch: BTC, ETH — often inverse to stock volatility
         → Quiet period for forex
         → Good time for macro positioning before Asia reopens
```

## Cross-Market Correlation Matrix

The system maintains a **dynamic** correlation matrix that updates daily. This is not a static table — correlations shift dramatically during different macro regimes.

**Normal regime correlations (approximate):**

| Asset | SPX | BTC | Gold | Oil | EUR/USD | US 10Y |
|-------|-----|-----|------|-----|---------|--------|
| SPX   | 1.0 | 0.6 | -0.2 | 0.3 | 0.1     | -0.5   |
| BTC   | 0.6 | 1.0 | 0.1  | 0.2 | 0.0     | -0.3   |
| Gold  | -0.2| 0.1 | 1.0  | 0.1 | 0.3     | -0.4   |
| Oil   | 0.3 | 0.2 | 0.1  | 1.0 | 0.2     | -0.1   |

**Crisis regime correlations (2020 COVID crash, approximately):**

| Asset | SPX | BTC | Gold | Oil | EUR/USD | US 10Y |
|-------|-----|-----|------|-----|---------|--------|
| SPX   | 1.0 | 0.8 | -0.6 | 0.7 | 0.4     | -0.7   |
| BTC   | 0.8 | 1.0 | -0.4 | 0.6 | 0.3     | -0.6   |

When crisis correlations replace normal correlations, diversification fails and the system shifts to capital preservation mode (bonds, gold, cash).

## Contagion Detection

The system continuously monitors for **contagion signals** — events that break historical patterns:

1. **Correlation spike detector:** If any two assets that normally have correlation < 0.3 suddenly show correlation > 0.7 over a 5-day rolling window, a contagion alert fires
2. **Volatility regime shift:** If VIX crosses 25, 30, or 40, the macro agent resets its regime classification
3. **Currency crisis signal:** If any major currency moves more than 3 standard deviations from its 20-day mean in one day, all correlated markets are flagged

---

# 9. Prediction Pipeline

## Step-by-Step Flow for One Asset Prediction

### Step 1: Data Ingestion (every 15 minutes)
```
Fetch from Yahoo Finance: latest OHLCV
Fetch from GDELT: news events mentioning the asset in last 1 hour
Fetch from FRED: any new macro releases today
Update technical indicators
Update cross-market state
```

### Step 2: Analyst Briefings (parallel, runs simultaneously)
```
Technical Analyst:   compute all 25 indicators → signal score
Fundamental Analyst: check earnings calendar, macro context → score
News Analyst:        GDELT + NewsAPI → sentiment + impact score
Macro Agent:         yield curve, DXY, VIX → regime + score
Cross-Market Agent:  correlation matrix, time-zone chain → score
```

### Step 3: Knowledge Base Query
```
Embed current state as vector
Query ChromaDB for top-10 similar historical situations
Calculate historical accuracy and average return in this situation
Format as context for Trader Agent
```

### Step 4: Bull/Bear Debate
```
Bull Researcher: build strongest case using all positive signals
Bear Researcher: find all risks, contradictions, bearish signals
Debate rounds: 1 (fast) or 3 (deep)
Summarize debate → key arguments for each side
```

### Step 5: Trader Decision
```
Read all analyst reports
Read debate summary
Read knowledge base historical context
Produce: direction, confidence, horizon, key risks
```

### Step 6: Cost Calculation
```
For every candidate destination market:
  - Broker fees (sell + buy)
  - Bid-ask spread both legs
  - Slippage estimate
  - FX conversion (if applicable)
  - Crypto gas fees (if applicable)
  - Wire fees (if custody changes)
  - Capital gains tax (based on holding period)
  → Net profit after all costs
  → Only proceed if net profit > minimum threshold
```

### Step 7: Position Sizing
```
Kelly Criterion adjusted for:
  - Market volatility regime
  - Asset-specific risk multiplier
  - Maximum position limit (default 25% of capital)
  - Portfolio-level drawdown protection
→ Recommended position size in USD
→ Stop-loss level
→ Take-profit target (2:1 reward-to-risk)
```

### Step 8: Output + Knowledge Base Update
```
Produce recommendation:
  - Move FROM [asset/market] TO [asset/market]
  - Amount: $X
  - Expected return: Y%
  - Total costs: $Z
  - Net profit: $W
  - Timing window: [minutes/hours/days/weeks]
  - Confidence: N%
  - Key risks: [list]
  - LLM explanation: [plain English]

Schedule outcome check:
  - At horizon date, fetch actual price
  - Record: was prediction correct?
  - Update knowledge base with outcome
```

---

# 10. Capital Allocation Engine

## The Optimization Problem

Given:
- Total available capital: $C
- Set of candidate trades: {T₁, T₂, ... Tₙ}
- Each trade has: expected return Rᵢ, cost Cᵢ, confidence Pᵢ, time horizon Hᵢ

Find the allocation {w₁, w₂, ... wₙ} that maximizes:
```
Σ wᵢ × (Rᵢ - Cᵢ) × Pᵢ

Subject to:
  Σ wᵢ = 1  (all capital deployed or held)
  wᵢ ≥ 0   (no short selling without explicit flag)
  wᵢ ≤ MAX_POSITION_PCT  (diversification constraint)
  Portfolio drawdown ≤ MAX_DRAWDOWN_PCT
```

This is a **quadratic programming problem** solved using CVXPY.

## Timing Decision

The system recommends timing based on three factors:

**Signal urgency** (from agents):
- Breaking news + strong sentiment + high confidence → act within hours
- Strong technical + moderate sentiment → act within 1-3 days
- Moderate signals across all agents → wait for confirmation, act in 1-2 weeks

**Market session timing:**
- Entering a position just before the high-volume session opens is suboptimal (wide spreads)
- Best entry: 30 minutes after session open (liquidity established)
- For forex: avoid entering during session overlap (spreads widen)
- For crypto: avoid entering during low-volume periods (manipulation risk)

**Cost timing:**
- Short-term capital gains are taxed at 37% vs 20% for long-term (US)
- If a position is 350 days old, waiting 15 more days saves 17% in taxes
- The cost engine models this and can recommend "hold 15 more days, save $X in tax"

---

# 11. Transaction Cost Intelligence

## Complete Cost Model

Every recommendation must pass the "net profit test" — costs are not an afterthought.

### Broker Commission Structure
```
Stocks (US):      0.05% per side   (Robinhood/Webull: $0, IBKR: 0.005/share)
Stocks (intl):    0.10-0.50%       (varies significantly by broker and country)
Crypto:           0.10% taker fee  (Binance/Coinbase standard)
Forex:            0.02% spread     (major pairs; exotic pairs much wider)
Commodities:      0.08%            (futures commission + exchange fee)
Bonds:            0.03%            (ETF: near zero; individual bonds: 0.1-0.5%)
REITs:            0.05%            (same as stocks, these are equity securities)
```

### Spread Cost Model
Spreads are not fixed — they widen during:
- Pre-market and after-hours (2-5x normal)
- News events and earnings (3-10x normal)
- Low liquidity periods (crypto at 3am, illiquid stocks)
- Market stress (VIX > 30: spreads can 5-10x)

The system uses VIX-adjusted spread estimates, not static percentages.

### Tax Optimization
```
Scenario: You hold an S&P 500 ETF for 350 days, up 15%
  Option A: Sell now
    Capital gain: $15,000
    Tax (short-term 37%): $5,550
    Net after tax: $9,450

  Option B: Wait 15 days (hold to day 365)
    Capital gain: $15,000 (same)
    Tax (long-term 20%): $3,000
    Net after tax: $12,000

  Tax optimization value: $2,550 saved by waiting 15 days
```

The cost engine computes this for every position and flags cases where waiting saves significant tax.

### FX Conversion Cascade
When moving money across markets involving different currencies:

```
Example: Moving from US stocks to Japanese bonds
  Step 1: Sell US stocks → receive USD
  Step 2: Convert USD to JPY (cost: ~0.25%)
  Step 3: Buy Japanese bonds denominated in JPY
  Step 4: (On exit) Convert JPY back to USD (cost: ~0.25%)
  Total FX cost: ~0.50% round trip

At $100,000: $500 in FX costs before any other fees
```

Some moves require multiple currency conversions (USD → EUR → CHF for Swiss bonds), compounding costs.

---

# 12. Risk Architecture

## Three Levels of Risk Protection

### Level 1: Position-Level Risk
- Stop-loss: set at 1.5× ATR below entry (adjusts for each asset's volatility)
- Take-profit: 2:1 reward-to-risk ratio (stops at 2% → take profit at 4%)
- Position size: Kelly Criterion × 0.5 (half-Kelly for safety)
- Maximum single position: 25% of available capital

### Level 2: Portfolio-Level Risk
- Maximum drawdown: 10% (if portfolio drops 10% from peak, all new trades halt)
- Concentration limit: no more than 40% in any one market category
- Correlation check: if two positions have correlation > 0.8, the second is reduced
- Volatility target: portfolio-level volatility kept below a configurable threshold

### Level 3: Regime Risk
- When macro regime = "Crisis" (VIX > 35 or correlation spike detected):
  - All new positions halted
  - Existing positions reviewed for survival
  - Capital shifted toward bonds and gold (defensive assets)
  - System enters "capital preservation mode"

## What the System Will Never Recommend

1. A trade where net profit (after ALL costs) is negative
2. A position larger than 25% of capital in a single asset
3. Any new trade when portfolio drawdown exceeds 10%
4. Entering a position during pre/post-market in a stock when spread > 0.5%
5. A crypto trade during periods of known exchange manipulation (exchange outages, abnormal volume)

---

# 13. Build Roadmap — Phase by Phase

## Phase 1: Foundation (Weeks 1-4)
**Goal:** Working system with real data and basic ML models

Deliverables:
- Data pipeline: Yahoo Finance + FRED + basic news
- Technical indicator computation (25 indicators)
- Basic LSTM + RF + GB ensemble
- Simple transaction cost calculator
- Command-line interface with results output

**Success metric:** System produces a prediction with net cost breakdown in < 60 seconds

## Phase 2: Multi-Agent Intelligence (Weeks 5-8)
**Goal:** Replace simple ML models with reasoning agents

Deliverables:
- Technical Analyst agent with LLM reasoning
- News Analyst agent with FinBERT + GDELT integration
- Macro Agent with FRED data
- Basic Bull/Bear debate (1 round)
- LangGraph orchestration of all agents

**Success metric:** Agents produce distinct, coherent analysis that disagrees with each other meaningfully

## Phase 3: Knowledge Base (Weeks 9-12)
**Goal:** System learns from its own predictions

Deliverables:
- ChromaDB vector store for prediction records
- Outcome recording background job
- Historical similarity query in prediction pipeline
- Knowledge base context injection into Trader Agent
- Accuracy tracking dashboard

**Success metric:** System can retrieve 5+ similar historical situations for any new prediction and its confidence calibration improves measurably

## Phase 4: Global Interconnection (Weeks 13-16)
**Goal:** Model cross-market and cross-country relationships

Deliverables:
- GDELT integration (global news in 65 languages)
- Time-zone sequence model
- Dynamic correlation matrix
- Cross-Market Contagion Agent
- Regime detection (Risk-On/Risk-Off/Crisis/Inflationary)

**Success metric:** System detects regime shifts within 24 hours of onset (tested on historical crises: 2020 COVID, 2022 rate shock)

## Phase 5: Production Polish (Weeks 17-20)
**Goal:** Reliable, fast, well-tested system

Deliverables:
- Walk-forward backtesting (no look-ahead bias)
- Performance analytics dashboard
- Full Streamlit UI
- Docker deployment
- Unit and integration tests

**Success metric:** Backtested Sharpe ratio > 1.5 on out-of-sample data for at least 3 of 6 markets

---

# 14. Technology Stack

## Core Infrastructure

| Component | Technology | Reason |
|-----------|-----------|--------|
| Language | Python 3.11 | Ecosystem for ML and finance |
| ML Framework | PyTorch | LSTM and neural models |
| Classical ML | scikit-learn | RF, GB, preprocessing |
| Agent Orchestration | LangGraph | Stateful multi-agent workflows |
| Vector Database | ChromaDB | Semantic knowledge base search |
| Relational Database | SQLite → PostgreSQL | Structured prediction records |
| Data Fetching | yfinance, pandas-datareader | Market data |
| Global News | GDELT API, NewsAPI | News ingestion |
| NLP/Sentiment | HuggingFace Transformers (FinBERT) | Financial sentiment |
| LLM Interface | LangChain | Unified LLM abstraction |
| Optimization | CVXPY | Portfolio optimization |
| Dashboard | Streamlit + Plotly | Interactive UI |
| Deployment | Docker + Docker Compose | Reproducible environment |

## LLM Support (via .env configuration)

| Provider | Best for | Model |
|----------|----------|-------|
| OpenAI | Best reasoning quality | gpt-4o |
| Anthropic | Long context, nuanced analysis | claude-3-5-sonnet |
| Google | Fast, cost-effective | gemini-1.5-pro |
| Groq | Ultra-fast inference | llama-3-70b |
| Ollama | Fully local, no API cost | llama3, mistral |

## Data Sources (all free tiers available)

| Source | Data Type | Key |
|--------|-----------|-----|
| Yahoo Finance | Price data | None needed |
| FRED | Macro data | Free registration |
| GDELT | Global news | None needed |
| NewsAPI | English news | Free (100/day) |
| Alpha Vantage | Price + fundamentals | Free (25/day) |
| Reddit (PRAW) | Social sentiment | Free OAuth |
| SEC EDGAR | US filings | None needed |

---

# 15. Key Papers & References

## Must-Read Papers (in priority order)

1. **TradingAgents** — Xiao et al. (2025), arXiv:2412.20138
   Multi-agent LLM trading framework. Direct architectural inspiration.

2. **Macro Alpha from GDELT News** — arXiv:2505.16136 (2025)
   Proof that global news sentiment from GDELT generates real trading alpha.

3. **Time-Zone VAR Model** — Wu et al. (2024), arXiv:2404.04335
   How global equity markets influence each other across time zones.

4. **TradingGPT / FinMem** — Li et al. (2023), arXiv:2309.03736 / Yu et al. (2023), arXiv:2311.13743
   Layered memory architecture for trading agents.

5. **MarketSenseAI 2.0** — Fatouros et al. (2025)
   RAG + LLM agents for multi-source financial analysis.

6. **ElliottAgents** — Chudziak & Wawer (2024/2025)
   Knowledge graph RAG for continuous learning in trading agents.

7. **FINSABER Benchmark** — Li et al. (2025), arXiv:2505.07078
   Why most LLM trading backtests are biased — how to build this right.

8. **News Contagion** — Zhang et al. (2025)
   How unscheduled events create different contagion patterns than scheduled ones.

## Key Datasets

- **GDELT Project** — gdeltproject.org — global news events, free
- **FRED** — fred.stlouisfed.org — US and international macro data, free
- **NASA CMAPSS** — if testing on sensor/time-series data
- **Quandl/Nasdaq Data Link** — financial data, some free tiers

## Important Warnings from Research

From FINSABER (Li et al., 2025):
- Always use walk-forward validation, never train-test split on the same time period
- Never use today's S&P 500 constituents as yesterday's investment universe (survivorship bias)
- Be skeptical of Sharpe ratios above 3 — likely a data issue
- Test across multiple time periods including crises, not just bull markets

---

*This document is the living specification for the CapitalFlow Intelligence System.*
*Last updated: March 2026*
*For research and educational purposes only. Not financial advice.*
