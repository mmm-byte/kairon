"""
kairon/engine/risk_engine.py
Position sizing, drawdown protection, stop-loss, Kelly Criterion.
Implements all three risk levels from Document 08.
"""
import math
import logging
from dataclasses import dataclass
from typing import Optional

from kairon.config import cfg

logger = logging.getLogger("kairon.risk")

MARKET_RISK_MULTIPLIERS = {
    "bonds":       0.75,
    "real_estate": 0.85,
    "stocks":      1.00,
    "forex":       1.10,
    "commodities": 1.25,
    "crypto":      1.80,
}

VOLATILITY_SCALE = {"Low": 1.00, "Medium": 0.75, "High": 0.50}

STOP_LOSS_BY_VOL = {"Low": 0.020, "Medium": 0.035, "High": 0.060}

ATR_THRESHOLDS = {
    "stocks":      (0.010, 0.025),
    "crypto":      (0.030, 0.060),
    "forex":       (0.003, 0.008),
    "commodities": (0.015, 0.035),
    "bonds":       (0.005, 0.012),
    "real_estate": (0.010, 0.020),
}


@dataclass
class PositionRecommendation:
    viable:             bool
    reason:             str
    position_usd:       float = 0.0
    position_pct:       float = 0.0
    stop_loss_pct:      float = 0.0
    stop_loss_price:    float = 0.0
    take_profit_pct:    float = 0.0
    take_profit_price:  float = 0.0
    max_loss_usd:       float = 0.0
    target_profit_usd:  float = 0.0
    risk_reward_ratio:  float = 0.0
    kelly_raw:          float = 0.0
    kelly_final:        float = 0.0
    volatility_regime:  str   = "Medium"

    def to_dict(self) -> dict:
        return {
            "viable":            self.viable,
            "reason":            self.reason,
            "position_usd":      round(self.position_usd, 2),
            "position_pct":      round(self.position_pct, 4),
            "stop_loss_pct":     round(self.stop_loss_pct, 4),
            "stop_loss_price":   round(self.stop_loss_price, 4),
            "take_profit_pct":   round(self.take_profit_pct, 4),
            "take_profit_price": round(self.take_profit_price, 4),
            "max_loss_usd":      round(self.max_loss_usd, 2),
            "target_profit_usd": round(self.target_profit_usd, 2),
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "kelly_raw":         round(self.kelly_raw, 4),
            "kelly_final":       round(self.kelly_final, 4),
            "volatility_regime": self.volatility_regime,
        }


def classify_volatility(atr_pct: float, market: str) -> str:
    lo, hi = ATR_THRESHOLDS.get(market, (0.01, 0.03))
    if atr_pct <= lo:  return "Low"
    if atr_pct >= hi:  return "High"
    return "Medium"


def kelly_fraction(win_prob: float, expected_return: float, stop_loss_pct: float) -> float:
    """Half-Kelly calculation from Document 08."""
    if not (0 < win_prob < 1):
        return 0.0
    b = expected_return / max(stop_loss_pct, 0.001)
    q = 1 - win_prob
    full_kelly = (win_prob * b - q) / b
    return max(0.0, full_kelly * 0.50)  # half-Kelly safety


def calculate_position(
    win_probability:   float,
    expected_return:   float,
    market:            str,
    atr_pct:           float,
    current_price:     float,
    available_capital: float,
    current_drawdown:  float,
    total_cost_pct:    float,
) -> PositionRecommendation:
    """Full position sizing calculation (Document 08 §5)."""

    # Gate 1: Drawdown
    if current_drawdown >= cfg.max_drawdown_pct:
        return PositionRecommendation(
            viable=False,
            reason=f"Portfolio drawdown {current_drawdown:.1%} exceeds {cfg.max_drawdown_pct:.0%} limit. No new positions.",
        )

    # Gate 2: Minimum confidence
    if win_probability < 0.50:
        return PositionRecommendation(
            viable=False,
            reason=f"Confidence {win_probability:.0%} below 50% minimum threshold.",
        )

    # Gate 3: Net profit
    net_return = expected_return - (total_cost_pct / 100)
    if net_return < cfg.min_net_profit_pct:
        return PositionRecommendation(
            viable=False,
            reason=f"Net return {net_return:.3%} below minimum {cfg.min_net_profit_pct:.3%} after costs.",
        )

    vol_regime  = classify_volatility(atr_pct, market)
    stop_pct    = STOP_LOSS_BY_VOL[vol_regime]

    raw_kelly   = kelly_fraction(win_probability, expected_return, stop_pct)
    mkt_kelly   = raw_kelly / MARKET_RISK_MULTIPLIERS.get(market, 1.0)
    vol_kelly   = mkt_kelly * VOLATILITY_SCALE[vol_regime]
    final_frac  = min(vol_kelly, cfg.max_position_pct)

    position_usd = final_frac * available_capital

    take_profit_pct   = max(net_return * 2.0, net_return + stop_pct)
    max_loss_usd      = position_usd * stop_pct
    target_profit_usd = position_usd * take_profit_pct
    rr_ratio          = take_profit_pct / stop_pct if stop_pct > 0 else 0

    reason = (f"Kelly {raw_kelly:.1%} → market adj {mkt_kelly:.1%} "
              f"→ vol adj {vol_kelly:.1%} → capped at {final_frac:.1%}")

    return PositionRecommendation(
        viable=True,
        reason=reason,
        position_usd=round(position_usd, 2),
        position_pct=round(final_frac, 4),
        stop_loss_pct=round(stop_pct, 4),
        stop_loss_price=round(current_price * (1 - stop_pct), 4),
        take_profit_pct=round(take_profit_pct, 4),
        take_profit_price=round(current_price * (1 + take_profit_pct), 4),
        max_loss_usd=round(max_loss_usd, 2),
        target_profit_usd=round(target_profit_usd, 2),
        risk_reward_ratio=round(rr_ratio, 2),
        kelly_raw=round(raw_kelly, 4),
        kelly_final=round(final_frac, 4),
        volatility_regime=vol_regime,
    )


class PortfolioMonitor:
    """Tracks portfolio-level risk metrics."""

    def __init__(self, total_capital: float):
        self.total_capital   = total_capital
        self.peak_capital    = total_capital
        self.current_capital = total_capital

    @property
    def current_drawdown(self) -> float:
        return max(0.0, (self.peak_capital - self.current_capital) / self.peak_capital)

    @property
    def is_halted(self) -> bool:
        return self.current_drawdown >= cfg.max_drawdown_pct

    def update_capital(self, new_capital: float) -> None:
        self.current_capital = new_capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital

    def check_concentration(self, asset: str, new_amount: float,
                             existing_positions: dict) -> dict:
        existing_val = existing_positions.get(asset, {}).get("value", 0.0)
        total_in_asset = existing_val + new_amount
        concentration = total_in_asset / self.total_capital
        if concentration > cfg.max_position_pct:
            max_add = max(0.0, cfg.max_position_pct * self.total_capital - existing_val)
            return {
                "allowed": False,
                "max_additional": round(max_add, 2),
                "reason": f"{asset} would be {concentration:.0%} of portfolio (max {cfg.max_position_pct:.0%})",
            }
        return {"allowed": True, "max_additional": new_amount}

    def get_crisis_actions(self, regime: str) -> list[str]:
        actions = []
        if self.is_halted:
            actions.append("HALT: All new positions suspended until drawdown recovers below 10%")
        if regime == "Crisis":
            actions.append("REDUCE: All risk assets. Shift to cash/short-duration bonds.")
            actions.append("HOLD: Gold and short-term Treasuries only.")
        return actions

    def to_dict(self) -> dict:
        return {
            "total_capital":    round(self.total_capital, 2),
            "current_capital":  round(self.current_capital, 2),
            "peak_capital":     round(self.peak_capital, 2),
            "current_drawdown": round(self.current_drawdown, 4),
            "is_halted":        self.is_halted,
        }
