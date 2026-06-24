# Document 08 — Risk Engine
## Position Sizing, Drawdown Protection, Stop-Loss, Kelly Criterion

---

## 1. The Three Levels of Risk Protection

```
Level 1: POSITION LEVEL
  How much to put into any single trade.
  Tools: Kelly Criterion, market risk multiplier, volatility scaling.

Level 2: PORTFOLIO LEVEL
  How much risk the whole portfolio carries.
  Tools: Drawdown limit, concentration limit, correlation check.

Level 3: REGIME LEVEL
  Whether to trade at all given current market conditions.
  Tools: Crisis mode detection, capital preservation mode.
```

---

## 2. Kelly Criterion — Position Sizing Formula

The Kelly Criterion calculates the optimal fraction of capital to risk on a single trade, given the probability of winning and the expected payoff.

### Full Kelly Formula
```
f* = (p × b - q) / b

Where:
  f* = fraction of capital to deploy
  p  = probability of winning (our confidence score)
  q  = probability of losing (1 - p)
  b  = net odds (expected return / potential loss)
```

### Implementation
```python
def kelly_fraction(
    win_probability: float,    # agent confidence (0.0 to 1.0)
    expected_return: float,    # expected % gain (e.g., 0.021 for 2.1%)
    stop_loss_pct: float,      # max loss before stop triggers (e.g., 0.018)
) -> float:
    """
    Returns the raw Kelly fraction.
    Always halved (half-Kelly) for safety before applying other multipliers.
    """
    if win_probability <= 0 or win_probability >= 1:
        return 0.0

    p = win_probability
    q = 1 - p
    b = expected_return / max(stop_loss_pct, 0.001)   # reward-to-risk ratio

    kelly = (p * b - q) / b

    # Half-Kelly: industry standard safety adjustment
    # Full Kelly is mathematically optimal but psychologically brutal
    # Half-Kelly gives ~75% of expected return with ~50% of variance
    half_kelly = kelly * 0.50

    return max(0.0, half_kelly)   # never negative
```

### Example Calculation
```
Gold BUY signal:
  Confidence (p):       0.82
  Expected return:      2.1% (from historical KB matches)
  Stop-loss:            1.8% (below $2,798 support)

  b = 0.021 / 0.018 = 1.167  (reward-to-risk ratio)
  q = 1 - 0.82 = 0.18
  Full Kelly = (0.82 × 1.167 - 0.18) / 1.167 = 0.665
  Half Kelly = 0.665 × 0.5 = 0.333 (33.3% of capital)

Before market and volatility adjustments, Kelly says: use 33.3% of available capital.
```

---

## 3. Market Risk Multipliers

Different markets have different inherent risk levels. A 33% Kelly position in Crypto is far riskier than 33% in Bonds. These multipliers scale down the position for riskier markets.

```python
MARKET_RISK_MULTIPLIERS = {
    "bonds":       0.75,   # Safest — reduce Kelly less
    "real_estate": 0.85,
    "stocks":      1.00,   # Baseline
    "forex":       1.10,   # Leverage risk
    "commodities": 1.25,   # Volatility risk
    "crypto":      1.80,   # Much higher volatility — divide by 1.8
}

def apply_market_multiplier(kelly: float, market: str) -> float:
    multiplier = MARKET_RISK_MULTIPLIERS.get(market, 1.0)
    return kelly / multiplier
```

---

## 4. Volatility Regime Scaling

Beyond the market type, the current volatility regime further scales the position.

```python
VOLATILITY_POSITION_SCALE = {
    "Low":    1.00,    # Normal size
    "Medium": 0.75,    # 25% smaller
    "High":   0.50,    # 50% smaller
}

def scale_for_volatility(kelly: float, volatility_regime: str) -> float:
    scale = VOLATILITY_POSITION_SCALE.get(volatility_regime, 0.75)
    return kelly * scale
```

Volatility regime is determined by the asset's ATR percentile:
```python
def classify_volatility(atr_pct: float, market: str) -> str:
    thresholds = {
        "stocks":      (0.010, 0.025),
        "crypto":      (0.030, 0.060),
        "forex":       (0.003, 0.008),
        "commodities": (0.015, 0.035),
        "bonds":       (0.005, 0.012),
        "real_estate": (0.010, 0.020),
    }
    lo, hi = thresholds.get(market, (0.01, 0.03))
    if atr_pct <= lo:   return "Low"
    if atr_pct >= hi:   return "High"
    return "Medium"
```

---

## 5. Complete Position Sizing Calculation

```python
MAX_POSITION_PCT   = 0.25   # Hard cap: max 25% of capital in any single asset
MAX_DRAWDOWN_PCT   = 0.10   # Halt all new trades if portfolio drops 10%
MIN_NET_PROFIT_PCT = 0.005  # Minimum net profit required (0.5%)

@dataclass
class PositionRecommendation:
    viable:           bool
    position_usd:     float
    position_pct:     float    # as fraction of available capital
    stop_loss_price:  float
    stop_loss_pct:    float
    take_profit_pct:  float
    max_loss_usd:     float
    target_profit_usd: float
    risk_reward_ratio: float
    reason:           str

def calculate_position(
    win_probability:    float,
    expected_return:    float,
    market:             str,
    volatility_regime:  str,
    current_price:      float,
    available_capital:  float,
    current_drawdown:   float,
    total_cost_pct:     float,    # from cost engine
) -> PositionRecommendation:

    # Gate 1: Drawdown check
    if current_drawdown >= MAX_DRAWDOWN_PCT:
        return PositionRecommendation(
            viable=False,
            reason=f"Portfolio drawdown {current_drawdown:.1%} exceeds limit {MAX_DRAWDOWN_PCT:.0%}. No new positions.",
            position_usd=0, position_pct=0, **zeros()
        )

    # Gate 2: Net profit check
    net_return = expected_return - total_cost_pct
    if net_return < MIN_NET_PROFIT_PCT:
        return PositionRecommendation(
            viable=False,
            reason=f"Net return {net_return:.3%} below minimum {MIN_NET_PROFIT_PCT:.3%} after costs.",
            position_usd=0, position_pct=0, **zeros()
        )

    # Gate 3: Minimum confidence
    if win_probability < 0.55:
        return PositionRecommendation(
            viable=False,
            reason=f"Confidence {win_probability:.0%} below 55% minimum threshold.",
            position_usd=0, position_pct=0, **zeros()
        )

    # Stop-loss: 1.5× ATR-equivalent based on volatility
    stop_loss_pct = {
        "Low":    0.020,    # 2.0% stop
        "Medium": 0.035,    # 3.5% stop
        "High":   0.060,    # 6.0% stop
    }.get(volatility_regime, 0.035)

    # Kelly calculation chain
    raw_kelly   = kelly_fraction(win_probability, expected_return, stop_loss_pct)
    mkt_kelly   = apply_market_multiplier(raw_kelly, market)
    final_kelly = scale_for_volatility(mkt_kelly, volatility_regime)

    # Apply hard cap
    final_fraction = min(final_kelly, MAX_POSITION_PCT)

    position_usd = final_fraction * available_capital

    # Reward-to-risk: target 2:1 minimum
    take_profit_pct   = max(net_return * 2, net_return + stop_loss_pct)
    max_loss_usd      = position_usd * stop_loss_pct
    target_profit_usd = position_usd * take_profit_pct
    risk_reward       = take_profit_pct / stop_loss_pct

    return PositionRecommendation(
        viable=True,
        position_usd=round(position_usd, 2),
        position_pct=round(final_fraction, 4),
        stop_loss_pct=round(stop_loss_pct, 4),
        stop_loss_price=round(current_price * (1 - stop_loss_pct), 4),
        take_profit_pct=round(take_profit_pct, 4),
        max_loss_usd=round(max_loss_usd, 2),
        target_profit_usd=round(target_profit_usd, 2),
        risk_reward_ratio=round(risk_reward, 2),
        reason=f"Kelly {raw_kelly:.1%} → Market adj {mkt_kelly:.1%} → Vol adj {final_kelly:.1%} → Capped at {final_fraction:.1%}",
    )
```

---

## 6. Portfolio-Level Risk Controls

```python
class PortfolioRiskMonitor:

    def __init__(self, total_capital: float):
        self.total_capital   = total_capital
        self.peak_capital    = total_capital
        self.current_capital = total_capital
        self.positions       = {}   # {asset: PositionRecord}

    @property
    def current_drawdown(self) -> float:
        return (self.peak_capital - self.current_capital) / self.peak_capital

    @property
    def is_halted(self) -> bool:
        return self.current_drawdown >= MAX_DRAWDOWN_PCT

    def check_concentration(self, new_asset: str, new_amount: float) -> dict:
        """Ensure no single asset exceeds 25% of portfolio."""
        existing = self.positions.get(new_asset, {}).get("value", 0)
        new_total = existing + new_amount
        concentration = new_total / self.total_capital

        if concentration > MAX_POSITION_PCT:
            allowed = max(0, (MAX_POSITION_PCT * self.total_capital) - existing)
            return {
                "allowed": False,
                "max_additional": round(allowed, 2),
                "reason": f"{new_asset} would be {concentration:.0%} of portfolio (max {MAX_POSITION_PCT:.0%})"
            }
        return {"allowed": True, "max_additional": new_amount}

    def check_correlation_risk(
        self,
        new_asset: str,
        new_market: str,
        regime: str
    ) -> dict:
        """
        Check if adding this position creates too-high correlation
        with existing positions.
        """
        for existing_asset, pos in self.positions.items():
            corr = compute_live_correlation(existing_asset, new_asset, regime)
            if abs(corr) > 0.80 and pos["value"] > self.total_capital * 0.15:
                return {
                    "warning": True,
                    "reason": (
                        f"{new_asset} has {corr:.2f} correlation with your existing "
                        f"{existing_asset} position. Adding both reduces diversification."
                    ),
                    "suggestion": f"Consider reducing {existing_asset} before adding {new_asset}",
                }
        return {"warning": False}

    def get_portfolio_var(self, confidence: float = 0.95) -> float:
        """
        Value at Risk: maximum expected loss at given confidence level
        over a 1-day horizon. Simplified parametric approach.
        """
        if not self.positions:
            return 0.0

        portfolio_returns = []
        for asset, pos in self.positions.items():
            daily_vol = get_asset_volatility(asset)   # 20-day std of daily returns
            portfolio_returns.append(pos["value"] * daily_vol)

        # Simple sum (conservative — ignores diversification benefit)
        total_vol = sum(portfolio_returns)

        # VaR at 95% confidence: 1.645 standard deviations
        z_score = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}.get(confidence, 1.645)
        return round(total_vol * z_score, 2)
```

---

## 7. Crisis Mode — Capital Preservation

When VIX > 35 or drawdown > 10%, the system enters capital preservation mode:

```python
def get_crisis_recommendations(
    positions: dict,
    regime: str,
    drawdown: float
) -> list[str]:
    """
    In crisis mode, generate specific recommendations to protect capital.
    """
    recs = []

    if drawdown >= MAX_DRAWDOWN_PCT:
        recs.append("HALT: All new position opening suspended until drawdown recovers below 10%")

    if regime == "Crisis":
        # Check each position
        for asset, pos in positions.items():
            market = pos["market"]
            if market in ["crypto", "stocks", "real_estate"]:
                recs.append(
                    f"REDUCE: {asset} ({market}) — Risk assets perform poorly in crisis. "
                    f"Consider reducing to 50% of current position."
                )
            if market in ["bonds", "commodities"] and asset in ["Gold", "Silver"]:
                recs.append(
                    f"HOLD: {asset} — Safe haven asset, appropriate for crisis regime."
                )

    recs.append("Consider moving excess capital to cash / short-duration Treasuries (SHY ETF)")
    return recs
```

---

## 8. Stop-Loss and Take-Profit Management

Every position recommendation includes explicit stop-loss and take-profit levels:

```python
def calculate_exit_levels(
    entry_price:     float,
    position_type:   str,      # "LONG" | "SHORT"
    stop_loss_pct:   float,    # e.g., 0.035 for 3.5%
    take_profit_pct: float,    # e.g., 0.070 for 7.0% (2:1 ratio)
) -> dict:
    if position_type == "LONG":
        return {
            "stop_loss":   round(entry_price * (1 - stop_loss_pct), 4),
            "take_profit": round(entry_price * (1 + take_profit_pct), 4),
            "entry":       entry_price,
            "risk_reward": round(take_profit_pct / stop_loss_pct, 2),
        }
    else:  # SHORT
        return {
            "stop_loss":   round(entry_price * (1 + stop_loss_pct), 4),
            "take_profit": round(entry_price * (1 - take_profit_pct), 4),
            "entry":       entry_price,
            "risk_reward": round(take_profit_pct / stop_loss_pct, 2),
        }
```

### Trailing Stop Logic (future feature)
Once a position moves 50% of the way to take-profit, the stop-loss trails at 50% of the move to lock in partial gains.

---

## 9. Risk Summary Card (shown on Screen 2)

```
Position Risk Summary — Gold BUY ($20,000)

Kelly Calculation:
  Raw Kelly:             33.3%
  After market adj:      33.3% ÷ 1.0 = 33.3%
  After volatility adj:  33.3% × 1.0 = 33.3%
  After hard cap:        25.0% (capped)

  Recommended position:  $15,350 (25% of $61,400 available)

Exit Levels:
  Entry price:    $2,847.30
  Stop-loss:      $2,746.44  (-3.5%)  → max loss: $537
  Take-profit:    $3,046.61  (+7.0%)  → target:   $1,074
  Risk/Reward:    2.00 : 1

Portfolio Impact:
  Current drawdown:       0.0%  (no drawdown)
  After this position:    $15,350 / $104,820 = 14.6% concentration
  Within limits:          ✓ (max 25%)
  Correlation check:      ✓ No high-corr overlap with existing positions
  Portfolio VaR (95%):    $3,840 daily maximum expected loss
```

---

*Document 08 — Risk Engine*
*Requires approval before proceeding to build*
