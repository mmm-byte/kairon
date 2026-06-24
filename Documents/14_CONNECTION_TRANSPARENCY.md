# Document 14 — Connection Transparency
## How Kairon Connects Information — The Full Information Web

---

## 1. The Problem This Document Solves

When Kairon says "BUY Gold", a user should be able to ask:
- Where did you get that signal from?
- What news are you reading?
- What is the connection between that news and Gold?
- How did you connect the dollar weakening to gold rising?
- What historical pattern are you matching this to?
- Why is this situation different from last month when you also said buy but it dropped?

This document specifies **how the connection map is built, stored, and displayed** so users can see every thread of reasoning the system pulled together.

---

## 2. The Connection Graph

Every prediction is backed by a directed graph of connections. Each node is a piece of information. Each edge is a causal relationship with a weight (strength) and a direction (how the relationship flows).

### Example: Gold BUY Signal — Full Connection Graph

```
WORLD EVENT
"Federal Reserve signals rate hold"
[GDELT: 1,240 mentions · Tone: -1.8 · Goldstein: -3.2]
         │
         │ weakens rate hike expectations (strength: 0.82)
         ▼
REAL YIELD IMPACT
US 10Y real yield drops from +1.4% to +1.1%
[FRED: DGS10 - T10YIE]
         │
         │ lower real yield historically benefits gold (strength: 0.74)
         ├─────────────────────────────────────────────────────────►
         │                                                          │
         ▼                                                          ▼
DOLLAR WEAKENS                                            GOLD PRICE RISES
DXY falls from 104.8 to 103.9                           Historical: when real
[Yahoo Finance: DXY=X]                                  yield drops 0.3%+,
         │                                              gold rises avg 1.8%
         │ inverse relationship                         in 5 days (KB: 31 obs)
         │ (strength: -0.68)
         ▼
GOLD BENEFITS FROM WEAK DOLLAR
Gold priced in USD — dollar weakness
makes gold cheaper for foreign buyers → demand rises
         │
         │ demand signal confirms price move
         ▼
TECHNICAL CONFIRMATION
RSI: 61 (strong, not overbought)
MACD: expanding (momentum increasing)
Volume: 1.4× average (institutional buying)
Price: above SMA10, SMA20, SMA50
         │
         │ pattern match: 94% similarity
         ▼
KNOWLEDGE BASE MATCH
Found 7 similar situations:
  - Oct 2023: Fed pause + DXY 104 → Gold +2.3% in 5 days ✓
  - Mar 2024: Rate hold signal → Gold +1.8% in 5 days ✓
  - Jul 2024: Fed dovish pivot → Gold +3.1% in 5 days ✓
  - Nov 2024: Hold + weak dollar → Gold +0.9% in 5 days ✓
  - Jan 2025: Rate hold + RSI 58 → Gold -0.4% in 5 days ✗ (CPI surprise)
  - Feb 2025: Hold + GDELT neg → Gold +1.6% in 5 days ✓
  - Mar 2025: Similar setup → Gold +2.1% in 5 days ✓
  KB accuracy in this exact setup: 6/7 = 86%
         │
         ▼
CROSS-MARKET CONFIRMATION
USD/JPY falling (risk-off confirmed)
Stocks slightly down (capital rotating to safe havens)
Silver also rising (confirms broad precious metals demand)
         │
         ▼
FINAL SIGNAL: BUY GOLD
Confidence: 82% · Expected: +2.1% in 5 days
Source threads: 6 independent signals all pointing UP
```

---

## 3. The Connection Map Screen

This is a new screen (Screen 6) — **Connection Map & Prediction Transparency**.

### Layout
```
┌──────────────────────────────────────────────────────────────────┐
│  Connection Map — Gold BUY Signal                               │
│  "Why is Kairon saying buy Gold?"                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Interactive node graph]                                        │
│                                                                  │
│  Nodes:  World events · Macro indicators · Price signals        │
│          KB matches · Agent conclusions · Final signal           │
│                                                                  │
│  Edges:  Causal relationships with strength weights             │
│          Thick = strong connection · Thin = weak connection      │
│          Green = positive influence · Red = negative influence   │
│                                                                  │
│  Click any node → see the raw data behind it                    │
│  Click any edge → see the relationship explained in plain words │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Information Sources Panel (left)                               │
│  ─────────────────────────────                                  │
│  ● GDELT news (847 events, 3 days)                              │
│  ● Yahoo Finance (Gold price history)                           │
│  ● FRED (Fed funds rate, real yield)                            │
│  ● NewsAPI (12 bullish headlines)                               │
│  ● Reddit (neutral sentiment)                                   │
│  ● Knowledge Base (7 similar situations)                        │
│  ● Technical indicators (25 computed)                           │
│                                                                  │
│  Signal Strength Panel (right)                                  │
│  ──────────────────────────────                                  │
│  From world events:        +0.42                                │
│  From macro indicators:    +0.82                                │
│  From price patterns:      +0.78                                │
│  From KB history:          +0.86 (6/7)                         │
│  From cross-market:        +0.58                                │
│  ────────────────────────────                                   │
│  FUSED SIGNAL:             +0.81 → BUY                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Node Types in the Graph

| Node Type | Color | Shape | What It Represents |
|-----------|-------|-------|-------------------|
| World Event | Blue | Circle | A GDELT news event |
| News Headline | Blue | Rectangle | A NewsAPI headline |
| Macro Indicator | Amber | Diamond | A FRED data point |
| Price Signal | Green/Red | Circle | A technical indicator reading |
| KB Match | Purple | Hexagon | A historical similar situation |
| Agent Conclusion | White | Rounded rect | What one agent decided |
| Cross-Market | Teal | Triangle | A signal from another market |
| Final Signal | Large circle | BUY/SELL/HOLD | The final decision |

### Edge Types

| Edge Type | Style | What It Means |
|-----------|-------|---------------|
| Strong positive | Thick green solid | Direct causal positive relationship |
| Weak positive | Thin green dashed | Correlation, not direct cause |
| Strong negative | Thick red solid | Direct inverse relationship |
| Weak negative | Thin red dashed | Weak inverse correlation |
| Uncertainty | Gray dashed | Unclear direction |

---

## 4. Information Source Tracing

Every piece of information in the system carries a **provenance tag** — where it came from, when it was fetched, and how confident we are in it.

```python
class Signal:
    value:      float        # -1.0 to +1.0
    direction:  str          # UP | DOWN | NEUTRAL
    confidence: float        # 0.0 to 1.0
    source:     str          # "GDELT" | "FRED" | "Yahoo" | "NewsAPI" | "KB"
    source_url: str          # direct link to the source (if available)
    raw_data:   dict         # the actual raw data used
    fetched_at: datetime     # when was this data fetched
    staleness:  str          # "fresh" | "cached_15m" | "cached_1h" | "stale"
    asset:      str          # which asset this signal refers to
    agent:      str          # which agent produced this signal
    reasoning:  str          # plain English explanation of the connection
```

When user clicks any node in the connection graph, they see all of this:

```
Node: "Fed Rate Hold Signal"
──────────────────────────────
Source:      GDELT Project
Fetched:     2 minutes ago (fresh)
Raw event:   "United States" made "statement" to "Federal Reserve"
             GoldsteinScale: -1.2 · NumMentions: 1,240 · AvgTone: -8.4

Related headlines (NewsAPI):
  - "Fed signals rates to remain elevated" — Reuters, 3h ago
  - "Powell: No cuts until inflation sustainably below 2%" — FT, 4h ago
  - "Rate hold expected at March meeting" — Bloomberg, 5h ago

What this means for Gold:
  Lower rate cut expectations → real yields stay elevated → normally
  negative for gold. BUT: current reading is -1.2 Goldstein (mild concern)
  not -6.0 (crisis). Combined with DXY weakness, the net effect is
  slightly positive for gold as inflation hedge demand rises.

Confidence in this signal: 71%
Agent that used this: News Analyst, Macro Agent
```

---

## 5. The "Why Is It Rising?" Explanation

A dedicated panel on Screen 6 answers the question: **"What exactly is pushing this asset up (or down)?"**

This shows a ranked list of contributing factors, each with:
- The factor name
- The raw evidence behind it
- The strength of its contribution
- Whether it is a new signal or a continuation of an existing trend

```
Why is Gold rising? — Contributing factors (ranked by strength)

#1  Macro regime shift to Risk-Off         contribution: +0.34
    Evidence: VIX rose from 12.4 to 14.2 over 7 days
              Yield curve flattened 8bps this week
              Investment-grade credit spreads widened 12bps
    This is the strongest signal. Risk-Off regimes historically
    produce the largest Gold moves.

#2  Real yield declining                   contribution: +0.27
    Evidence: 10Y nominal yield: 4.21% (unchanged)
              10Y inflation expectations: 2.34% (up from 2.18%)
              Real yield = 4.21 - 2.34 = 1.87% (down from 2.03%)
    Lower real yields reduce the opportunity cost of holding gold.
    Gold does not pay interest — when real yields fall, gold becomes
    relatively more attractive.

#3  Technical momentum building            contribution: +0.22
    Evidence: Price crossed above SMA50 on Day 3
              MACD histogram positive for 4 consecutive days
              Volume 1.4× 20-day average on up days vs 0.8× on down days
              RSI at 61 — momentum present but not overbought
    Chart confirms what macro is saying. Volume confirmation is key.

#4  Global safe haven demand (GDELT)       contribution: +0.14
    Evidence: Geopolitical tension events: 847 mentions in 72h
              Average GoldsteinScale of those events: -4.2
              Events concentrated in: Middle East, Eastern Europe
    Geopolitical uncertainty historically drives safe haven flows.
    Gold benefits from uncertainty even when the direct economic
    impact is unclear.

#5  DXY weakness                           contribution: +0.09
    Evidence: DXY moved from 104.8 to 103.9 (-0.86%)
              EUR/USD rose 0.6%, JPY strengthened
    Mild headwind currently (DXY still above 103.5 support).
    Would be a stronger signal if DXY breaks below 103.

NEGATIVE FACTORS (working against Gold):

-1  DXY still above 103.5 support         contribution: -0.08
    If DXY holds here, dollar strength limits Gold upside.

-2  Upcoming CPI release (2 days)          contribution: -0.06
    CPI above 3.5% would reduce rate cut hopes → Gold headwind.
    Creates uncertainty until the release.

NET SIGNAL: +0.58 (positive factors dominate)
```

---

## 6. How Connections Between Markets Are Shown

The cross-market connection panel shows live influence arrows between all 6 markets.

```
Current Cross-Market Influence Map (right now)

FOREX            COMMODITIES      BONDS
EUR/USD ─────►  Gold             US 10Y ─────────────►
  -0.6%           +1.2%            4.21%              Gold
  (DXY strong)    (rising)         (stable)         (benefits from
       │                                              stable rates)
       ▼
   DXY strong ──────────────────────────────────────► Gold headwind
   (partially                                          -0.08 weight
   offsets)

STOCKS           CRYPTO           REAL ESTATE
S&P 500 ───────► Bitcoin ◄──────── VIX
  +0.4%           +2.8%           14.2
  (mild risk-on)  (risk-on        (low fear =
                  momentum)       risk assets OK)

ASIA SESSION (3h ago):
  Nikkei +0.8% → European manufacturing positive → DAX +0.6%
  Shanghai -0.3% → Copper mild pressure → Commodity miners cautious

GDELT NEWS FLOWS (72h):
  Middle East tension ──► Gold safe haven demand ──► Gold BUY signal
  China PMI weak ────────► Copper bearish signal ───► Commodities mixed
  Fed statement ─────────► USD reaction ─────────────► Gold + Bonds move
```

---

## 7. Prediction Confidence Decomposition

When the system says "82% confidence", users deserve to know what that 82% is made of.

```
Confidence decomposition for: Gold BUY (82%)
────────────────────────────────────────────

Base model accuracy (Technical + Fundamental + News):
  Historical accuracy in similar setups: 68%

Knowledge base adjustment:
  Found 7 similar situations, 6 correct (86%)
  Adjustment: +8% → 76%

Agreement bonus:
  5/5 agents bullish (full agreement)
  Adjustment: +4% → 80%

News freshness:
  GDELT data is 8 minutes old (fresh)
  NewsAPI data is 22 minutes old (fresh)
  No staleness penalty → 80%

Regime alignment bonus:
  Risk-Off regime historically correlates 78% with Gold success
  Adjustment: +2% → 82%

Final confidence: 82%

What would increase confidence:
  - DXY breaking below 103.5 → +4%
  - CPI print below 3.0% on Friday → +6%
  - More central banks confirming dovish stance → +3%

What would decrease confidence:
  - CPI above 3.5% → -15%
  - DXY breakout above 105 → -10%
  - VIX dropping below 12 (market too calm, risk-on hurts Gold) → -8%
```

---

## 8. Historical Accuracy Tracking Per Connection Type

The system tracks not just overall accuracy but accuracy **broken down by what type of signal drove the prediction**:

| Connection Type | Predictions Using It | Accuracy | Avg Return When Correct |
|----------------|---------------------|----------|------------------------|
| GDELT news → Gold | 31 | 77% | +2.1% |
| Fed statement → bonds | 18 | 83% | +1.3% |
| DXY fall → Gold | 24 | 71% | +1.6% |
| VIX spike → safe havens | 15 | 80% | +2.4% |
| Technical breakout → crypto | 22 | 64% | +3.8% |
| China PMI → copper | 19 | 68% | -1.2% |
| Yield curve inversion → recession | 8 | 75% | +4.1% (bonds) |

This tells users which types of connections are most reliable — and which to treat with more skepticism.

---

## 9. The "Show Your Work" Button

On every move recommendation card, a "Show your work ↗" button opens the full connection map for that specific prediction. The map shows:

1. Every data source consulted
2. Every connection made between data points
3. Every agent's reasoning
4. The KB historical matches
5. The confidence decomposition
6. What would change the prediction

This is what turns Kairon from a black box into a transparent reasoning partner.

---

*Document 14 — Connection Transparency*
*Requires approval before proceeding to build*
