# Document 09 — UI Screens
## All 5 Screens — Layout, Components, Interactions, Data

---

## Design Language

**Aesthetic:** Dark terminal / mission control. Not a generic finance dashboard.
**Typography:** Syne (display) + JetBrains Mono (data/numbers)
**Color system:**
```
Background layers: #080b0f → #0d1117 → #111820 → #161e28
Green  (bullish/positive): #00e676
Red    (bearish/negative): #ff3d57
Amber  (warning/neutral):  #ffb300
Blue   (informational):    #2979ff
Purple (AI/agents):        #aa00ff
Text:   #e8edf5 / #7a8496 / #3d4558
```
**Principles:**
- Every number that matters is visible without scrolling
- Color always encodes meaning (never decoration)
- Monospace font for all financial data (alignment critical)
- Decision buttons are the most prominent element on action screens

---

## Global Layout

```
┌─────────────────────────────────────────────────────────┐
│  TOPBAR (52px)                                          │
│  Logo · Regime chip · SIM badge · Portfolio · Clock     │
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT AREA                          │
│ (210px)  │  (scrollable)                               │
│          │                                             │
│ Nav items│  Active screen renders here                 │
│          │                                             │
│ Sim      │                                             │
│ Portfolio│                                             │
│ Value    │                                             │
│          │                                             │
│ Regime   │                                             │
│ Switcher │                                             │
└──────────┴─────────────────────────────────────────────┘
```

### Topbar contents (left to right)
1. Logo: "Kai**ron**" — "ron" in green
2. Live dot (pulsing green animation)
3. Regime chip — label + color changes with current regime
4. "SIM MODE — No real money" amber badge (always visible)
5. [Right-aligned] Simulated portfolio value in green monospace
6. [Right-aligned] UTC clock in monospace

### Sidebar contents
- Navigation items (5 screens)
- Simulated portfolio value card (updates with regime changes)
- Regime switcher buttons (Calm / Risk-off / Inflationary / Crisis)

---

## Screen 1: Mission Control

**Purpose:** Global overview — answer "what is the world telling me right now?"
**When to use:** Open this first, every single day.

### Layout
```
KPI Row (5 cards)
├─ Portfolio value
├─ Available capital
├─ Active signals count
├─ VIX (fear index)
└─ KB accuracy

Two-Column Section
├─ LEFT: Live market snapshot table
└─ RIGHT: Sentiment bars + Active alerts

Three-Column Section
├─ Gold sparkline chart
├─ Bitcoin sparkline chart
└─ S&P 500 sparkline chart
```

### KPI Cards
Each card has a colored top border (green/amber/red based on value):

| Card | Value | Sub-line |
|------|-------|---------|
| Portfolio (sim) | $104,820 | ↑ +$4,820 today |
| Available capital | $61,400 | $43.4k deployed |
| Active signals | 5 | 3 BUY · 1 SELL · 1 WATCH |
| VIX | 14.2 | Low fear — risk on |
| KB accuracy | 74% | 142 predictions tracked |

All values change when regime is switched.

### Market Snapshot Table
Columns: Asset name + ticker, Price (monospace, updates every 3 seconds), 24h change %, Signal badge, Confidence %

Signal badge styles:
- BUY: green background, green text
- SELL: red background, red text
- HOLD: amber background, amber text
- WATCH: blue background, blue text

### Sentiment Bars
One horizontal bar per market. Bar fill = absolute sentiment value. Color = green (positive) or red (negative). Label on left, numeric value (+0.72 or -0.38) on right.
Below bars: Fear & Greed index (0-100 number with label like "62 — Greed").

### Active Alerts
Stacked list, each showing:
- Colored dot (green = bullish, red = bearish, amber = watch)
- Bold title (what happened)
- Monospace subtitle (technical detail)
- Tag badge on right (HIGH / MED / AVOID / WATCH)

Clickable — takes user to Screen 2 filtered for that alert.

### Sparkline Charts
30-day simulated price chart for Gold, Bitcoin, S&P 500. Line + fill below. Colored dot at current price. Signal and daily change shown below chart.

### Regime Switching
When user clicks a regime button in sidebar, ALL of these change simultaneously:
- Regime chip label and color in topbar
- VIX value and sub-label
- Fear & Greed score
- Portfolio value and daily change
- Sentiment bar values shift
- Alert content updates

---

## Screen 2: Move Recommendations

**Purpose:** Where profits come from — decide what to execute.
**This is the most important screen.**

### Layout
```
Screen title + subtitle

KPI Row (4 cards)
├─ Total net profit if all executed
├─ Capital required vs available
├─ Highest confidence move
└─ Average cost drag

Move cards (stacked, ranked #1 to #N)
```

### Move Card Structure
Each card contains:

**Header row:**
- Rank badge (#1 green, #2 purple, #3 blue)
- FROM asset → TO asset with market tag
- Capital amount · Horizon · Confidence · KB citation
- Urgency badge (right-aligned, color-coded)

**Three-column body:**

Column 1 — Cost Waterfall:
```
Gross profit             +$500  ████████████████████
Broker fees (×2)          -$20  ████
Spread + slippage         -$32  ██████
FX conversion              $0
Crypto gas                 $0
Wire/transfer              $0
Capital gains tax         -$28  █████
─────────────────────────────
Total costs               -$80  ████████████████
NET PROFIT               +$420
2.10% · Break-even: 0.40%
```

Column 2 — Agent Signals:
```
Technical    ████████████████     +0.78
Fundamental  █████████████        +0.65
News         ██████████████       +0.71
Macro        ████████████████     +0.82
Cross-market ███████████          +0.58

KB: 6/7 similar setups → Gold +2.1% avg in 5 days
```

Column 3 — Timing & Risks:
```
Act: 1–3 days
Strong macro + news signals. Risk-Off regime
favors Gold. Don't wait past Thursday CPI.

→ CPI above 3.5% → rate cut odds fade
→ DXY breakout above 105 → Gold headwind
→ Stop-loss: $2,798 (-1.8%)
```

**AI Analysis strip** (full width, darker background):
"AI analysis: [plain English explanation from LLM]"

**Action row** (full width):
- Execute button (colored to match asset)
- Pass button
- Confidence + KB citation text
- Agent details link (→ Screen 3)

### Execute Behavior
When clicked:
- Button text changes to "✓ Executed — logged to KB"
- Button style changes to outline green
- Card fades to 40% opacity
- Decision logged to knowledge base with timestamp
- Outcome check scheduled at horizon date

### Pass Behavior
When clicked:
- Card fades to 40% opacity
- Optional: prompt for reason (feeds knowledge base)

### Tax Optimization Alert
When a position has been held 340-364 days:
- Amber highlight on cost column
- Alert text: "Wait X more days → save $Y in tax (short-term → long-term)"
- Execute button changes to "Schedule in X days →"

---

## Screen 3: Agent Intelligence

**Purpose:** Full transparency — understand exactly why the system said what it said.

### Layout
```
Screen title

2×N agent card grid (one per agent)

Full-width: Bull vs Bear debate card

Full-width: Cross-market contagion map
```

### Agent Cards (2 per row)
Each card shows:
- Agent name + avatar initials (colored circle)
- Score (+0.78 in large monospace, colored)
- Reasoning paragraph (2-4 sentences, what the agent saw)

Agent avatar colors:
- Technical: green (#00e676)
- Fundamental: amber (#ffb300)
- News: blue (#2979ff)
- Macro: red (#ff3d57)
- Cross-Market: purple (#aa00ff)

### Bull vs Bear Debate Card
Two sections, side by side with divider:
- Bull section: green text, strongest case for the trade
- Bear section: red text, strongest case against

Below debate: "Trader verdict" — the synthesis conclusion in white text with green "AI analysis:" label.

### Cross-Market Contagion Map
3-column layout:
- Asia → Europe signals
- Europe → US signals
- US → Crypto signals

Each column shows 2-3 specific causal relationships happening right now.

---

## Screen 4: Knowledge Base

**Purpose:** See the system learning — accuracy tracking, lessons extracted, prediction log.

### Layout
```
Screen title

3 KPI cards: Total predictions · Overall accuracy · Best asset

Two-column section:
├─ LEFT: Accuracy by asset (bar chart)
└─ RIGHT: Lessons extracted

Full-width: Prediction log table
```

### Accuracy By Asset
Horizontal bars, one per asset. Color: green (>75%), amber (65-75%), red (<65%). Shows percentage and prediction count.

### Lessons Extracted
Cards with colored left border. Each shows:
- Lesson statement (the pattern learned)
- Confidence % and observation count (monospace)

### Prediction Log Table
Columns: Date | Asset | Predicted | Actual | Outcome | Net P&L

Outcome badge: green "CORRECT" or red "WRONG"

---

## Screen 5: Cost Calculator

**Purpose:** Calculate exact net profit for any move you are considering.

### Layout
```
Screen title

Two-column:
├─ LEFT: Input form
└─ RIGHT: Cost breakdown + Decision
```

### Input Form (5 fields)
1. Capital amount ($) — number input (min: $10)
2. From market — dropdown (6 options)
3. To market — dropdown (6 options)
4. Expected return (%) — number input with 0.1 step
5. Days held (for tax calculation) — number input
6. Unrealized gain on position being sold (%) — number input

All inputs trigger instant recalculation (oninput event).

### Cost Breakdown (auto-calculates)
Itemized list:
- Gross profit
- Broker fees (×2)
- Spread + slippage
- FX conversion (only if forex involved)
- Crypto gas fee (only if crypto destination)
- Wire/transfer fee (only if custody changes)
- Capital gains tax (rate shown: short-term 37% or long-term 20%)
- **Total costs**
- **NET PROFIT** (large, colored green or red)
- Net % and break-even % needed

### Decision Box
- Green "✓ PROCEED" box: profitable after costs
- Red "✗ DO NOT PROCEED" box: costs exceed expected profit

Both include explanation text of the specific calculation.

---

## Regime Effects on All Screens

| Element | Calm | Risk-Off | Inflationary | Crisis |
|---------|------|----------|--------------|--------|
| Topbar chip | Green | Red | Amber | Purple |
| VIX | 14.2 | 28.7 | 22.1 | 52.4 |
| Portfolio | $104,820 | $98,600 | $102,100 | $91,600 |
| Fear & Greed | 62 — Greed | 31 — Fear | 44 — Neutral | 8 — Extreme Fear |
| Move #1 | Gold/Stocks BUY | Treasuries BUY | Commodities BUY | Cash hold |
| Agent weights | Technical leads | Macro leads | News leads | Crisis mode |

---

## Mobile Considerations (v2)

Screen 1: Single column, KPIs as 2×3 grid
Screen 2: Move cards full width, body sections stack vertically
Screen 3: Agent cards single column
Screen 4: Accuracy bars compress well
Screen 5: Form stacks vertically, breakdown below

---

*Document 09 — UI Screens*
*Requires approval before proceeding to build*
