"""
kairon/intelligence/signal_velocity.py
Signal velocity and acceleration tracking (Document 15, Section 9).
Tells users whether they're catching a trend early (better) or late (riskier).
"""
import logging
from typing import Optional
from dataclasses import dataclass

from kairon.db import database as db

logger = logging.getLogger("kairon.velocity")


@dataclass
class VelocityReading:
    agent:        str
    signal:       float
    velocity:     float      # rate of change (first derivative)
    acceleration: float      # rate of change of velocity (second derivative)
    trend:        str        # "accelerating" | "decelerating" | "steady"
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "agent":          self.agent,
            "signal":         round(self.signal, 4),
            "velocity":       round(self.velocity, 4),
            "acceleration":   round(self.acceleration, 4),
            "trend":          self.trend,
            "interpretation": self.interpretation,
        }


def compute_signal_velocity(
    signal_history: list[float],
    window: int = 5,
) -> dict:
    """
    Compute velocity and acceleration for a signal series.
    velocity    = total change over window (first derivative proxy)
    acceleration = recent change minus prior change (second derivative proxy)
    """
    if len(signal_history) < max(window, 3):
        return {
            "velocity":     0.0,
            "acceleration": 0.0,
            "trend":        "insufficient_data",
        }

    recent        = signal_history[-window:]
    velocity      = recent[-1] - recent[0]
    acc_recent    = recent[-1] - recent[-2]
    acc_prev      = recent[-2] - recent[-3] if len(recent) >= 3 else 0.0
    acceleration  = acc_recent - acc_prev

    if acceleration > 0.005:
        trend = "accelerating"
    elif acceleration < -0.005:
        trend = "decelerating"
    else:
        trend = "steady"

    return {
        "velocity":     round(velocity, 4),
        "acceleration": round(acceleration, 4),
        "trend":        trend,
    }


def get_signal_velocities_for_asset(asset: str, lookback: int = 10) -> list[VelocityReading]:
    """
    Pull recent prediction records for an asset and compute signal velocity
    for each agent. Used by the explainability panel.
    """
    rows = db.execute(
        """SELECT technical_score, fundamental_score, news_score,
                  macro_score, cross_market_score, composite_score
           FROM predictions
           WHERE asset=?
           ORDER BY created_at DESC LIMIT ?""",
        (asset, lookback),
    )

    if len(rows) < 3:
        return []

    # Reverse so oldest first
    rows = list(reversed(rows))

    agents = [
        ("technical",    "technical_score"),
        ("fundamental",  "fundamental_score"),
        ("news",         "news_score"),
        ("macro",        "macro_score"),
        ("cross_market", "cross_market_score"),
    ]

    readings = []
    for agent_name, col in agents:
        history = [r[col] for r in rows if r.get(col) is not None]
        if len(history) < 3:
            continue

        vel = compute_signal_velocity(history)
        current = history[-1]

        # Interpretation
        trend = vel["trend"]
        v     = vel["velocity"]
        if trend == "accelerating" and v > 0:
            interp = f"↑↑ {agent_name.replace('_',' ').title()} signal accelerating bullish — early in move"
        elif trend == "accelerating" and v < 0:
            interp = f"↓↓ {agent_name.replace('_',' ').title()} signal accelerating bearish"
        elif trend == "decelerating":
            interp = f"→ {agent_name.replace('_',' ').title()} signal slowing — momentum fading"
        else:
            interp = f"→ {agent_name.replace('_',' ').title()} signal steady"

        readings.append(VelocityReading(
            agent=agent_name,
            signal=round(current, 4),
            velocity=vel["velocity"],
            acceleration=vel["acceleration"],
            trend=trend,
            interpretation=interp,
        ))

    return readings


def get_overall_velocity_label(readings: list[VelocityReading]) -> str:
    """
    Summarise whether the overall signal is accelerating or fading.
    Used for the "Are we early or late?" UI note.
    """
    if not readings:
        return "Insufficient history to assess velocity"

    accel_count = sum(1 for r in readings if r.trend == "accelerating")
    decel_count = sum(1 for r in readings if r.trend == "decelerating")
    n           = len(readings)

    if accel_count >= n * 0.6:
        return "ACCELERATING → Signal is strengthening. Early in the move — better risk/reward."
    if decel_count >= n * 0.6:
        return "DECELERATING → Signal is fading. Late entry — consider waiting for re-entry."
    return "STEADY → Signal maintaining. Neither early nor late — watch for breakout."
