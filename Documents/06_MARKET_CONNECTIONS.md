# Document 06 — Market Connections
## The Mathematical Model of How Markets Influence Each Other

---

## 1. The Problem With Static Correlations

Every finance textbook shows a correlation table between assets. The problem: those numbers are static averages. In reality, the correlation between Gold and stocks is approximately -0.20 in calm markets, -0.55 in fear markets, and -0.70 in crisis markets. Using a single number destroys the most valuable insight — that relationships change depending on the situation.

Kairon uses a **dynamic correlation model** that maintains three separate correlation matrices (normal, fear, crisis) and transitions between them based on real-time regime detection.

---

## 2. The Three Correlation Matrices

### Matrix 1: Normal / Calm Market
```
Asset pair              Correlation   Relationship
──────────────────────────────────────────────────
SPX   ↔ BTC             +0.35        Moderate positive (risk assets)
SPX   ↔ Gold            -0.20        Mild inverse (safe haven)
SPX   ↔ Oil             +0.30        Positive (growth proxy)
SPX   ↔ US 10Y          -0.50        Negative (rate sensitivity)
SPX   ↔ EUR/USD         +0.10        Weak (limited relationship)
Gold  ↔ USD (DXY)       -0.68        Strong inverse (priced in USD)
Gold  ↔ Silver          +0.82        Very strong (precious metals)
Gold  ↔ US 10Y Real     -0.74        Strong inverse (opportunity cost)
BTC   ↔ ETH             +0.88        Near-perfect (crypto beta)
Oil   ↔ CAD/USD         +0.71        Strong (petrocurrency)
Oil   ↔ Gold            +0.25        Mild (inflation hedge)
EUR/USD ↔ DXY           -0.95        Near-perfect inverse
US 10Y ↔ US 2Y          +0.87        Very strong (yield curve)
REITs ↔ US 10Y          -0.65        Strong inverse (rate sensitivity)
```

### Matrix 2: Fear / Risk-Off Market (VIX 22-35)
```
Asset pair              Correlation   Change from Normal
──────────────────────────────────────────────────────
SPX   ↔ BTC             +0.65        +0.30 (risk assets fall together)
SPX   ↔ Gold            -0.55        -0.35 (safe haven demand surges)
SPX   ↔ Oil             +0.55        +0.25 (demand fears hit both)
SPX   ↔ US 10Y          -0.70        -0.20 (flight to treasuries)
Gold  ↔ USD (DXY)       -0.30        +0.38 (both can rise in fear)
Gold  ↔ US 10Y Real     -0.82        -0.08 (stronger inverse)
BTC   ↔ ETH             +0.92        +0.04 (crypto falls together)
Oil   ↔ CAD/USD         +0.60        -0.11 (still correlated but weaker)
```

### Matrix 3: Crisis Market (VIX > 35)
```
Asset pair              Correlation   Change from Normal
──────────────────────────────────────────────────────
SPX   ↔ BTC             +0.88        +0.53 (everything crashes)
SPX   ↔ Gold            -0.70        -0.50 (gold surges as stocks crash)
SPX   ↔ Oil             +0.82        +0.52 (demand collapse hits both)
SPX   ↔ US 10Y          -0.80        -0.30 (max treasury demand)
Gold  ↔ USD (DXY)       +0.45        +1.13 (BOTH surge — liquidity crisis)
BTC   ↔ ETH             +0.95        +0.07 (near-lockstep)
All risk assets ↔ each other: approaching +0.90 (diversification collapses)
```

---

## 3. Regime Transition Model

The system continuously monitors for regime transitions using three signals:

### Signal 1: VIX Level and Trend
```python
def get_vix_regime(vix: float, vix_7d_change: float) -> str:
    if vix > 35:
        return "crisis"
    if vix > 22 or (vix > 18 and vix_7d_change > 4):
        return "fear"
    if vix < 16 and vix_7d_change < 0:
        return "calm"
    return "transitioning"
```

### Signal 2: Correlation Spike Detection (Eigenvalue Method)
```python
def detect_correlation_regime(returns_matrix: np.ndarray) -> str:
    """
    The eigenvalue ratio method from academic literature.
    In crisis, the largest eigenvalue dominates (all assets move together).
    In calm markets, many eigenvalues matter (assets move independently).
    """
    corr_matrix = np.corrcoef(returns_matrix.T)
    eigenvalues = np.linalg.eigvalsh(corr_matrix)
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]

    # Ratio of largest to second-largest eigenvalue
    ratio = eigenvalues_sorted[0] / eigenvalues_sorted[1]

    if ratio > 4.0:   return "crisis"       # one factor dominates all
    if ratio > 2.5:   return "fear"         # moderate concentration
    return "calm"                           # healthy diversification
```

### Signal 3: Credit Spread Monitoring
```python
def get_credit_regime(hy_spread: float, ig_spread: float) -> str:
    """
    High yield and investment grade spreads signal credit stress.
    Source: FRED series BAMLH0A0HYM2 and BAMLC0A0CM
    """
    if hy_spread > 700 or ig_spread > 200:   return "crisis"
    if hy_spread > 400 or ig_spread > 120:   return "fear"
    return "calm"
```

### Final Regime: Majority Vote
```python
def determine_regime(vix, vix_change, returns_matrix, hy_spread, ig_spread) -> str:
    votes = [
        get_vix_regime(vix, vix_change),
        detect_correlation_regime(returns_matrix),
        get_credit_regime(hy_spread, ig_spread),
    ]
    # Majority vote, with crisis taking priority on any single trigger
    if "crisis" in votes:   return "crisis"
    if votes.count("fear") >= 2:   return "fear"
    if votes.count("calm") >= 2:   return "calm"
    return "transitioning"
```

---

## 4. The Dynamic Correlation Update

The correlation matrix is updated daily using a rolling window approach. Rather than jumping abruptly between the three fixed matrices, the system interpolates smoothly:

```python
def compute_live_correlation(
    asset_a: str,
    asset_b: str,
    regime: str,
    transition_speed: float = 0.15   # how fast to shift between regimes
) -> float:
    """
    Returns the current correlation between two assets,
    interpolated between regime matrices based on current conditions.
    """
    # Get rolling empirical correlation (20-day and 60-day)
    corr_20d = compute_rolling_correlation(asset_a, asset_b, window=20)
    corr_60d = compute_rolling_correlation(asset_a, asset_b, window=60)

    # Get regime target correlation
    regime_target = CORRELATION_MATRICES[regime][(asset_a, asset_b)]

    # Blend: empirical (short) + empirical (long) + regime target
    live_corr = (
        0.40 * corr_20d +      # recent empirical behavior
        0.35 * corr_60d +      # medium-term empirical behavior
        0.25 * regime_target   # regime model expectation
    )

    return round(max(-1.0, min(1.0, live_corr)), 4)
```

---

## 5. Time-Zone Information Cascade — Full Specification

Markets open sequentially around the world. Each session transmits information to the next.

```python
UTC_SESSIONS = {
    "tokyo": {
        "open":  "00:00",
        "close": "06:00",
        "key_assets":    ["^N225", "JPY=X", "7203.T"],  # Nikkei, USDJPY, Toyota
        "leads":         ["european_auto", "asian_tech", "copper"],
        "signal_delay":  "2-4 hours"   # how long before Europe reacts
    },
    "shanghai": {
        "open":  "01:30",
        "close": "07:00",
        "key_assets":    ["000001.SS", "CNY=X", "HG=F"],  # Shanghai, USDCNY, Copper
        "leads":         ["copper", "iron_ore", "rare_earths", "asian_commodities"],
        "signal_delay":  "2-6 hours"
    },
    "london": {
        "open":  "08:00",
        "close": "16:30",
        "key_assets":    ["^FTSE", "GBPUSD=X", "EURUSD=X", "GC=F"],
        "leads":         ["forex_majors", "gold_fix", "european_equities"],
        "signal_delay":  "4-6 hours",
        "special": "London Metal Exchange gold fix at 10:30 UTC sets global gold reference"
    },
    "new_york": {
        "open":  "14:30",
        "close": "21:00",
        "key_assets":    ["^GSPC", "^IXIC", "^VIX", "DX-Y.NYB"],
        "leads":         ["global_risk_appetite", "crypto_flows", "all_commodities"],
        "signal_delay":  "immediate",
        "special": "VIX opening level sets global risk tone for the session"
    },
    "crypto_always": {
        "open":  "00:00",
        "close": "23:59",
        "notes": "24/7, no session breaks. Low-volume periods (00:00-08:00 UTC) have wider spreads and manipulation risk."
    }
}
```

### The Cascade Signal Algorithm

```python
def compute_cascade_signals(current_utc_hour: int, market_data: dict) -> dict:
    """
    Based on current time and recent session moves, compute
    likely direction of markets not yet open or early in session.
    """
    signals = {}

    # Tokyo closed, check its impact on Europe
    if 6 <= current_utc_hour <= 9:
        nikkei_5d = market_data["^N225"]["return_5d"]
        usdjpy     = market_data["JPY=X"]["return_1d"]

        # Nikkei strength → European auto stocks
        if abs(nikkei_5d) > 0.01:
            signals["european_auto"] = nikkei_5d * 0.35

        # JPY weakening = risk-on from Japan → positive for equities
        if usdjpy < -0.005:  # JPY strengthening = risk-off
            signals["global_risk"] = usdjpy * -0.40

    # Shanghai impact on copper and London open
    if 7 <= current_utc_hour <= 10:
        shanghai_1d = market_data["000001.SS"]["return_1d"]
        if abs(shanghai_1d) > 0.005:
            signals["copper"]    = shanghai_1d * 0.45
            signals["iron_ore"]  = shanghai_1d * 0.52
            signals["gold"]      = shanghai_1d * 0.12   # mild

    # New York pre-market impact
    if 13 <= current_utc_hour <= 15:
        spx_futures = market_data.get("ES=F", {}).get("return_1d", 0)
        if abs(spx_futures) > 0.003:
            signals["global_risk"]    = spx_futures * 0.60
            signals["crypto"]         = spx_futures * 0.40
            signals["gold"]           = spx_futures * -0.25  # inverse

    return signals
```

---

## 6. The Cross-Asset Influence Weight Matrix

Every agent considers cross-market influences using this weight matrix. The weights determine how strongly a signal in one market should update the signal for another.

```python
# How strongly market A's signal influences the prediction for market B
# Read as: INFLUENCE[from_market][to_market] = weight
# Positive = same direction, Negative = inverse

CROSS_INFLUENCE = {
    "spx": {
        "btc":           +0.40,   # risk-on/off correlation
        "gold":          -0.25,   # inverse (fear vs greed)
        "oil":           +0.30,   # economic growth proxy
        "bonds":         -0.45,   # flight to safety inverse
        "real_estate":   +0.35,   # growth sensitivity
        "forex_usd":     +0.15,   # mild positive
    },
    "dxy": {
        "gold":          -0.68,   # strong inverse (pricing)
        "oil":           -0.40,   # commodity pricing effect
        "btc":           -0.25,   # mild inverse
        "em_currencies": -0.75,   # strong inverse
        "forex_usd":     +0.95,   # essentially IS the DXY
    },
    "vix": {
        "gold":          +0.55,   # fear → safe haven demand
        "bonds":         +0.65,   # fear → treasury demand
        "btc":           -0.45,   # fear → crypto sell-off
        "spx":           -0.80,   # definitional inverse
        "oil":           -0.35,   # fear → demand concerns
    },
    "oil": {
        "inflation_expectations": +0.72,  # oil is a major CPI input
        "gold":                   +0.25,  # inflation hedge co-movement
        "cad_usd":                +0.71,  # petrocurrency
        "nok_usd":                +0.65,  # Norwegian krone
        "airline_stocks":         -0.60,  # cost input inverse
    },
    "us_10y_yield": {
        "gold":          -0.74,   # opportunity cost
        "real_estate":   -0.65,   # cap rate sensitivity
        "growth_stocks": -0.58,   # discount rate impact
        "bonds_price":   -0.99,   # definitional inverse
        "usd":           +0.45,   # higher yields attract USD
    },
}
```

---

## 7. Contagion Detection Algorithm

Contagion occurs when correlations suddenly spike above their normal range. The system monitors for this continuously.

```python
def detect_contagion(
    asset_pair: tuple[str, str],
    current_corr: float,
    normal_corr: float,
    window_days: int = 5
) -> dict:
    """
    Detect if a correlation has spiked beyond normal range.
    A spike > 2 standard deviations from the rolling average is flagged.
    """
    corr_history = get_rolling_correlations(asset_pair, days=90)
    mean   = np.mean(corr_history)
    std    = np.std(corr_history)

    z_score = (current_corr - mean) / (std + 1e-9)

    if abs(z_score) > 2.5:
        severity = "SEVERE" if abs(z_score) > 4 else "MODERATE"
        return {
            "contagion_detected": True,
            "severity":           severity,
            "asset_pair":         asset_pair,
            "current_corr":       round(current_corr, 3),
            "normal_corr":        round(normal_corr, 3),
            "z_score":            round(z_score, 2),
            "interpretation":     _interpret_contagion(asset_pair, z_score),
            "action":             "reduce_all_risk_positions" if severity == "SEVERE"
                                  else "increase_monitoring",
        }

    return {"contagion_detected": False}


def _interpret_contagion(asset_pair, z_score):
    a, b = asset_pair
    if z_score > 0:
        return (f"{a} and {b} are moving MORE together than usual "
                f"— diversification benefit reduced")
    else:
        return (f"{a} and {b} are moving MORE oppositely than usual "
                f"— potential arbitrage or regime divergence")
```

---

## 8. The Correlation Network Visualization Data

This data feeds the connection map on Screen 6:

```python
def get_network_data(regime: str) -> dict:
    """
    Returns nodes and edges for the connection graph visualization.
    Edge width = correlation strength. Edge color = direction.
    """
    assets = ["SPX", "BTC", "Gold", "Oil", "EUR/USD", "US 10Y", "REITs"]
    edges  = []

    for i, a in enumerate(assets):
        for b in assets[i+1:]:
            corr = compute_live_correlation(a, b, regime)
            if abs(corr) > 0.20:    # only show meaningful connections
                edges.append({
                    "source":    a,
                    "target":    b,
                    "weight":    abs(corr),
                    "direction": "positive" if corr > 0 else "negative",
                    "color":     "#00e676" if corr > 0 else "#ff3d57",
                    "width":     abs(corr) * 8,   # visual thickness
                    "label":     f"{corr:+.2f}",
                })

    return {
        "nodes":  [{"id": a, "label": a} for a in assets],
        "edges":  edges,
        "regime": regime,
    }
```

---

*Document 06 — Market Connections*
*Requires approval before proceeding to build*
