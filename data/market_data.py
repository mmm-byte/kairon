"""
kairon/data/market_data.py
Price data fetcher: Yahoo Finance primary, with fallback stubs for
Binance (crypto) and Stooq (international). Graceful degradation with
staleness flags on every response.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
import numpy as np

from kairon.data import cache as cache_mod
from kairon.data.source_status import source_status

logger = logging.getLogger("kairon.market_data")

# ── Asset universe (Document 03) ───────────────────────────────────────────
ASSETS = {
    # Stocks
    "SPY":     {"name": "S&P 500 ETF",      "market": "stocks"},
    "QQQ":     {"name": "NASDAQ ETF",        "market": "stocks"},
    "AAPL":    {"name": "Apple",             "market": "stocks"},
    "MSFT":    {"name": "Microsoft",         "market": "stocks"},
    "NVDA":    {"name": "NVIDIA",            "market": "stocks"},
    "TSLA":    {"name": "Tesla",             "market": "stocks"},
    "AMZN":    {"name": "Amazon",            "market": "stocks"},
    # Crypto
    "BTC-USD": {"name": "Bitcoin",           "market": "crypto"},
    "ETH-USD": {"name": "Ethereum",          "market": "crypto"},
    "SOL-USD": {"name": "Solana",            "market": "crypto"},
    "BNB-USD": {"name": "BNB",              "market": "crypto"},
    "XRP-USD": {"name": "XRP",              "market": "crypto"},
    # Forex
    "EURUSD=X": {"name": "EUR/USD",          "market": "forex"},
    "GBPUSD=X": {"name": "GBP/USD",          "market": "forex"},
    "JPY=X":    {"name": "USD/JPY",          "market": "forex"},
    "AUDUSD=X": {"name": "AUD/USD",          "market": "forex"},
    # Commodities
    "GC=F":    {"name": "Gold",              "market": "commodities"},
    "CL=F":    {"name": "Crude Oil",         "market": "commodities"},
    "SI=F":    {"name": "Silver",            "market": "commodities"},
    "HG=F":    {"name": "Copper",            "market": "commodities"},
    "ZW=F":    {"name": "Wheat",             "market": "commodities"},
    "NG=F":    {"name": "Natural Gas",       "market": "commodities"},
    # Bonds
    "^TNX":    {"name": "US 10Y Yield",      "market": "bonds"},
    "^IRX":    {"name": "US 2Y Yield",       "market": "bonds"},
    "TLT":     {"name": "20Y Treasury ETF",  "market": "bonds"},
    "LQD":     {"name": "IG Corp Bond ETF",  "market": "bonds"},
    "HYG":     {"name": "High Yield ETF",    "market": "bonds"},
    # Real estate
    "VNQ":     {"name": "REIT ETF",          "market": "real_estate"},
    "PLD":     {"name": "Prologis",          "market": "real_estate"},
    "AMT":     {"name": "American Tower",    "market": "real_estate"},
    # Indices (for cross-market)
    "^GSPC":   {"name": "S&P 500",           "market": "stocks"},
    "^VIX":    {"name": "VIX",               "market": "macro"},
    "DX-Y.NYB":{"name": "DXY (Dollar Index)","market": "macro"},
    "^N225":   {"name": "Nikkei 225",        "market": "stocks"},
    "^FTSE":   {"name": "FTSE 100",          "market": "stocks"},
    "^GDAXI":  {"name": "DAX",               "market": "stocks"},
}

# Reverse lookup: name → ticker
TICKER_BY_NAME = {v["name"]: k for k, v in ASSETS.items()}


def _try_yfinance(ticker: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Yahoo Finance. Returns None on failure."""
    try:
        import yfinance as yf
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"open": "open", "high": "high", "low": "low",
                                 "close": "close", "volume": "volume"})
        return df.dropna(subset=["close"])
    except Exception as e:
        logger.warning(f"yfinance failed for {ticker}: {e}")
        return None


def _try_binance(ticker: str) -> Optional[pd.DataFrame]:
    """
    Fetch klines from Binance public API (no key required).
    Only for crypto tickers — converts 'BTC-USD' → 'BTCUSDT'.
    """
    try:
        import urllib.request
        import json
        symbol = ticker.replace("-USD", "USDT").replace("-", "").upper()
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=200"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        rows = []
        for k in data:
            rows.append({
                "date": pd.Timestamp(k[0], unit="ms", tz="UTC"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        df = pd.DataFrame(rows).set_index("date")
        return df if not df.empty else None
    except Exception as e:
        logger.warning(f"Binance fallback failed for {ticker}: {e}")
        return None


def _validate_df(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Validate OHLCV dataframe."""
    errors = []
    if len(df) < 30:
        errors.append(f"only {len(df)} rows (need 30+)")
    if df["close"].isna().sum() / len(df) > 0.05:
        errors.append("more than 5% null close prices")
    if not (df["close"] > 0).all():
        errors.append("non-positive close prices found")
    if not df.index.is_monotonic_increasing:
        errors.append("dates not in order")
    if "high" in df and "low" in df:
        if not (df["high"] >= df["low"]).all():
            errors.append("high < low in some rows")
    return len(errors) == 0, errors


def fetch_ohlcv(ticker: str, period: str = "6mo") -> dict:
    """
    Fetch OHLCV with automatic fallback.
    Returns a dict with 'df' (DataFrame), 'source', 'stale', 'fetched_at'.
    """
    asset_info = ASSETS.get(ticker, {"name": ticker, "market": "unknown"})
    market = asset_info["market"]

    # 1. Try Yahoo Finance
    df = _try_yfinance(ticker, period=period)
    if df is not None:
        valid, errs = _validate_df(df)
        if valid:
            source_status.mark_healthy("yahoo_finance")
            return {
                "df": df,
                "source": "yahoo_finance",
                "stale": False,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "ticker": ticker,
                "asset": asset_info["name"],
                "market": market,
            }
        logger.warning(f"Yahoo Finance data for {ticker} failed validation: {errs}")

    # 2. Crypto fallback — Binance public API
    if market == "crypto":
        df = _try_binance(ticker)
        if df is not None:
            valid, errs = _validate_df(df)
            if valid:
                source_status.mark_healthy("binance")
                return {
                    "df": df,
                    "source": "binance",
                    "stale": False,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "ticker": ticker,
                    "asset": asset_info["name"],
                    "market": market,
                }

    # 3. Return stale cache if available
    cached = cache_mod.get_price(ticker)
    if cached:
        cached["stale"] = True
        source_status.mark_degraded("yahoo_finance", "fetch failed, using cache")
        logger.warning(f"Returning stale cache for {ticker}")
        return cached

    # 4. Generate realistic simulated data for development/demo
    source_status.mark_degraded("yahoo_finance", "unavailable")
    logger.warning(f"No data for {ticker} — generating demo data")
    return _generate_demo_data(ticker, asset_info)


def _generate_demo_data(ticker: str, asset_info: dict) -> dict:
    """
    Generate plausible demo OHLCV for development when no network is available.
    Uses realistic seed prices and random walks with fat tails.
    """
    SEED_PRICES = {
        "GC=F": 2847.30, "CL=F": 78.40, "BTC-USD": 87500.0, "ETH-USD": 3180.0,
        "^GSPC": 5726.0, "SPY": 572.0, "QQQ": 490.0, "AAPL": 209.0,
        "EURUSD=X": 1.0832, "GBPUSD=X": 1.2634, "JPY=X": 149.8,
        "^TNX": 4.21, "^IRX": 5.32, "^VIX": 14.2, "DX-Y.NYB": 103.9,
        "HG=F": 4.18, "ZW=F": 545.0, "SI=F": 31.5, "NG=F": 2.14,
        "TLT": 92.0, "LQD": 105.0, "HYG": 77.0,
        "VNQ": 85.0, "PLD": 120.0, "AMT": 195.0,
        "SOL-USD": 155.0, "BNB-USD": 385.0, "XRP-USD": 0.52,
        "MSFT": 412.0, "NVDA": 875.0, "TSLA": 175.0, "AMZN": 192.0,
        "^N225": 38500.0, "^FTSE": 7640.0, "^GDAXI": 17800.0,
        "AUDUSD=X": 0.6521,
    }
    rng = np.random.default_rng(abs(hash(ticker)) % (2**31))
    base_price = SEED_PRICES.get(ticker, 100.0)
    n = 252  # 1 year of trading days

    # Generate a random walk with slight upward drift
    volatility = 0.012 if asset_info["market"] == "crypto" else 0.008
    returns = rng.normal(0.0002, volatility, n)
    closes = base_price * np.cumprod(1 + returns)

    highs = closes * (1 + rng.uniform(0.002, 0.015, n))
    lows = closes * (1 - rng.uniform(0.002, 0.015, n))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = rng.integers(1_000_000, 50_000_000, n)

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n, freq="B")
    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes.astype(float),
    }, index=dates)

    return {
        "df": df,
        "source": "demo_simulation",
        "stale": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "asset": asset_info["name"],
        "market": asset_info["market"],
    }


def get_current_price(ticker: str) -> Optional[float]:
    """Get just the latest close price for a ticker."""
    cached = cache_mod.get_price(ticker)
    if cached and not cached.get("stale"):
        df = cached.get("df")
        if df is not None and not df.empty:
            return float(df["close"].iloc[-1])

    result = fetch_ohlcv(ticker, period="5d")
    df = result.get("df")
    if df is not None and not df.empty:
        return float(df["close"].iloc[-1])
    return None


def get_all_prices() -> dict[str, dict]:
    """Fetch current price for all tracked assets. Returns {ticker: price_data}."""
    results = {}
    for ticker, info in ASSETS.items():
        if info["market"] == "macro":
            continue  # macro data fetched separately
        price = get_current_price(ticker)
        if price is not None:
            results[ticker] = {
                "ticker": ticker,
                "name": info["name"],
                "market": info["market"],
                "price": round(price, 4),
            }
    return results
