# Document 07 — Cost Engine
## Every Cost Calculated — Exact Formulas and Fee Schedules

---

## 1. The Seven Cost Types

Every move recommendation runs through all seven cost types before showing the user a net profit figure. If net profit is negative after all costs, the move is rejected.

| # | Cost Type | When It Applies | Typical Range |
|---|-----------|----------------|---------------|
| 1 | Broker commission (sell) | Always | 0.00%–0.10% |
| 2 | Broker commission (buy) | Always | 0.00%–0.10% |
| 3 | Bid-ask spread | Always | 0.01%–0.50% |
| 4 | Slippage | Always | 0.01%–0.30% |
| 5 | FX conversion | Cross-currency moves | 0.15%–0.50% |
| 6 | Crypto gas / network fee | Crypto transactions | $0.001–$5.00 flat |
| 7 | Capital gains tax | When selling at a profit | 0%–37% of gain |

---

## 2. Broker Commission Schedule

```python
BROKER_COMMISSIONS = {
    # Per-side rates (applied twice: once to sell, once to buy)
    "stocks":      0.0005,   # 0.05% — Robinhood/Webull free, IBKR $0.005/share
    "crypto":      0.0010,   # 0.10% — Coinbase/Binance taker fee
    "forex":       0.0002,   # 0.02% — FX broker commission (major pairs)
    "commodities": 0.0008,   # 0.08% — Futures commission + exchange fee
    "bonds":       0.0003,   # 0.03% — Bond ETF (near zero at Fidelity)
    "real_estate": 0.0005,   # 0.05% — REIT ETF (same as stocks)
}

def calc_broker_cost(amount: float, from_market: str, to_market: str) -> float:
    sell_fee = amount * BROKER_COMMISSIONS.get(from_market, 0.001)
    buy_fee  = amount * BROKER_COMMISSIONS.get(to_market,   0.001)
    return sell_fee + buy_fee
```

---

## 3. Bid-Ask Spread and Slippage

Spreads are not fixed — they widen dramatically during news events, low-liquidity periods, and high fear. Kairon uses VIX-adjusted spread estimates.

```python
BASE_SPREAD = {
    "stocks":      0.0001,   # Major caps: very tight
    "crypto":      0.0015,   # BTC/ETH: wider, especially for altcoins
    "forex":       0.00015,  # Major pairs: extremely tight
    "commodities": 0.0012,   # Futures: moderate
    "bonds":       0.0008,   # ETFs: tight
    "real_estate": 0.0010,   # REITs: moderate
}

BASE_SLIPPAGE = {
    "stocks":      0.0005,
    "crypto":      0.0020,   # Higher volatility = more slippage
    "forex":       0.0001,
    "commodities": 0.0010,
    "bonds":       0.0005,
    "real_estate": 0.0010,
}

def calc_spread_and_slippage(
    amount: float,
    from_market: str,
    to_market: str,
    vix: float,
    is_news_event: bool = False
) -> tuple[float, float]:
    """
    VIX-adjusted spread and slippage calculation.
    Both legs (sell + buy) are included.
    """
    # VIX multiplier: spreads widen significantly in fear/crisis
    if vix > 35:      vix_mult = 5.0   # Crisis: spreads 5× wider
    elif vix > 25:    vix_mult = 2.5   # Fear: spreads 2.5× wider
    elif vix > 18:    vix_mult = 1.5   # Mild fear: 50% wider
    else:             vix_mult = 1.0   # Normal

    # News event multiplier (major announcements: Fed, CPI, earnings)
    news_mult = 3.0 if is_news_event else 1.0

    combined_mult = max(vix_mult, news_mult)  # take the larger

    spread = amount * combined_mult * (
        BASE_SPREAD.get(from_market, 0.001) +
        BASE_SPREAD.get(to_market,   0.001)
    )

    slippage = amount * combined_mult * (
        BASE_SLIPPAGE.get(from_market, 0.001) +
        BASE_SLIPPAGE.get(to_market,   0.001)
    )

    return round(spread, 2), round(slippage, 2)
```

### When to Flag High Spread Warning

```python
SPREAD_WARNING_THRESHOLD = 0.005  # 0.5% total spread+slippage

def should_warn_spread(spread: float, slippage: float, amount: float) -> bool:
    total_pct = (spread + slippage) / amount
    return total_pct > SPREAD_WARNING_THRESHOLD
```

If threshold exceeded, the UI shows: "⚠️ Wide spreads detected — costs are elevated. Consider waiting for calmer market conditions."

---

## 4. FX Conversion Fees

When moving money across currency zones, conversion costs apply.

```python
# Which markets require FX conversion when crossing between them
FX_CONVERSION_REQUIRED = {
    # (from_market, to_market): (from_currency, to_currency, rate)
    ("stocks", "forex"):       ("USD", "varies",  0.0025),  # 0.25%
    ("forex",  "stocks"):      ("varies", "USD",  0.0025),
    ("forex",  "crypto"):      ("varies", "USD",  0.0030),
    ("crypto", "forex"):       ("USD", "varies",  0.0030),
    ("bonds",  "forex"):       ("USD", "varies",  0.0020),
    # Same-currency moves (USD-USD): no conversion
    ("stocks", "crypto"):      None,   # both USD-denominated
    ("stocks", "commodities"): None,   # both USD-denominated
    ("stocks", "bonds"):       None,   # both USD-denominated
}

FX_CONVERSION_RATE = 0.0025   # 0.25% default (bank rate)
FX_WIRE_COST       = 15.00    # flat fee for international wire

def calc_fx_cost(amount: float, from_market: str, to_market: str) -> float:
    key = (from_market, to_market)
    if key not in FX_CONVERSION_REQUIRED or FX_CONVERSION_REQUIRED[key] is None:
        return 0.0
    _, _, rate = FX_CONVERSION_REQUIRED[key]
    return round(amount * rate, 2)
```

---

## 5. Crypto Gas Fees (Flat USD)

Gas fees are network transaction costs, not percentage-based. They depend on the blockchain and current network congestion.

```python
# Approximate gas fees in USD (updated periodically from gas trackers)
CRYPTO_GAS_FEES = {
    "BTC-USD":  2.50,   # Bitcoin network fee (average)
    "ETH-USD":  3.80,   # Ethereum gas (varies 0.50-50.00)
    "SOL-USD":  0.001,  # Solana (near-zero)
    "BNB-USD":  0.10,   # Binance Smart Chain
    "XRP-USD":  0.0002, # XRP Ledger (near-zero)
    "default":  2.00,   # Unknown crypto
}

# Additional fees when moving between exchanges or to wallet
EXCHANGE_WITHDRAWAL_FEES = {
    "BTC":  0.0002,   # BTC (in BTC, ~$17 at $85k)
    "ETH":  0.005,    # ETH (in ETH, ~$16 at $3,200)
    "default": 5.00,  # USD equivalent
}

def calc_crypto_gas(
    to_asset: str,
    is_on_chain_transfer: bool = False
) -> float:
    """
    Gas fee applies when buying crypto.
    Additional withdrawal fee applies for on-chain transfers.
    """
    gas = CRYPTO_GAS_FEES.get(to_asset, CRYPTO_GAS_FEES["default"])
    if is_on_chain_transfer:
        gas += EXCHANGE_WITHDRAWAL_FEES.get(
            to_asset.replace("-USD", ""),
            EXCHANGE_WITHDRAWAL_FEES["default"]
        )
    return round(gas, 2)
```

---

## 6. Wire Transfer Fees

Wire fees apply when moving capital between different custody environments.

```python
# Flat wire/transfer fees in USD
WIRE_FEES = {
    # (from_market, to_market): fee
    ("stocks",      "crypto"):      25.00,  # Bank → crypto exchange
    ("crypto",      "stocks"):      25.00,  # Crypto → bank → brokerage
    ("stocks",      "forex"):       15.00,  # Brokerage → FX broker
    ("forex",       "stocks"):      15.00,
    ("crypto",      "forex"):       30.00,  # Crypto → FX broker (2 steps)
    ("forex",       "crypto"):      30.00,
    # Same-custody moves: no wire fee
    ("stocks",      "bonds"):        0.00,
    ("stocks",      "real_estate"):  0.00,
    ("bonds",       "real_estate"):  0.00,
    ("bonds",       "stocks"):       0.00,
    ("commodities", "stocks"):       0.00,
    ("real_estate", "stocks"):       0.00,
}

def calc_wire_fee(from_market: str, to_market: str) -> float:
    key = (from_market, to_market)
    return WIRE_FEES.get(key, 0.0)
```

---

## 7. Capital Gains Tax

This is often the largest cost. The system calculates tax based on actual holding period and unrealized gain.

```python
# US tax rates (configurable via .env for other jurisdictions)
SHORT_TERM_RATE = 0.37   # ordinary income rate (federal, high bracket)
LONG_TERM_RATE  = 0.20   # preferential rate for > 1 year
TAX_YEAR_DAYS   = 365    # days to qualify for long-term

# State tax rates (added on top of federal)
STATE_TAX_RATES = {
    "CA": 0.133,  # California (highest)
    "NY": 0.109,  # New York
    "TX": 0.000,  # Texas (no state income tax)
    "FL": 0.000,  # Florida
    "WA": 0.000,  # Washington
    "default": 0.05,  # rough national average
}

def calc_tax(
    amount_usd: float,
    unrealized_gain_pct: float,
    holding_days: int,
    state: str = "default",
    tax_loss_carryforward: float = 0.0,
) -> dict:
    """
    Calculate capital gains tax on closing a position.

    Returns itemized tax breakdown and optimization suggestion.
    """
    unrealized_gain_usd = amount_usd * unrealized_gain_pct

    # No tax if no gain or if at a loss
    if unrealized_gain_usd <= 0:
        return {
            "tax_usd": 0.0,
            "tax_type": "No gain — no tax",
            "rate": 0.0,
            "optimization": None
        }

    # Apply tax loss carryforward
    taxable_gain = max(0, unrealized_gain_usd - tax_loss_carryforward)
    if taxable_gain == 0:
        return {
            "tax_usd": 0.0,
            "tax_type": f"Offset by ${tax_loss_carryforward:.2f} carryforward",
            "rate": 0.0,
            "optimization": None
        }

    # Determine rate
    federal_rate = LONG_TERM_RATE if holding_days >= TAX_YEAR_DAYS else SHORT_TERM_RATE
    state_rate   = STATE_TAX_RATES.get(state, STATE_TAX_RATES["default"])
    total_rate   = federal_rate + state_rate

    tax_usd = taxable_gain * total_rate

    # Tax optimization check
    days_to_long_term = TAX_YEAR_DAYS - holding_days
    optimization = None
    if 0 < days_to_long_term <= 30:
        long_term_tax = taxable_gain * (LONG_TERM_RATE + state_rate)
        short_term_tax = taxable_gain * (SHORT_TERM_RATE + state_rate)
        saving = short_term_tax - long_term_tax
        if saving > 100:   # only flag if saving > $100
            optimization = {
                "action": f"Wait {days_to_long_term} more days",
                "saving": round(saving, 2),
                "message": (
                    f"Waiting {days_to_long_term} days qualifies for long-term rate "
                    f"({LONG_TERM_RATE:.0%} vs {SHORT_TERM_RATE:.0%}). "
                    f"Tax saving: ${saving:,.2f}"
                )
            }

    return {
        "tax_usd":       round(tax_usd, 2),
        "tax_type":      f"{'Long' if holding_days >= TAX_YEAR_DAYS else 'Short'}-term "
                         f"({total_rate:.0%} federal+state)",
        "federal_rate":  federal_rate,
        "state_rate":    state_rate,
        "total_rate":    total_rate,
        "taxable_gain":  round(taxable_gain, 2),
        "optimization":  optimization,
    }
```

---

## 8. The Master Cost Calculation Function

```python
def calculate_all_costs(
    amount_usd:          float,
    from_market:         str,
    to_market:           str,
    to_asset:            str        = "",
    holding_days:        int        = 0,
    unrealized_gain_pct: float      = 0.0,
    vix:                 float      = 15.0,
    is_news_event:       bool       = False,
    is_on_chain:         bool       = False,
    state:               str        = "default",
    tax_loss_carryforward: float    = 0.0,
) -> CostBreakdown:

    broker  = calc_broker_cost(amount_usd, from_market, to_market)
    spread, slippage = calc_spread_and_slippage(
        amount_usd, from_market, to_market, vix, is_news_event
    )
    fx      = calc_fx_cost(amount_usd, from_market, to_market)
    gas     = calc_crypto_gas(to_asset, is_on_chain) if to_market == "crypto" else 0.0
    wire    = calc_wire_fee(from_market, to_market)
    tax_res = calc_tax(amount_usd, unrealized_gain_pct, holding_days, state, tax_loss_carryforward)

    total   = broker + spread + slippage + fx + gas + wire + tax_res["tax_usd"]
    total_pct = total / (amount_usd + 1e-9)

    return CostBreakdown(
        amount_usd           = amount_usd,
        broker_cost          = round(broker, 2),
        spread_cost          = round(spread, 2),
        slippage_cost        = round(slippage, 2),
        fx_conversion_cost   = round(fx, 2),
        crypto_gas_cost      = round(gas, 2),
        wire_cost            = round(wire, 2),
        tax_cost             = tax_res["tax_usd"],
        tax_type             = tax_res["tax_type"],
        tax_optimization     = tax_res.get("optimization"),
        total_cost_usd       = round(total, 2),
        total_cost_pct       = round(total_pct * 100, 4),
        break_even_return_pct = round(total_pct * 100, 4),
    )
```

---

## 9. Minimum Net Profit Gate

Before any move is recommended, it must pass this gate:

```python
MIN_NET_PROFIT_PCT = 0.005   # 0.5% minimum net profit (from .env)

def passes_minimum_profit_gate(
    gross_return_pct: float,
    costs: CostBreakdown,
) -> tuple[bool, str]:
    """
    Returns (passes, reason).
    A move is only recommended if net profit exceeds the minimum threshold.
    """
    net_pct = gross_return_pct - (costs.total_cost_pct / 100)

    if net_pct < 0:
        return False, f"Net profit negative: {net_pct:.3%} after costs"

    if net_pct < MIN_NET_PROFIT_PCT:
        return False, (
            f"Net profit {net_pct:.3%} below minimum threshold "
            f"{MIN_NET_PROFIT_PCT:.3%}. Wait for stronger signal."
        )

    return True, f"Net profit {net_pct:.3%} exceeds minimum threshold"
```

---

*Document 07 — Cost Engine*
*Requires approval before proceeding to build*
