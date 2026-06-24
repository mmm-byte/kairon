# Document 01 — Product Vision
## What Kairon Is, Who It's For, What Problem It Solves

---

## 1. The One-Line Description

Kairon is a multi-market financial intelligence platform that watches 6 global markets simultaneously, uses a team of AI agents to identify the best capital move, calculates exact net profit after every single cost, and tells you precisely what to buy, what to sell, when to act, and when to wait.

---

## 2. The Problem It Solves

### Problem 1: Markets are connected but tools treat them as isolated
When oil prices spike in the Middle East, gold rises, the dollar strengthens, emerging market currencies fall, and bond yields move — all within hours. Yet every trading tool shows you one market at a time. Kairon watches all 6 simultaneously and maps how they influence each other.

### Problem 2: Hidden costs destroy profits
A trade that looks like +3% return actually delivers +1.8% after broker fees, spread, slippage, gas fees, wire transfer, and capital gains tax. Most tools show you the gross return. Kairon shows you what you actually keep in your pocket.

### Problem 3: AI systems are black boxes
Current AI trading tools give you a signal — BUY or SELL — with no explanation. You cannot trust something you do not understand. Kairon shows you exactly which agent voted which way, what news they read, what historical patterns they found, and why the system reached its conclusion.

### Problem 4: Systems do not learn from experience
Every time a prediction is made, win or lose, that outcome is valuable knowledge. Most systems discard it. Kairon stores every prediction, records every outcome, and uses that history to make better predictions over time.

### Problem 5: Global news moves markets before price data reflects it
When a war starts, when a central bank makes a surprise announcement, when a supply chain disrupts — the price reaction comes minutes or hours later. By then it is too late. Kairon reads global news in 65 languages via GDELT and translates events into market signals before price data catches up.

---

## 3. Who Is This For

### Primary user: Active investor / serious trader
- Has capital across multiple asset classes (stocks, crypto, some commodities)
- Spends 1-3 hours per week actively managing their portfolio
- Understands markets at an intermediate level
- Wants data-driven decisions, not gut feelings
- Frustrated that tools show signals but not reasoning or real costs

### Secondary user: Learning investor
- Wants to understand how professional analysis works
- Uses Kairon in simulation mode to learn without risk
- Studies why the system recommends what it recommends
- Builds knowledge of market relationships over time

### What Kairon is NOT for:
- High-frequency traders (Kairon operates on days-to-weeks time horizons)
- Fully automated trading (every recommendation requires human approval)
- Get-rich-quick speculation (the system is conservative and risk-aware)

---

## 4. The Core Promise

> "Tell me what to buy, what to sell, when to act, and what it will actually cost me — and show me why."

Every feature of Kairon serves this promise. If a feature does not directly help answer one of those four questions, it does not belong in the product.

---

## 5. Simulation Mode — The Critical Design Decision

**Kairon stores zero real user financial data.**

This is not a limitation — it is a deliberate design choice and a competitive advantage:

- No user accounts required to use the core product
- No liability for real trading decisions
- No regulatory complexity (not acting as a financial advisor)
- Users can explore freely without risk
- The intelligence is real; the portfolio is simulated

Users set a simulated starting capital (default: $100,000). They can:
- Switch between 4 market regimes (calm, fear, inflation, crisis)
- See how recommendations change in each regime
- Execute moves in simulation to track hypothetical performance
- Use the cost calculator on any trade they are actually considering

The platform uses real market data patterns for prices, real news sentiment from GDELT, and real analytical logic — everything is genuine except the capital being risked.

---

## 6. What Makes Kairon Different

| Feature | Kairon | Bloomberg Terminal | Typical Trading App | AI Signal Tools |
|---------|--------|-------------------|---------------------|-----------------|
| 6 markets simultaneously | Yes | Yes ($24k/year) | No | No |
| Real costs before signal | Yes | No | No | No |
| Explains AI reasoning | Yes | N/A | N/A | No |
| Learns from past predictions | Yes | No | No | No |
| Global news in 65 languages | Yes | Yes ($24k/year) | No | No |
| Tax optimization alerts | Yes | No | No | No |
| Regime-aware analysis | Yes | Partial | No | No |
| Zero user data stored | Yes | No | No | No |
| Free to use | Yes | No | Mostly | Mostly |

---

## 7. The 6 Markets Covered

| Market | What It Includes | Why It Matters |
|--------|-----------------|----------------|
| Stocks | US equities, ETFs, major indices | Largest asset class globally |
| Crypto | BTC, ETH, SOL, BNB, XRP | 24/7 market, high volatility, growing institutional adoption |
| Forex | EUR/USD, GBP/USD, USD/JPY, AUD/USD | Largest market in the world by volume |
| Commodities | Gold, Silver, Oil, Natural Gas, Wheat, Copper | Real assets, inflation hedge, geopolitical proxy |
| Bonds | US Treasuries (2Y, 10Y, 30Y), corporate bond ETFs | Safe haven, rate cycle indicator |
| Real Estate | REITs, real estate ETFs | Income + inflation hedge |

---

## 8. The 5 User-Facing Screens

| Screen | Purpose | Primary Action |
|--------|---------|----------------|
| Mission Control | Global overview — start here every day | See what the world is telling you right now |
| Move Recommendations | Where profits come from | Decide which moves to execute |
| Agent Intelligence | Transparency — understand the why | Deep-dive into any recommendation |
| Knowledge Base | Learning — system improves over time | Review accuracy, see lessons learned |
| Cost Calculator | Never get surprised by fees | Calculate net profit before any trade |

---

## 9. Revenue Model (Future)

Kairon v1.0 is free. Future monetization options:

- **Kairon Pro** — real-time GDELT news, more assets per market, portfolio tracking
- **Kairon API** — developers build apps on top of the intelligence layer
- **Kairon Advisor** — white-label version for financial advisors

None of these require storing user financial data. The simulation model scales to all tiers.

---

## 10. Success Metrics

| Metric | Target at Launch | Target at 6 Months |
|--------|-----------------|-------------------|
| KB accuracy (overall) | 65%+ | 75%+ |
| Signal freshness | Updates every 15 min | Updates every 5 min |
| Cost calculation accuracy | Within 5% of real costs | Within 2% of real costs |
| Screens covered | 5 | 5 + mobile |
| Markets covered | 6 | 6 + 2 (emerging markets) |
| Assets tracked | 30 | 60 |

---

*Document 01 — Product Vision*
*Requires approval before proceeding to build*
