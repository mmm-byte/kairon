"""
kairon/intelligence/correlation_tracker.py
Dynamic correlation matrix from Document 06.
Computes rolling correlations across all markets, separated by regime.
Updates daily via scheduler. Detects correlation regime shifts and contagion.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from kairon.db import database as db

logger = logging.getLogger("kairon.correlation")

# ── Asset pairs to track (Document 06) ───────────────────────────────────────
TRACKED_PAIRS = [
    ("^GSPC",   "BTC-USD",  "SPX_BTC"),
    ("^GSPC",   "GC=F",     "SPX_Gold"),
    ("^GSPC",   "CL=F",     "SPX_Oil"),
    ("GC=F",    "DX-Y.NYB", "Gold_DXY"),
    ("BTC-USD", "ETH-USD",  "BTC_ETH"),
    ("GC=F",    "SI=F",     "Gold_Silver"),
    ("^GSPC",   "^TNX",     "SPX_10Y"),
    ("CL=F",    "HG=F",     "Oil_Copper"),
    ("^TNX",    "DX-Y.NYB", "Yield_DXY"),
]

# Expected regime correlation ranges (Document 06 §3)
REGIME_EXPECTED = {
    "Risk-On":      {"SPX_BTC": (0.25, 0.55), "SPX_Gold": (-0.35, -0.10),
                     "Gold_DXY": (-0.75, -0.55), "BTC_ETH": (0.80, 0.95)},
    "Risk-Off":     {"SPX_BTC": (0.55, 0.80), "SPX_Gold": (-0.65, -0.40),
                     "Gold_DXY": (-0.45, -0.20), "BTC_ETH": (0.88, 0.98)},
    "Crisis":       {"SPX_BTC": (0.80, 0.95), "SPX_Gold": (-0.75, -0.55),
                     "Gold_DXY": (0.30, 0.60),  "BTC_ETH": (0.92, 0.99)},
    "Inflationary": {"SPX_BTC": (0.30, 0.55), "SPX_Gold": (-0.20, 0.10),
                     "Gold_DXY": (-0.65, -0.45), "BTC_ETH": (0.78, 0.92)},
}


def _safe_corr(s1: pd.Series, s2: pd.Series, window: int = 60) -> float:
    """Rolling correlation between two return series, clamped to [-1, 1]."""
    r1 = s1.pct_change().dropna()
    r2 = s2.pct_change().dropna()
    aligned = pd.concat([r1, r2], axis=1).dropna()
    if len(aligned) < 20:
        return float("nan")
    corr = aligned.iloc[:, 0].rolling(window).corr(aligned.iloc[:, 1]).iloc[-1]
    if pd.isna(corr):
        return float("nan")
    return round(float(np.clip(corr, -1.0, 1.0)), 4)


def compute_correlation_matrix(regime: str = "Risk-On") -> dict:
    """
    Compute current rolling correlations for all tracked pairs.
    Uses demo data when live data is unavailable.
    """
    from kairon.data.market_data import fetch_ohlcv

    closes: dict[str, pd.Series] = {}
    for pair in TRACKED_PAIRS:
        for ticker in (pair[0], pair[1]):
            if ticker not in closes:
                result = fetch_ohlcv(ticker, period="6mo")
                df     = result.get("df")
                if df is not None and not df.empty:
                    closes[ticker] = df["close"]

    correlations: dict[str, float] = {}
    for t1, t2, label in TRACKED_PAIRS:
        if t1 in closes and t2 in closes:
            corr = _safe_corr(closes[t1], closes[t2])
            correlations[label] = corr
        else:
            correlations[label] = float("nan")

    # Fill NaN with regime defaults for display
    defaults = REGIME_EXPECTED.get(regime, REGIME_EXPECTED["Risk-On"])
    for label, (lo, hi) in defaults.items():
        if label not in correlations or pd.isna(correlations.get(label, float("nan"))):
            correlations[label] = round((lo + hi) / 2, 3)

    return correlations


def detect_contagion(correlations: dict, regime: str) -> dict:
    """
    Compare current correlations to expected regime ranges.
    Elevated correlations signal contagion (everything moves together).
    """
    alerts = []
    expected = REGIME_EXPECTED.get(regime, {})

    for label, corr in correlations.items():
        if pd.isna(corr) or label not in expected:
            continue
        lo, hi = expected[label]
        if corr > hi + 0.15:
            alerts.append({
                "pair":    label,
                "current": corr,
                "expected_range": f"{lo:.2f}–{hi:.2f}",
                "type":    "elevated",
                "message": f"{label} correlation {corr:.2f} above expected {hi:.2f} — contagion risk",
            })
        elif corr < lo - 0.15:
            alerts.append({
                "pair":    label,
                "current": corr,
                "expected_range": f"{lo:.2f}–{hi:.2f}",
                "type":    "suppressed",
                "message": f"{label} correlation {corr:.2f} below expected {lo:.2f} — decoupling",
            })

    # Overall correlation regime
    avg_abs   = np.nanmean([abs(v) for v in correlations.values()])
    spx_btc   = correlations.get("SPX_BTC", 0.4)
    contagion  = avg_abs > 0.65 or (not pd.isna(spx_btc) and spx_btc > 0.75)

    return {
        "alerts":        alerts,
        "contagion":     contagion,
        "avg_abs_corr":  round(avg_abs, 3),
        "regime":        regime,
        "severity":      "high" if contagion else ("medium" if alerts else "low"),
    }


def snapshot_and_save(regime: str = "Risk-On") -> dict:
    """Compute correlations, save to DB, return the snapshot."""
    correlations = compute_correlation_matrix(regime)
    contagion    = detect_contagion(correlations, regime)

    import json
    snap_id = str(uuid.uuid4())
    try:
        db.insert("correlation_snapshots", {
            "id":               snap_id,
            "regime":           regime,
            "correlations":     json.dumps(correlations),
            "spx_btc":          correlations.get("SPX_BTC"),
            "spx_gold":         correlations.get("SPX_Gold"),
            "spx_oil":          correlations.get("SPX_Oil"),
            "gold_dxy":         correlations.get("Gold_DXY"),
            "btc_eth":          correlations.get("BTC_ETH"),
        })
        logger.info(f"Correlation snapshot saved: {snap_id[:8]} | regime={regime} | "
                    f"SPX/BTC={correlations.get('SPX_BTC')}")
    except Exception as e:
        logger.error(f"Failed to save correlation snapshot: {e}")

    return {
        "snapshot_id":   snap_id,
        "correlations":  correlations,
        "contagion":     contagion,
        "regime":        regime,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }


def get_latest_snapshot() -> Optional[dict]:
    """Get the most recent correlation snapshot from DB."""
    import json
    row = db.execute_one(
        "SELECT * FROM correlation_snapshots ORDER BY captured_at DESC LIMIT 1"
    )
    if not row:
        return None
    try:
        row["correlations"] = json.loads(row["correlations"])
    except Exception:
        pass
    return row


def get_correlation_heatmap_data(regime: str = "Risk-On") -> dict:
    """
    Build a correlation heatmap data structure for the UI.
    Returns a symmetric matrix of {pair: corr} plus color-coding.
    """
    correlations = compute_correlation_matrix(regime)

    def corr_color(v: float) -> str:
        if pd.isna(v): return "#3d4558"
        if v > 0.7:    return "#00e676"
        if v > 0.4:    return "#4CAF50"
        if v > 0.1:    return "#8BC34A"
        if v > -0.1:   return "#ffb300"
        if v > -0.4:   return "#FF7043"
        if v > -0.7:   return "#ff3d57"
        return "#B71C1C"

    heatmap = []
    for label, corr in correlations.items():
        parts = label.split("_", 1)
        heatmap.append({
            "pair":     label,
            "asset1":   parts[0],
            "asset2":   parts[1] if len(parts) > 1 else label,
            "corr":     corr if not pd.isna(corr) else 0.0,
            "color":    corr_color(corr),
            "label":    f"{corr:+.2f}" if not pd.isna(corr) else "N/A",
            "strength": abs(corr) if not pd.isna(corr) else 0.0,
        })

    heatmap.sort(key=lambda x: abs(x["corr"]), reverse=True)
    return {"heatmap": heatmap, "regime": regime,
            "generated_at": datetime.now(timezone.utc).isoformat()}
