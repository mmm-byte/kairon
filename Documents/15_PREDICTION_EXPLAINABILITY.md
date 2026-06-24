# Document 15 — Prediction Explainability
## How the Model Understands What Is Increasing and Why

---

## 1. The Core Question This Document Answers

When Kairon predicts Gold will rise, you deserve to know:
1. What signals told it that?
2. How did it weight those signals?
3. What is the causal chain from raw data to prediction?
4. What patterns from history match this situation?
5. What would have to be true for it to be wrong?
6. How certain is it, and where does that certainty come from?

This document specifies the full explainability pipeline — every step from raw data to final prediction, made visible to the user.

---

## 2. The Five Layers of Understanding

Kairon builds its understanding in five sequential layers. Each layer adds context to the previous one.

```
Layer 1: RAW SIGNALS
What is the data saying right now?
─────────────────────────────────────────────────────────────
Gold price: $2,847.30 (+1.2% today)
RSI: 61.4
MACD: +14.2 (expanding)
GDELT 72h tone: +0.42 (847 mentions)
Fed statement AvgTone: -8.4 (dovish leaning)
DXY: 103.9 (-0.86% today)
VIX: 14.2 (low, risk-on)
US 10Y real yield: 1.87% (falling)

         │
         ▼

Layer 2: PATTERN RECOGNITION
What do these signals mean when seen together?
─────────────────────────────────────────────────────────────
RSI 61 + MACD expanding + Volume 1.4× = TECHNICAL BREAKOUT PATTERN
DXY falling + real yield falling = DOLLAR WEAKNESS PATTERN
GDELT -8.4 tone + 847 mentions = MODERATE GEOPOLITICAL CONCERN PATTERN
VIX 14.2 + VIX rising (from 12.4) = EARLY RISK-OFF SIGNAL

         │
         ▼

Layer 3: CROSS-SIGNAL CORRELATION
How do these patterns reinforce or contradict each other?
─────────────────────────────────────────────────────────────
Technical breakout + Dollar weakness AGREE → both favor Gold
Geopolitical concern + Early risk-off AGREE → both favor safe havens
VIX still low (14.2) PARTIALLY CONTRADICTS → not full risk-off yet
All four patterns consistent in direction → HIGH CONVICTION

         │
         ▼

Layer 4: HISTORICAL PRECEDENT
When has this combination appeared before, and what happened?
─────────────────────────────────────────────────────────────
KB found 7 similar situations (cosine similarity > 0.85):
  6 of 7: Gold rose within 5 days (avg +2.1%)
  1 of 7: Gold fell (CPI surprise that week — external shock)
  Pattern reliability: 86% in this exact combination

         │
         ▼

Layer 5: FORWARD PROJECTION
Given all of the above, what is likely to happen next?
─────────────────────────────────────────────────────────────
Base case (82% probability): Gold rises 1.8-2.5% in 5 days
  Driver: DXY continues weak, real yields stable/falling
  Trigger: Institutional buyers confirmed by volume

Bear case (18% probability): Gold falls or stays flat
  Driver: CPI surprise → rate cut expectations reset → Gold loses catalyst
  Trigger: CPI > 3.5% on Friday
```

---

## 3. The Signal Flow Diagram (shown to user)

This is displayed visually on Screen 6 as an animated flow diagram. Each step lights up as data flows through it.

```
DATA SOURCES              PROCESSING                OUTPUT
────────────             ────────────              ────────

Yahoo Finance ──────►  Technical           ─────►
(OHLCV daily)          Analyst: +0.78             │
                        ↑ RSI 61                  │
GDELT News ────────►  News Analyst         ─────►  │
(847 events)            Agent: +0.71              │  SIGNAL
                        ↑ Tone +0.42              │  FUSION
FRED (FOMC, ───────►  Macro Agent         ─────►  │
yield curve)            Agent: +0.82              │   +0.81
                        ↑ Risk-Off regime         │   ──────
NewsAPI ───────────►  Fundamental         ─────►  │   BUY
(12 headlines)          Analyst: +0.65            │
                        ↑ Real yield low          │
Cross-market ──────►  Cross-Market        ─────►  │
(DXY, VIX)             Agent: +0.58              │
                        ↑ DXY weak               │
                                                  │
Knowledge Base ────►  Historical          ─────►  │
(7 matches)            Match: 86%                │
                        ↑ 6/7 correct             │
                                                  ▼
                       Bull/Bear Debate          COST
                       Bull: +0.68       ────►  ENGINE
                       Bear: +0.42              ↓
                                               NET
                                              PROFIT
                                               ↓
                                            DECISION
```

---

## 4. What "Understanding What Is Increasing" Actually Means

The system does not just detect that Gold is rising. It identifies **which force is the primary driver**, because different drivers have different implications for how long the move lasts and how far it goes.

### Force Classification System

Every BUY signal is tagged with its primary force:

| Force Type | What It Is | Duration | Example |
|-----------|-----------|----------|---------|
| Macro shift | Regime change, central bank pivot | Weeks to months | Fed pivots dovish → Gold rises for months |
| News catalyst | Single event creates sudden demand | Hours to days | War breaks out → Gold spikes, then normalizes |
| Technical breakout | Price breaks key level with volume | Days to weeks | Breaks $2,800 resistance with 1.5× volume |
| Currency weakness | Dollar falls, Gold auto-rises | Days to weeks | DXY drops → Gold inverse relationship |
| Safe haven flow | Fear drives capital into gold | Hours to days | VIX spikes → Gold and bonds rise together |
| Inflation hedge | CPI data drives inflation expectations | Weeks | CPI miss → gold as inflation protection |
| Supply shock | Mining disruption, export ban | Variable | Mine strike → supply constrained |
| Seasonal demand | Jewelry, harvest seasons | Weeks | India wedding season → physical demand |

### Why This Matters for the User

If Gold is rising because of a **macro shift** (Fed pivots), the move could last months — you hold longer and size up.

If Gold is rising because of a **news catalyst** (single geopolitical event), the move might last 24-48 hours — you enter fast and exit fast.

The system explicitly tells the user which type of force is driving each move.

---

## 5. The Increasing/Decreasing Indicator Panel

A dedicated panel on Screen 6 shows, for every asset being watched:

```
What is pushing GOLD right now?

INCREASING FORCES (pushing price up)       DECREASING FORCES (pushing price down)
──────────────────────────────────        ──────────────────────────────────────
↑ Real yield declining      +0.27        ↓ DXY still above 103.5     -0.08
  FRED: 1.87% (was 2.03%)                  DXY: 103.9 (not broken yet)

↑ Risk-Off macro regime     +0.34        ↓ CPI uncertainty ahead     -0.06
  VIX rising 7-day trend                   Release in 2 days

↑ Geopolitical demand       +0.14        ↓ RSI approaching 65         -0.04
  GDELT: 847 events, -4.2 avg               Mild overbought caution

↑ Technical breakout        +0.22
  Above all 3 MAs, MACD expanding

↑ Institutional buying      +0.11
  Volume 1.4× average on up days

────────────────────────                 ────────────────────────────
TOTAL UPWARD FORCE:  +1.08               TOTAL DOWNWARD FORCE: -0.18
──────────────────────────────────────────────────────────────────
NET FORCE: +0.90 → STRONG BUY
```

This panel updates every 15 minutes as new data flows in. Users can watch the forces shift in real time.

---

## 6. Causal Chain Explanation (Plain English)

For every prediction, the LLM generates a causal chain explanation — a step-by-step narrative of how the world got to this prediction.

```
CAUSAL CHAIN: Why Gold is likely to rise

Step 1: The Federal Reserve signaled it will hold rates steady.
This matters because when rates stay put, the real return on
holding cash or bonds does not improve. Investors start looking
for alternatives.

Step 2: Because of the rate hold signal, the US Dollar weakened.
The dollar fell 0.86% today (DXY: 104.8 → 103.9). Since Gold
is priced in dollars, a weaker dollar makes Gold cheaper for
buyers using euros, yen, or yuan. More buyers → higher price.

Step 3: Real yields are falling.
The 10-year Treasury yield stayed at 4.21%, but inflation
expectations rose from 2.18% to 2.34%. This means the REAL
return (yield minus inflation) fell from 2.03% to 1.87%.
Gold pays no interest — so when real returns elsewhere fall,
Gold becomes relatively more attractive.

Step 4: Geopolitical tensions are elevated.
GDELT detected 847 news events about geopolitical instability
over the past 72 hours, with an average Goldstein score of -4.2
(moderately negative). This creates background safe-haven
demand — investors want insurance.

Step 5: The technical picture confirms the macro picture.
Price is above all three moving averages. MACD is expanding.
Volume on up days is 1.4× average. These patterns say
institutional money is flowing IN, not out.

Step 6: History says this combination works.
The knowledge base found 7 situations where these same conditions
appeared together. In 6 of those 7 cases, Gold rose an average
of +2.1% within 5 days.

Conclusion: Four independent reasons are all pointing in the same
direction. The single risk that could break this thesis is a
surprise CPI print on Friday — if inflation re-accelerates, the
Fed story changes.
```

---

## 7. The Contradiction Detector

The system actively looks for cases where signals contradict each other and surfaces them explicitly.

```
CONTRADICTIONS DETECTED for Gold BUY:

Contradiction #1 (Minor):
  Technical Analyst says: RSI at 61 → approaching overbought territory
  Macro Agent says: Risk-Off regime historically drives Gold higher
  These are in tension: technicals say caution, macro says charge.
  Resolution: Macro regime wins over short-term RSI in Gold's case
  (KB confirms: RSI 60-65 + Risk-Off → Gold still rises 79% of the time)
  Net impact on confidence: -2%

Contradiction #2 (Significant):
  News Analyst says: GDELT tone positive (+0.42) → bullish
  DXY signal says: Dollar at 103.9, still above 103.5 support
  These are in tension: news is bullish but DXY could strengthen.
  Resolution: If DXY bounces from 103.5, it would cap Gold's upside.
  Net impact on confidence: -5%
  User action: Set alert for DXY at 103.5 (below = Gold breakout,
               above = Gold capped)

No major contradictions found. Confidence maintained at 82%.
```

---

## 8. The Sensitivity Analysis Panel

Users can ask: "What would have to change for this prediction to flip?"

```
Sensitivity Analysis: Gold BUY → WHAT WOULD FLIP IT TO SELL?

If ANY of these happen, re-run analysis immediately:

Critical flips (would flip to SELL):
  ● CPI > 3.5% on Friday          Impact: -25% confidence → likely AVOID
  ● DXY breaks ABOVE 105           Impact: -18% confidence → HOLD
  ● VIX drops below 12             Impact: -12% confidence → weaker BUY
  ● Fed official says "hike"        Impact: -30% confidence → likely SELL

Would strengthen BUY:
  ● DXY breaks BELOW 103.5         Impact: +8% confidence
  ● CPI < 3.0% on Friday           Impact: +12% confidence
  ● VIX rises above 18             Impact: +6% confidence (more risk-off)
  ● Central bank gold purchase news Impact: +10% confidence

Would change timing (not direction):
  ● Volume drops below 0.8× average → Move slower, wait for re-entry
  ● MACD histogram starts contracting → Consider reducing position size

[Set Alerts for These Conditions →]
```

---

## 9. How the Model Learns "What Is Increasing"

The model does not just see current data. It builds an understanding of **velocity and acceleration** — how fast signals are moving and whether they are speeding up or slowing down.

### Velocity Tracking
```python
def compute_signal_velocity(signal_history: list[float], window: int = 5) -> dict:
    """
    Velocity = how fast the signal is changing (first derivative)
    Acceleration = whether velocity is increasing or decreasing (second derivative)
    """
    if len(signal_history) < window:
        return {"velocity": 0, "acceleration": 0, "trend": "insufficient_data"}

    recent    = signal_history[-window:]
    velocity  = recent[-1] - recent[0]            # total change over window
    acc_recent = recent[-1] - recent[-2]          # last period change
    acc_prev   = recent[-2] - recent[-3]          # prior period change
    acceleration = acc_recent - acc_prev

    return {
        "velocity":     round(velocity, 4),       # positive = rising signal
        "acceleration": round(acceleration, 4),   # positive = speeding up
        "trend":        "accelerating" if acceleration > 0 else
                        "decelerating" if acceleration < 0 else "steady"
    }
```

### What This Looks Like for Users

```
GOLD — Signal Velocity Dashboard

Macro signal:        +0.82 ↑↑ (accelerating — getting stronger)
Technical signal:    +0.78 → (steady — maintaining)
News signal:         +0.71 ↑ (rising — new catalyst just appeared)
Cross-market signal: +0.58 ↓ (slowing — DXY stabilizing)

Overall signal velocity: ACCELERATING → Early in the move, not late
This suggests: The signal has room to run. Not a late entry.
```

This tells users whether they are catching a trend early (better) or late (riskier).

---

## 10. The "How Confident Should I Be?" User Guide

```
Confidence Level Guide (shown in UI):

90-100%   Extremely rare. All signals perfectly aligned.
           Historical: Happens ~3% of the time.
           Action: Maximum position allowed by risk engine.

80-90%    Strong signal. KB confirms. Agents agree.
           Historical: Happens ~12% of the time.
           Action: Full Kelly position. Tight stop.

70-80%    Good signal. Minor contradictions exist.
           Historical: Happens ~25% of the time.
           Action: 75% of Kelly position.

60-70%    Moderate signal. Some agents disagree.
           Historical: Happens ~35% of the time.
           Action: Half position. Watch for confirmation.

50-60%    Weak signal. Many agents disagree.
           Historical: Happens ~20% of the time.
           Action: Wait for better setup. Maybe 25% position.

Below 50% System says HOLD or AVOID.
           Action: No new position. Review existing ones.
```

---

## 11. Real-Time Signal Updates — The "Live Feed" Panel

A scrolling live feed shows new signals as they arrive, with plain-English explanations:

```
LIVE SIGNAL FEED — updating every 15 minutes

14:32 UTC  NEW: Fed minutes released — more hawkish than expected
           Impact: Gold headwind +0.08 (negative for Gold)
           Signal updated: Gold confidence 82% → 78%

14:18 UTC  GDELT: New geopolitical event detected (Middle East)
           GoldsteinScale: -5.2 (significant tension)
           Impact: Safe haven demand +0.11 (positive for Gold)
           Signal updated: Gold confidence 76% → 82%

14:05 UTC  Technical: Gold crossed above 200-day moving average
           This is a significant long-term bullish signal
           Impact: Technical score +0.08
           Signal updated: Gold direction CONFIRMED BUY

13:52 UTC  DXY update: Dollar at 103.85 (-0.94% today)
           Breaking below 104 is a bullish trigger for Gold
           Impact: Currency weakness signal +0.06
           Signal updated: Confidence strengthening

13:37 UTC  Volume: Gold trading 1.6× average volume
           Institutional buying confirmed by large block trades
           Impact: Technical confirmation +0.05

[Older entries...]
```

---

*Document 15 — Prediction Explainability*
*Requires approval before proceeding to build*
