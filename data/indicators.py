"""
kairon/data/indicators.py
Computes all 25 technical indicators from Document 04.
Pure pandas + numpy — no external TA library required.
"""
import math
import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger("kairon.indicators")


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff().fillna(0))
    return (sign * volume).cumsum()


def compute_all(df: pd.DataFrame, market_type: str = "stocks") -> dict:
    """
    Compute all 25 indicators on an OHLCV DataFrame.
    Returns a flat dict of indicator values (latest bar).
    Handles insufficient data gracefully.
    """
    if df is None or len(df) < 30:
        logger.warning(f"Insufficient data for indicators: {len(df) if df is not None else 0} rows")
        return _empty_indicators()

    close  = df["close"]
    high   = df.get("high", close)
    low    = df.get("low", close)
    volume = df.get("volume", pd.Series(0, index=df.index))

    try:
        # Moving averages
        sma_10 = _sma(close, 10)
        sma_20 = _sma(close, 20)
        sma_50 = _sma(close, 50) if len(df) >= 50 else _sma(close, len(df) // 2)
        ema_12 = _ema(close, 12)
        ema_26 = _ema(close, 26)

        # MACD
        macd_line   = ema_12 - ema_26
        macd_signal = _ema(macd_line, 9)
        macd_hist   = macd_line - macd_signal

        # RSI
        rsi = _rsi(close, 14)

        # Bollinger Bands
        std_20    = close.rolling(20).std()
        bb_upper  = sma_20 + 2 * std_20
        bb_lower  = sma_20 - 2 * std_20
        bb_width  = (bb_upper - bb_lower) / sma_20.replace(0, np.nan)
        bb_pos    = (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

        # ATR and volatility
        atr        = _atr(high, low, close, 14)
        atr_pct    = atr / close.replace(0, np.nan)
        vol_20d    = close.pct_change().rolling(20).std()

        # Volume
        vol_sma_20  = volume.rolling(20).mean()
        vol_ratio   = volume / vol_sma_20.replace(0, np.nan)

        # OBV
        obv = _obv(close, volume)

        # Returns / momentum
        ret_1d     = close.pct_change(1)
        ret_5d     = close.pct_change(5)
        ret_20d    = close.pct_change(20)
        momentum_10 = close / close.shift(10).replace(0, np.nan) - 1

        # Z-score
        z_score_20 = (close - sma_20) / std_20.replace(0, np.nan)

        # Intraday stats
        close_open = (close - df.get("open", close)) / df.get("open", close).replace(0, np.nan)
        hl_pct     = (high - low) / close.replace(0, np.nan)

        def last(s: pd.Series) -> Optional[float]:
            v = s.dropna()
            if len(v) == 0:
                return None
            return round(float(v.iloc[-1]), 6)

        indicators = {
            # Trend
            "sma_10":      last(sma_10),
            "sma_20":      last(sma_20),
            "sma_50":      last(sma_50),
            "ema_12":      last(ema_12),
            "ema_26":      last(ema_26),
            # MACD
            "macd":        last(macd_line),
            "macd_signal": last(macd_signal),
            "macd_hist":   last(macd_hist),
            # Momentum
            "rsi":         last(rsi),
            # Bollinger
            "bb_upper":    last(bb_upper),
            "bb_lower":    last(bb_lower),
            "bb_width":    last(bb_width),
            "bb_pos":      last(bb_pos),
            # Volatility
            "atr":         last(atr),
            "atr_pct":     last(atr_pct),
            "volatility_20d": last(vol_20d),
            # Volume
            "vol_sma_20":  last(vol_sma_20),
            "vol_ratio":   last(vol_ratio),
            "obv":         last(obv),
            # Returns
            "return_1d":   last(ret_1d),
            "return_5d":   last(ret_5d),
            "return_20d":  last(ret_20d),
            "momentum_10": last(momentum_10),
            # Other
            "z_score_20":  last(z_score_20),
            "close_open":  last(close_open),
            "hl_pct":      last(hl_pct),
            # Current price
            "close":       last(close),
            "volume":      last(volume),
            # Derived trend label
            "trend":       _classify_trend(last(sma_10), last(sma_20), last(sma_50), last(close)),
            # Market type (passed through for scoring)
            "market_type": market_type,
        }

        return indicators

    except Exception as e:
        logger.error(f"Indicator computation failed: {e}", exc_info=True)
        return _empty_indicators()


def _classify_trend(sma10: Optional[float], sma20: Optional[float],
                    sma50: Optional[float], close: Optional[float]) -> str:
    if None in (sma10, sma20, sma50, close):
        return "neutral"
    if sma10 > sma20 > sma50:
        return "bullish"
    if sma10 < sma20 < sma50:
        return "bearish"
    if close > sma50:
        return "mixed_bullish"
    return "mixed_bearish"


def _empty_indicators() -> dict:
    """Return a zero-filled indicator dict for graceful degradation."""
    return {k: None for k in [
        "sma_10", "sma_20", "sma_50", "ema_12", "ema_26",
        "macd", "macd_signal", "macd_hist", "rsi",
        "bb_upper", "bb_lower", "bb_width", "bb_pos",
        "atr", "atr_pct", "volatility_20d",
        "vol_sma_20", "vol_ratio", "obv",
        "return_1d", "return_5d", "return_20d", "momentum_10",
        "z_score_20", "close_open", "hl_pct",
        "close", "volume", "trend", "market_type",
    ]}


def score_technical(indicators: dict, market_type: str = "stocks") -> float:
    """
    Full Technical Analyst scoring from Document 04.
    Returns a float in [-1.0, +1.0].
    """
    ind = indicators
    score = 0.0

    # Guard: if we have no data, return 0
    if ind.get("close") is None:
        return 0.0

    # ── Trend (30%) ──────────────────────────────────────────────────────────
    sma10, sma20, sma50 = ind.get("sma_10"), ind.get("sma_20"), ind.get("sma_50")
    close = ind.get("close", 0)
    if sma10 and sma20 and sma50:
        if sma10 > sma20 > sma50:
            score += 0.30
        elif sma10 < sma20 < sma50:
            score -= 0.30
        else:
            score += 0.10 * (1 if close > sma50 else -1)

    # ── Momentum RSI (25%) ───────────────────────────────────────────────────
    rsi = ind.get("rsi")
    if rsi is not None:
        if 40 < rsi < 70:
            score += 0.25 * (rsi - 55) / 15
        elif rsi >= 75:
            score -= 0.15
        elif rsi <= 25:
            score += 0.15

    # ── MACD (20%) ───────────────────────────────────────────────────────────
    macd_hist = ind.get("macd_hist")
    macd_val  = ind.get("macd")
    if macd_hist is not None and macd_val is not None:
        if macd_hist > 0 and macd_val > 0:
            score += 0.20
        elif macd_hist < 0 and macd_val < 0:
            score -= 0.20

    # ── Volume confirmation (15%) ────────────────────────────────────────────
    vol_ratio = ind.get("vol_ratio")
    ret_1d    = ind.get("return_1d")
    if vol_ratio is not None and ret_1d is not None:
        if vol_ratio > 1.3 and ret_1d > 0:
            score += 0.15
        elif vol_ratio > 1.3 and ret_1d < 0:
            score -= 0.15

    # ── Bollinger position (10%) ─────────────────────────────────────────────
    bb = ind.get("bb_pos")
    if bb is not None:
        if bb > 0.85:
            score -= 0.10
        elif bb < 0.15:
            score += 0.10

    # ── Market-type adjustments ──────────────────────────────────────────────
    if market_type == "crypto":
        score *= 0.85
    elif market_type == "bonds":
        score *= 0.70

    return max(-1.0, min(1.0, round(score, 4)))
