# Document 13 — Real Data Loading
## How Users Load Their Own Real Financial Data for Simulation

---

## 1. The Core Idea

Kairon's simulation mode uses realistic market patterns by default. But users who want to see analysis based on their **actual holdings** — the real stocks they own, the real crypto they hold, the real cash they have — can load that data directly into the platform.

**Critical: No data is stored on any server. Everything runs in the browser session. When you close the tab, it's gone.**

---

## 2. Three Ways to Load Real Data

### Method A — Manual Entry (Always Available)
The simplest method. User types in their holdings directly.

```
Screen: "Load My Portfolio"

┌─────────────────────────────────────────────────────┐
│  My Holdings                                        │
│                                                     │
│  Asset          Quantity    Avg Buy Price   Value   │
│  ─────────────────────────────────────────────────  │
│  AAPL           [50    ]    [$148.20  ]    $9,240   │
│  BTC            [0.25  ]    [$62,000  ]    $21,855  │
│  Gold ETF (GLD) [20    ]    [$180.00  ]    $3,720   │
│  Cash           [       ]   [         ]   $15,000   │
│                                                     │
│  + Add holding                                      │
│                                                     │
│  Total portfolio value:  $49,815                    │
│  [Run Analysis on My Portfolio →]                   │
└─────────────────────────────────────────────────────┘
```

What gets computed automatically:
- Current market value (live price × quantity)
- Unrealized gain/loss (current - avg buy price)
- % of portfolio per holding
- Days held (if date purchased is provided)
- Tax implication (short vs long-term based on days held)

### Method B — CSV Upload
User exports their holdings from their broker and uploads the CSV. Kairon reads it, maps columns automatically, and loads the portfolio.

**Supported brokers and their CSV formats:**

| Broker | Export Location | Column Mapping |
|--------|----------------|---------------|
| Robinhood | Account → Statements → CSV | Symbol, Quantity, Average Cost |
| Coinbase | Reports → Generate Report | Asset, Quantity, Cost Basis |
| Fidelity | Portfolio → Download | Symbol, Quantity, Cost Basis/Share |
| Charles Schwab | Accounts → History → Export | Symbol, Quantity, Price |
| Interactive Brokers | Reports → Tax → CSV | Symbol, Quantity, Cost |
| Binance | Orders → Export | Symbol, Amount, Average Price |
| Generic | Any CSV | Manual column mapping |

**CSV Upload Flow:**
```
1. User drags CSV file onto upload zone (or clicks to browse)
2. System previews first 5 rows of the file
3. System auto-detects column mapping
4. User confirms or corrects the mapping:
   - Which column = Asset name/ticker
   - Which column = Quantity
   - Which column = Purchase price
   - Which column = Purchase date (optional)
5. System loads holdings
6. Analysis runs automatically
```

**Privacy note shown during upload:**
> "Your file is processed entirely in your browser. It is never sent to any server. We cannot see your financial data."

### Method C — Paste from Spreadsheet
User copies rows from Excel/Google Sheets and pastes directly.

```
Paste your holdings here (copied from Excel/Sheets):

┌────────────────────────────────────────────────────┐
│ AAPL    50    148.20    2024-03-15                  │
│ BTC     0.25  62000     2024-01-08                  │
│ GLD     20    180.00    2023-11-20                  │
│ Cash    15000                                       │
└────────────────────────────────────────────────────┘

[Parse My Data →]
```

System detects columns automatically (ticker, quantity, price, date).

---

## 3. What Happens After Data Is Loaded

Once the portfolio is loaded, the entire platform re-runs its analysis using the user's actual holdings as context:

### Screen 1 (Mission Control) changes:
- Portfolio value now shows the user's real simulated value (real prices × real quantities)
- "Available capital" shows their actual cash balance
- "Active signals" count refers to assets they actually hold
- KPI cards show their real unrealized gains/losses

### Screen 2 (Move Recommendations) changes:
**This is the most powerful change.**

Move recommendations now show:
- "You currently hold 50 AAPL (worth $9,240) — should you hold, add, or sell?"
- "You hold 0.25 BTC (bought at $62,000, currently at $87,420, +41% unrealized gain)"
- Tax optimization becomes real: "You've held AAPL 373 days — long-term tax rate applies (20% vs 37%)"
- Cost calculations use their actual quantities, not hypothetical amounts

**Example move card with real data loaded:**
```
#1  Your AAPL (373 days) → Gold
    You currently hold: 50 shares @ $148.20 avg = $9,240 cost basis
    Current value: $10,450 (+$1,210 unrealized gain, +13.1%)
    
    Tax situation: 373 days held → LONG-TERM rate (20%)
    Tax on $1,210 gain: $242 (vs $448 if sold before day 365)
    
    Cost Breakdown:
    Gross profit (if Gold rises 2.5%): +$261
    Broker fees (×2):                  -$10
    Spread + slippage:                 -$14
    Capital gains tax (20%):          -$242
    ─────────────────────────────────────
    NET PROFIT: +$5
    
    ⚠ Not worth it yet. Wait for Gold to signal +4%+ move to cover your tax drag.
```

### Screen 5 (Cost Calculator) changes:
Pre-populated with user's real holdings. They can select any of their assets as the "from" position and see exact costs.

### Agent analysis changes:
Agents now know:
- What the user actually holds (not hypothetical)
- When they bought it (tax implications)
- Their unrealized gains (risk of selling)
- Their concentration (e.g., "You are 45% in AAPL — highly concentrated in tech")

---

## 4. Real Data Loading UI — Screen Design

```
┌──────────────────────────────────────────────────────────────┐
│  Load My Real Holdings                                       │
│  Your data never leaves your browser. Zero server storage.  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Choose how to load:                                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Manual  │  │  Upload  │  │  Paste   │                  │
│  │  Entry   │  │  CSV     │  │  from    │                  │
│  │          │  │          │  │  Sheet   │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│                                                              │
│  ─────────────────── OR ───────────────────                 │
│                                                              │
│  Quick Load — Common Portfolios (for learning):             │
│                                                              │
│  [Conservative ($100k)] [Balanced ($100k)] [Aggressive ($100k)]
│  [Crypto Heavy ($50k)]  [All Stocks ($100k)]                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Quick Load Preset Portfolios (for users who want to explore)

| Preset | Holdings | Purpose |
|--------|---------|---------|
| Conservative | 60% bonds, 30% gold, 10% cash | Learn how defensive portfolios respond |
| Balanced | 40% stocks, 20% bonds, 20% gold, 20% cash | Classic 60/40 equivalent |
| Aggressive | 60% stocks, 30% crypto, 10% cash | High risk/reward portfolio |
| Crypto Heavy | 50% BTC, 30% ETH, 20% cash | Crypto-focused portfolio |
| All Stocks | SPY 40%, AAPL 20%, NVDA 20%, TSLA 10%, AMZN 10% | Equity-only |

---

## 5. Supported Asset Types

When loading real data, Kairon can analyze:

| Asset Type | Examples | Notes |
|-----------|---------|-------|
| US Stocks | AAPL, MSFT, NVDA, any NYSE/NASDAQ ticker | Full analysis |
| US ETFs | SPY, QQQ, GLD, VNQ | Full analysis |
| Crypto | BTC, ETH, SOL, BNB, XRP | Full analysis |
| Forex positions | EUR/USD, GBP/USD | Full analysis |
| Commodities | Gold, Oil (via ETFs) | Full analysis |
| Bonds | Treasury ETFs, TLT, SHY | Full analysis |
| REITs | VNQ, O, AMT | Full analysis |
| Cash | USD, EUR, GBP | Purchasing power analysis |
| Unknown ticker | Any string | User prompted to confirm or map manually |

---

## 6. Privacy Architecture

**This is the most important section.**

```
User loads CSV
      │
      ▼ (all in browser memory)
JavaScript FileReader API reads the file
      │
      ▼
Data parsed in browser (Papa Parse library — client-side only)
      │
      ▼
Holdings stored in browser sessionStorage (cleared on tab close)
      │
      ▼
When analysis runs: ticker symbols sent to API to fetch live prices
      │
      ▼
API returns: price, technical indicators, signals
(No quantity, no cost basis, no personal data ever sent)
      │
      ▼
All portfolio calculations happen in browser JavaScript
(Value × quantity, gain/loss, tax computation — all local)
      │
      ▼
User sees results. Nothing persisted anywhere.
```

**What IS sent to the server:**
- Ticker symbols (e.g., "AAPL", "BTC") to fetch live prices
- Nothing else

**What is NEVER sent to the server:**
- Quantities owned
- Purchase prices
- Purchase dates
- Total portfolio value
- Gains or losses
- Any personal information

---

## 7. Data Validation

When user inputs are loaded, the system validates:

```python
def validate_holding(ticker, quantity, avg_price):
    errors = []

    # Ticker exists
    if not yahoo_finance_exists(ticker):
        errors.append(f"Ticker '{ticker}' not found — did you mean {suggest_similar(ticker)}?")

    # Quantity is positive
    if quantity <= 0:
        errors.append("Quantity must be greater than 0")

    # Price is reasonable (within 10× of historical range)
    current = get_current_price(ticker)
    if avg_price > current * 10 or avg_price < current * 0.1:
        errors.append(f"Avg price ${avg_price} seems unusual for {ticker} (current: ${current})")

    return errors
```

If errors found: highlight the row in red, show the error message, let user correct before proceeding.

---

## 8. Session Persistence Option

By default, data is lost when the tab closes. Users can optionally enable session persistence:

```
[  ] Remember my holdings for this browser session
    (Uses browser localStorage — data stays until you clear it)
    No server storage. Only your browser.
```

When enabled:
- Holdings saved to `localStorage` under key `kairon_portfolio_v1`
- Automatically loaded on next visit
- "Clear my data" button always visible to wipe it

---

*Document 13 — Real Data Loading*
*Requires approval before proceeding to build*
