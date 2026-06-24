"""
kairon/intelligence/correlations.py
Dynamic correlation model from Document 06.
Maintains three correlation matrices (calm, fear, crisis) and
transitions between them based on real-time VIX + eigenvalue regime detection.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from kairon.db import database as db
from kairon.data import cache as cache_mod

logger = logging.getLogger("kairon.correlations")

# ── Static correlation matrices by regime (Document 06) ───────────────────────
CORRELATIONS = {
    "calm": {
        "SPX_BTC":     0.35,
        "SPX_Gold":   -0.20,
        "SPX_Oil":     0.30,
        "SPX_10Y":    -0.50,
        "SPX_EURUSD":  0.10,
        "Gold_DXY":   -0.68,
        "Gold_Silver": 0.82,
        "Gold_RealY": -0.74,
        "BTC_ETH":     0.88,
        "Oil_CADUSD":  0.71,
        "Oil_Gold":    0.25,
        "EURUSD_DXY": -0.95,
        "10Y_2Y":      0.87,
        "REITs_10Y":  -0.65,
    },
    "fear": {
        "SPX_BTC":     0.65,
        "SPX_Gold":   -0.55,
        "SPX_Oil":     0.55,
        "SPX_10Y":    -0.70,
        "SPX_EURUSD":  0.05,
        "Gold_DXY":   -0.30,
        "Gold_Silver": 0.78,
        "Gold_RealY": -0.82,
        "BTC_ETH":     0.92,
        "Oil_CADUSD":  0.60,
        "Oil_Gold":    0.35,
        "EURUSD_DXY": -0.95,
        "10Y_2Y":      0.80,
        "REITs_10Y":  -0.75,
    },
    "crisis": {
        "SPX_BTC":     0.88,
        "SPX_Gold":   -0.70,
        "SPX_Oil":     0.82,
        "SPX_10Y":    -0.80,
        "SPX_EURUSD":  0.15,
        "Gold_DXY":    0.45,   # both surge in liquidity crises
        "Gold_Silver": 0.72,
        "Gold_RealY": -0.85,
        "BTC_ETH":     0.95,
        "Oil_CADUSD":  0.50,
        "Oil_Gold":    0.55,
        "EURUSD_DXY": -0.92,
        "10Y_2Y":      0.75,
        "REITs_10Y":  -0.85,
    },
}

# Tickers used for live correlation computation
CORRELATION_TICKERS = {
    "SPX":    "^GSPC",
    "BTC":    "BTC-USD",
    "Gold":   "GC=F",
    "Oil":    "CL=F",
    "Silver": "SI=F",
    "10Y":    "^TNX",
    "2Y":     "^IRX",
    "EURUSD": "EURUSD=X",
    "REITs":  "VNQ",
    "ETH":    "ETH-USD",
}


def get_vix_regime(vix: float, vix_7d_change: float = 0.0) -> str:
    """VIX-based regime from Document 06."""
    if vix > 35:
        return "crisis"
    if vix > 22 or (vix > 18 and vix_7d_change > 4):
        return "fear"
    if vix < 16 and vix_7d_change <= 0:
        return "calm"
    return "transitioning"


def detect_correlation_regime(returns_df: pd.DataFrame) -> tuple[str, float]:
    """
    Eigenvalue method from Document 06.
    Ratio of largest to second-largest eigenvalue reveals concentration.
    """
    if returns_df.shape[0] < 20 or returns_df.shape[1] < 3:
        return "calm", 1.0

    try:
        clean = returns_df.dropna(axis=1, how="any").dropna()
        if clean.shape[0] < 10 or clean.shape[1] < 3:
            return "calm", 1.0
        corr_matrix = np.corrcoef(clean.T)
        eigenvalues = np.sort(np.linalg.eigvalsh(corr_matrix))[::-1]
        ratio = eigenvalues[0] / eigenvalues[1] if eigenvalues[1] > 0.001 else 1.0
        if ratio > 4.0:  return "crisis", round(ratio, 2)
        if ratio > 2.5:  return "fear",   round(ratio, 2)
        return "calm",   round(ratio, 2)
    except Exception as e:
        logger.debug(f"Eigenvalue computation failed: {e}")
        return "calm", 1.0


def compute_live_correlations(days: int = 60) -> dict:
    """
    Fetch recent prices for all tracked tickers and compute live pairwise correlations.
    Falls back to static matrix when data is unavailable.
    """
    from kairon.data.market_data import fetch_ohlcv

    returns_dict = {}
    for name, ticker in CORRELATION_TICKERS.items():
        try:
            data = fetch_ohlcv(ticker, period="3mo")
            df   = data.get("df")
            if df is not None and len(df) >= 20:
                returns_dict[name] = df["close"].pct_change().dropna().tail(days)
        except Exception as e:
            logger.debug(f"Could not fetch {ticker} for correlation: {e}")

    if len(returns_dict) < 3:
        logger.warning("Insufficient data for live correlations — using static matrices")
        return {}

    # Align all series on common dates
    returns_df = pd.DataFrame(returns_dict).dropna()
    if returns_df.shape[0] < 10:
        return {}

    # Compute pairwise correlations for key pairs
    live_corr  = {}
    name_pairs = [
        ("SPX", "BTC", "SPX_BTC"),
        ("SPX", "Gold","SPX_Gold"),
        ("Gold","ETH", "Gold_ETH"),
        ("BTC", "ETH", "BTC_ETH"),
    ]
    for n1, n2, key in name_pairs:
        if n1 in returns_df and n2 in returns_df:
            c = float(returns_df[n1].corr(returns_df[n2]))
            if not (c != c):  # nan check
                live_corr[key] = round(c, 3)

    # Regime detection
    eigen_regime, eigen_ratio = detect_correlation_regime(returns_df)
    live_corr["_eigen_regime"] = eigen_regime
    live_corr["_eigen_ratio"]  = eigen_ratio

    return live_corr


def get_correlation_matrix(regime: str, live_override: dict = None) -> dict:
    """
    Get the appropriate correlation matrix for the current regime,
    optionally blended with live-computed values.
    """
    base = CORRELATIONS.get(regime, CORRELATIONS["calm"]).copy()

    if live_override:
        for pair, val in live_override.items():
            if not pair.startswith("_") and pair in base:
                # Blend: 70% static (stable), 30% live (responsive)
                base[pair] = round(0.70 * base[pair] + 0.30 * val, 3)

    return base


def get_asset_correlations(asset: str, market: str, regime: str) -> dict:
    """
    Return correlations relevant to a specific asset/market for the connection map.
    """
    matrix = get_correlation_matrix(regime)

    relevant = {}
    if market == "commodities" and "gold" in asset.lower():
        relevant = {
            "vs Dollar (DXY)":  matrix["Gold_DXY"],
            "vs Silver":        matrix["Gold_Silver"],
            "vs Real Yield":    matrix["Gold_RealY"],
            "vs S&P 500":       matrix["SPX_Gold"],
            "vs Oil":           matrix["Oil_Gold"],
        }
    elif market == "crypto":
        relevant = {
            "vs S&P 500":  matrix["SPX_BTC"],
            "vs ETH":      matrix["BTC_ETH"],
        }
    elif market == "stocks":
        relevant = {
            "vs Bitcoin":  matrix["SPX_BTC"],
            "vs Gold":     matrix["SPX_Gold"],
            "vs Oil":      matrix["SPX_Oil"],
            "vs 10Y":      matrix["SPX_10Y"],
        }
    elif market == "bonds":
        relevant = {
            "vs S&P 500":  matrix["SPX_10Y"],
            "vs REITs":    matrix["REITs_10Y"],
            "vs 2Y":       matrix["10Y_2Y"],
        }
    elif market == "forex":
        relevant = {
            "vs DXY":      matrix["EURUSD_DXY"],
            "vs S&P 500":  matrix["SPX_EURUSD"],
        }
    elif market == "real_estate":
        relevant = {
            "vs 10Y yield": matrix["REITs_10Y"],
            "vs S&P 500":   matrix.get("SPX_REITs", 0.45),
        }

    return relevant


def save_correlation_snapshot(regime: str, matrix: dict, eigen_ratio: float = 0.0) -> str:
    """Persist the current correlation snapshot for historical tracking."""
    snap_id = str(uuid.uuid4())
    db.insert("correlation_snapshots", {
        "id":               snap_id,
        "regime":           regime,
        "correlations":     str(matrix),
        "eigenvalue_ratio": round(eigen_ratio, 3),
        "spx_btc":          matrix.get("SPX_BTC"),
        "spx_gold":         matrix.get("SPX_Gold"),
        "spx_oil":          matrix.get("SPX_Oil"),
        "gold_dxy":         matrix.get("Gold_DXY"),
        "btc_eth":          matrix.get("BTC_ETH"),
    })
    return snap_id


def get_contagion_alert(regime: str, asset: str, market: str) -> Optional[dict]:
    """
    Determine if there is a cross-market contagion risk for this asset.
    Returns alert dict or None.
    """
    if regime not in ("crisis", "fear"):
        return None

    matrix = get_correlation_matrix(regime)
    spx_corr = matrix.get("SPX_BTC" if market == "crypto" else "SPX_Gold", 0)

    if regime == "crisis":
        return {
            "level":   "HIGH",
            "message": (
                f"CRISIS REGIME: Correlations collapsing — all risk assets moving together. "
                f"{asset} correlation with S&P 500: {spx_corr:+.2f}. "
                f"Diversification benefit severely reduced."
            ),
            "recommended_action": "Reduce all risk exposure. Cash/short-term treasuries only.",
        }
    if regime == "fear" and abs(spx_corr) > 0.5:
        return {
            "level":   "MEDIUM",
            "message": (
                f"FEAR REGIME: Cross-asset correlation elevated. "
                f"{asset} correlation with equities: {spx_corr:+.2f}. "
                f"Expect coordinated moves."
            ),
            "recommended_action": "Reduce position sizes. Monitor VIX for escalation.",
        }
    return None
