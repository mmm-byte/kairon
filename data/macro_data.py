"""
kairon/data/macro_data.py
Macro data: FRED primary, Yahoo Finance proxy fallback (no API key needed).
Covers all series from Document 03: rates, inflation, VIX, DXY, credit spreads.
"""
import logging
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import numpy as np

from kairon.data import cache as cache_mod
from kairon.data.source_status import source_status

logger = logging.getLogger("kairon.macro")

# ── FRED series → Yahoo Finance proxy mapping ─────────────────────────────────
FRED_TO_YAHOO_PROXY = {
    "DGS10":        "^TNX",       # US 10Y Treasury yield
    "DGS2":         "^IRX",       # US 2Y Treasury yield
    "VIXCLS":       "^VIX",       # VIX
    "DTWEXBGS":     "DX-Y.NYB",   # DXY (dollar index)
    "BAMLH0A0HYM2": "HYG",        # High yield proxy (ETF price, not spread)
    "BAMLC0A0CM":   "LQD",        # IG bond proxy
    "T10YIE":       None,         # Breakeven inflation — no clean proxy
    "FEDFUNDS":     None,         # Fed funds — use hardcoded recent value
}

# Known approximate current values for when all sources fail
FALLBACK_VALUES = {
    "FEDFUNDS":     4.33,
    "DGS10":        4.21,
    "DGS2":         4.68,
    "T10Y2Y":       -0.47,  # inverted
    "CPIAUCSL":     314.1,
    "T10YIE":       2.34,
    "VIXCLS":       14.2,
    "DTWEXBGS":     103.9,
    "BAMLH0A0HYM2": 3.42,
    "BAMLC0A0CM":   0.89,
    "ECBDFR":       3.25,
}

SERIES_META = {
    "FEDFUNDS":     {"name": "Federal Funds Rate",             "units": "%"},
    "DGS10":        {"name": "10Y Treasury Yield",             "units": "%"},
    "DGS2":         {"name": "2Y Treasury Yield",              "units": "%"},
    "T10Y2Y":       {"name": "Yield Spread (10Y-2Y)",          "units": "%"},
    "CPIAUCSL":     {"name": "CPI (Urban Consumers)",          "units": "Index"},
    "T10YIE":       {"name": "10Y Inflation Expectations",     "units": "%"},
    "VIXCLS":       {"name": "VIX Fear Index",                 "units": "Index"},
    "DTWEXBGS":     {"name": "US Dollar Index (DXY proxy)",    "units": "Index"},
    "BAMLH0A0HYM2": {"name": "High Yield Credit Spread",       "units": "bps"},
    "BAMLC0A0CM":   {"name": "IG Credit Spread",               "units": "bps"},
    "ECBDFR":       {"name": "ECB Deposit Facility Rate",      "units": "%"},
}


def _fetch_fred_series(series_id: str, api_key: str, limit: int = 10) -> Optional[float]:
    """Fetch the latest value for a FRED series."""
    try:
        params = urllib.parse.urlencode({
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        })
        url = f"https://api.stlouisfed.org/fred/series/observations?{params}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        obs = [o for o in data.get("observations", []) if o.get("value") != "."]
        if obs:
            return float(obs[0]["value"])
    except Exception as e:
        logger.warning(f"FRED fetch failed for {series_id}: {e}")
    return None


def _fetch_yahoo_proxy(ticker: str) -> Optional[float]:
    """Get latest price from Yahoo Finance as a macro proxy."""
    try:
        from kairon.data.market_data import fetch_ohlcv
        result = fetch_ohlcv(ticker, period="5d")
        df = result.get("df")
        if df is not None and not df.empty:
            return float(df["close"].iloc[-1])
    except Exception as e:
        logger.debug(f"Yahoo proxy failed for {ticker}: {e}")
    return None


def get_macro_value(series_id: str) -> dict:
    """
    Get a macro value with full provenance.
    Tries: cache → FRED → Yahoo proxy → hardcoded fallback.
    """
    # 1. Cache hit
    cached = cache_mod.get_macro(series_id)
    if cached:
        return cached

    from kairon.config import cfg
    value = None
    source = "fallback"

    # 2. FRED (if API key available)
    if cfg.has_fred:
        value = _fetch_fred_series(series_id, cfg.fred_api_key)
        if value is not None:
            source = "fred"
            source_status.mark_healthy("fred")

    # 3. Yahoo Finance proxy
    if value is None:
        proxy_ticker = FRED_TO_YAHOO_PROXY.get(series_id)
        if proxy_ticker:
            value = _fetch_yahoo_proxy(proxy_ticker)
            if value is not None:
                source = "yahoo_proxy"
                source_status.mark_degraded("fred", "using Yahoo proxy" if not cfg.has_fred else "")

    # 4. Hardcoded fallback
    if value is None:
        value = FALLBACK_VALUES.get(series_id)
        source = "hardcoded_fallback"
        if not cfg.has_fred:
            source_status.mark_degraded("fred", "no API key — add FRED_API_KEY for real data")

    result = {
        "series_id":    series_id,
        "series_name":  SERIES_META.get(series_id, {}).get("name", series_id),
        "value":        value,
        "source":       source,
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
        "stale":        source in ("hardcoded_fallback",),
    }
    if value is not None:
        cache_mod.set_macro(series_id, result)
    return result


def get_macro_snapshot() -> dict:
    """
    Fetch all key macro indicators and return a unified snapshot.
    This is what the Macro Agent and regime detector consume.
    """
    series_ids = ["FEDFUNDS", "DGS10", "DGS2", "T10YIE", "VIXCLS",
                  "DTWEXBGS", "BAMLH0A0HYM2", "BAMLC0A0CM", "ECBDFR"]

    readings = {}
    for sid in series_ids:
        r = get_macro_value(sid)
        readings[sid] = r.get("value")

    # Derived values
    dgs10 = readings.get("DGS10") or 4.21
    t10yie = readings.get("T10YIE") or 2.34
    dgs2 = readings.get("DGS2") or 4.68
    real_yield_10y = round(dgs10 - t10yie, 4)
    yield_spread   = round(dgs10 - dgs2, 4)

    if yield_spread > 0.5:
        yield_curve = "normal"
    elif yield_spread < -0.1:
        yield_curve = "inverted"
    else:
        yield_curve = "flat"

    vix = readings.get("VIXCLS") or 14.2

    return {
        "fed_rate":        readings.get("FEDFUNDS"),
        "yield_10y":       readings.get("DGS10"),
        "yield_2y":        readings.get("DGS2"),
        "yield_spread":    yield_spread,
        "inflation_exp":   readings.get("T10YIE"),
        "real_yield_10y":  real_yield_10y,
        "vix":             vix,
        "dxy":             readings.get("DTWEXBGS"),
        "hy_spread":       readings.get("BAMLH0A0HYM2"),
        "ig_spread":       readings.get("BAMLC0A0CM"),
        "ecb_rate":        readings.get("ECBDFR"),
        "yield_curve":     yield_curve,
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
    }


def classify_regime(macro: dict) -> dict:
    """
    Classify current macro regime from Document 04 (6 regimes).
    Uses the macro snapshot dict as input.
    """
    vix   = macro.get("vix") or 14.2
    hy    = macro.get("hy_spread") or 3.5
    yc    = macro.get("yield_curve", "normal")
    inf   = macro.get("inflation_exp") or 2.3
    real  = macro.get("real_yield_10y") or 1.9

    # Crisis
    if vix > 35 or hy > 7.0:
        return {
            "regime": "Crisis",
            "confidence": 0.90,
            "favorable_markets": ["bonds", "commodities"],
            "unfavorable_markets": ["crypto", "stocks", "real_estate"],
            "reasoning": f"VIX={vix:.1f} or HY spread={hy:.2f}% signals crisis conditions.",
        }

    # Risk-Off
    if vix > 22 or hy > 4.5:
        return {
            "regime": "Risk-Off",
            "confidence": 0.78,
            "favorable_markets": ["bonds", "commodities"],
            "unfavorable_markets": ["crypto", "stocks"],
            "reasoning": f"Elevated VIX={vix:.1f} and credit spreads signal fear/risk-off.",
        }

    # Stagflationary
    if inf > 3.5 and real < 0.5:
        return {
            "regime": "Stagflationary",
            "confidence": 0.65,
            "favorable_markets": ["commodities"],
            "unfavorable_markets": ["bonds", "stocks", "crypto"],
            "reasoning": f"High inflation expectations ({inf:.1f}%) + low real yield = stagflation risk.",
        }

    # Inflationary
    if inf > 3.0:
        return {
            "regime": "Inflationary",
            "confidence": 0.72,
            "favorable_markets": ["commodities", "real_estate"],
            "unfavorable_markets": ["bonds"],
            "reasoning": f"Inflation expectations ({inf:.1f}%) above 3% drives commodity preference.",
        }

    # Deflationary
    if inf < 1.5 and real > 2.5:
        return {
            "regime": "Deflationary",
            "confidence": 0.60,
            "favorable_markets": ["bonds"],
            "unfavorable_markets": ["commodities"],
            "reasoning": f"Low inflation ({inf:.1f}%) + high real yields = deflationary pressure.",
        }

    # Default: Risk-On (Goldilocks)
    return {
        "regime": "Risk-On",
        "confidence": 0.68,
        "favorable_markets": ["stocks", "crypto", "real_estate"],
        "unfavorable_markets": ["bonds"],
        "reasoning": f"VIX={vix:.1f} (low), inflation moderate, credit spreads contained. Risk-On.",
    }
