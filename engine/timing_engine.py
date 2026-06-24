"""
kairon/engine/timing_engine.py
Timing engine — Document 19.
Determines WHEN to act on a signal, not just whether to act.
Outputs urgency level, optimal entry window, event risk, and spread timing.
"""
import logging
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("kairon.timing")


# ── Urgency levels ────────────────────────────────────────────────────────────
class Urgency:
    IMMEDIATE = "IMMEDIATE"   # act within 2 hours
    SHORT     = "SHORT"       # 1–3 days
    MEDIUM    = "MEDIUM"      # 1–2 weeks
    PATIENT   = "PATIENT"     # 2+ weeks


URGENCY_LABELS = {
    Urgency.IMMEDIATE: "Act within 2 hours",
    Urgency.SHORT:     "1–3 day window",
    Urgency.MEDIUM:    "1–2 week window",
    Urgency.PATIENT:   "No urgency",
}

URGENCY_BADGE_COLORS = {
    Urgency.IMMEDIATE: "red",
    Urgency.SHORT:     "amber",
    Urgency.MEDIUM:    "blue",
    Urgency.PATIENT:   "gray",
}


# ── Optimal entry windows by asset class (Document 19) ───────────────────────
OPTIMAL_ENTRY_WINDOWS = {
    "stocks":      {"window": "14:45–16:00 UTC", "reason": "30-45min after NYSE open — liquidity established"},
    "stocks_eu":   {"window": "08:30–10:00 UTC", "reason": "After Frankfurt/London open, before US overlap"},
    "forex":       {"window": "08:00–12:00 UTC", "reason": "London session — highest forex volume globally"},
    "commodities": {"window": "13:30–16:00 UTC", "reason": "COMEX open + London/NY overlap — tightest spreads"},
    "bonds":       {"window": "14:35–15:30 UTC", "reason": "Post-NYSE open, peak ETF liquidity"},
    "crypto":      {"window": "12:00–16:00 UTC", "reason": "Avoid 00:00–06:00 UTC — low liquidity, wider spreads"},
    "real_estate": {"window": "14:35–15:30 UTC", "reason": "REIT ETFs trade as equities — NYSE hours"},
}

# Gold specifically has a London Metal Exchange fix
ASSET_SPECIFIC_WINDOWS = {
    "GC=F":    {"window": "10:30 UTC",          "reason": "London Metal Exchange fix sets global gold reference"},
    "CL=F":    {"window": "14:30–16:00 UTC",    "reason": "EIA report window + NY session — peak oil liquidity"},
    "ZW=F":    {"window": "14:30–19:20 UTC",    "reason": "CBOT grain session — most volume in US morning"},
    "HG=F":    {"window": "08:00–17:00 UTC",    "reason": "LME copper + COMEX overlap — best copper liquidity"},
    "SI=F":    {"window": "13:30–17:00 UTC",    "reason": "COMEX silver trading hours"},
    "EURUSD=X":{"window": "08:00–12:00 UTC",    "reason": "ECB/London overlap — EUR/USD peak volume"},
    "GBPUSD=X":{"window": "08:00–11:00 UTC",    "reason": "London morning session — GBP peak liquidity"},
    "BTC-USD": {"window": "14:00–18:00 UTC",    "reason": "NY session — highest BTC/USD liquidity"},
    "ETH-USD": {"window": "14:00–18:00 UTC",    "reason": "NY session — ETH/USD peak volume"},
}

# Avoid periods for each market
AVOID_WINDOWS = {
    "crypto":      "00:00–06:00 UTC (low liquidity, manipulation risk)",
    "stocks":      "09:30–09:45 UTC (opening volatility spike)",
    "forex":       "22:00–00:00 UTC (Tokyo-London gap)",
    "commodities": "Weekends (futures roll premium risk)",
}


# ── Economic calendar — known recurring events ────────────────────────────────
# Used as fallback when web scraping fails
RECURRING_EVENTS_2026 = [
    # FOMC meetings 2026
    {"name": "FOMC Rate Decision", "dates": [
        "2026-01-29", "2026-03-19", "2026-05-07", "2026-06-18",
        "2026-07-30", "2026-09-17", "2026-11-05", "2026-12-17",
    ], "impact": "high", "assets": ["bonds", "forex", "commodities", "stocks", "crypto"]},
    # US CPI — first week of each month
    {"name": "US CPI Release", "dates": [
        "2026-01-15","2026-02-12","2026-03-12","2026-04-14",
        "2026-05-13","2026-06-11","2026-07-15","2026-08-12",
        "2026-09-11","2026-10-14","2026-11-12","2026-12-11",
    ], "impact": "high", "assets": ["bonds", "forex", "commodities", "stocks"]},
    # Non-Farm Payroll — first Friday of month
    {"name": "Non-Farm Payroll", "dates": [
        "2026-01-09","2026-02-06","2026-03-06","2026-04-03",
        "2026-05-08","2026-06-05","2026-07-03","2026-08-07",
        "2026-09-04","2026-10-02","2026-11-06","2026-12-04",
    ], "impact": "high", "assets": ["forex", "stocks", "bonds"]},
    # ECB rate decisions
    {"name": "ECB Rate Decision", "dates": [
        "2026-01-30","2026-03-05","2026-04-17","2026-06-05",
        "2026-07-16","2026-09-10","2026-10-22","2026-12-10",
    ], "impact": "medium", "assets": ["forex", "bonds", "stocks"]},
    # OPEC meetings
    {"name": "OPEC Meeting", "dates": [
        "2026-02-03","2026-04-07","2026-06-02","2026-08-04",
        "2026-10-06","2026-12-01",
    ], "impact": "high", "assets": ["commodities"]},
    # US GDP
    {"name": "US GDP Release", "dates": [
        "2026-01-29","2026-04-29","2026-07-29","2026-10-28",
    ], "impact": "medium", "assets": ["stocks", "forex", "bonds"]},
]


@dataclass
class EventRisk:
    level:      str            # "none" | "low" | "medium" | "high"
    name:       Optional[str] = None
    days_away:  Optional[int] = None
    message:    Optional[str] = None
    action:     str = "monitor"  # "monitor" | "wait" | "reduce_size"

    def to_dict(self) -> dict:
        return {
            "level":     self.level,
            "name":      self.name,
            "days_away": self.days_away,
            "message":   self.message,
            "action":    self.action,
        }


@dataclass
class TimingRecommendation:
    urgency:            str
    urgency_label:      str
    urgency_color:      str
    optimal_entry:      str
    entry_reason:       str
    avoid_window:       Optional[str]
    event_risk:         EventRisk
    spread_note:        str
    recommended_action: str
    horizon_label:      str

    def to_dict(self) -> dict:
        return {
            "urgency":            self.urgency,
            "urgency_label":      self.urgency_label,
            "urgency_color":      self.urgency_color,
            "optimal_entry":      self.optimal_entry,
            "entry_reason":       self.entry_reason,
            "avoid_window":       self.avoid_window,
            "event_risk":         self.event_risk.to_dict(),
            "spread_note":        self.spread_note,
            "recommended_action": self.recommended_action,
            "horizon_label":      self.horizon_label,
        }


def get_upcoming_events(market: str, ticker: str, days_ahead: int = 14) -> list[dict]:
    """Find upcoming market-moving events relevant to this asset."""
    today = date.today()
    events = []

    for event in RECURRING_EVENTS_2026:
        # Check if this event is relevant to the market/ticker
        relevant_markets = event.get("assets", [])
        if market not in relevant_markets and ticker not in relevant_markets:
            continue

        for date_str in event["dates"]:
            try:
                ev_date = date.fromisoformat(date_str)
                delta   = (ev_date - today).days
                if 0 <= delta <= days_ahead:
                    events.append({
                        "name":       event["name"],
                        "date":       date_str,
                        "days_away":  delta,
                        "impact":     event["impact"],
                        "market":     market,
                    })
            except ValueError:
                pass

    return sorted(events, key=lambda e: e["days_away"])


def get_event_risk(market: str, ticker: str, urgency_days: int) -> EventRisk:
    """Classify event risk for an upcoming entry."""
    events = get_upcoming_events(market, ticker, days_ahead=urgency_days + 2)

    if not events:
        return EventRisk(level="none", action="monitor")

    # Most impactful upcoming event
    high_impact = [e for e in events if e["impact"] == "high"]
    soonest = high_impact[0] if high_impact else events[0]
    days    = soonest["days_away"]

    if days == 0:
        return EventRisk(
            level="high", name=soonest["name"], days_away=0,
            message=f"{soonest['name']} is TODAY — entry is high risk",
            action="wait",
        )
    if days <= 1:
        return EventRisk(
            level="high", name=soonest["name"], days_away=days,
            message=f"{soonest['name']} in {days} day — consider waiting",
            action="reduce_size",
        )
    if days <= 3 and soonest["impact"] == "high":
        return EventRisk(
            level="medium", name=soonest["name"], days_away=days,
            message=f"{soonest['name']} in {days} days — enter before or wait",
            action="monitor",
        )

    return EventRisk(
        level="low", name=soonest["name"], days_away=days,
        message=f"Nearest event: {soonest['name']} in {days} days",
        action="monitor",
    )


def _signal_velocity(composite_score: float, prev_composite: Optional[float],
                      force_type: str) -> float:
    """Estimate how fast the signal is changing."""
    if prev_composite is None:
        return abs(composite_score) * 0.5
    return abs(composite_score - prev_composite)


def classify_urgency(
    composite_score: float,
    force_type:      str,
    market:          str,
    ticker:          str,
    news_age_hours:  float   = 4.0,
    prev_composite:  Optional[float] = None,
) -> str:
    """
    Classify urgency level from Document 19.
    Returns one of: IMMEDIATE, SHORT, MEDIUM, PATIENT
    """
    strength  = abs(composite_score)
    velocity  = _signal_velocity(composite_score, prev_composite, force_type)
    is_crypto = market == "crypto"
    is_forex  = market == "forex"

    # IMMEDIATE: breaking news + strong signal + fast-moving market
    if (velocity > 0.15 and news_age_hours < 2
            and (is_crypto or is_forex) and strength > 0.6):
        return Urgency.IMMEDIATE

    # IMMEDIATE: extreme composite on fast market
    if strength > 0.80 and force_type == "news_catalyst":
        return Urgency.IMMEDIATE

    # SHORT: strong signal with nearby event risk
    events = get_upcoming_events(market, ticker, days_ahead=4)
    if events and strength > 0.5:
        return Urgency.SHORT

    # SHORT: strong signal, no major event risk
    if strength > 0.60:
        return Urgency.SHORT

    # MEDIUM: macro/fundamental shift (slow-moving)
    if force_type in ("macro_shift", "fundamental_value"):
        return Urgency.MEDIUM

    # MEDIUM: moderate signal
    if strength > 0.35:
        return Urgency.MEDIUM

    return Urgency.PATIENT


def get_timing_recommendation(
    composite_score: float,
    force_type:      str,
    market:          str,
    ticker:          str,
    horizon_days:    int,
    news_age_hours:  float = 4.0,
    vix:             float = 14.2,
    prev_composite:  Optional[float] = None,
) -> TimingRecommendation:
    """Full timing recommendation for a prediction."""

    urgency      = classify_urgency(composite_score, force_type, market, ticker,
                                     news_age_hours, prev_composite)
    event_risk   = get_event_risk(market, ticker, urgency_days=horizon_days)

    # Entry window
    window_info  = (ASSET_SPECIFIC_WINDOWS.get(ticker) or
                    OPTIMAL_ENTRY_WINDOWS.get(market) or
                    OPTIMAL_ENTRY_WINDOWS["stocks"])
    avoid        = AVOID_WINDOWS.get(market)

    # Spread note
    if vix > 30:
        spread_note = f"VIX={vix:.1f} (elevated) — spreads are 2–3× wider than normal. Enter carefully."
    elif vix > 20:
        spread_note = f"VIX={vix:.1f} (slightly elevated) — slight spread widening expected."
    else:
        spread_note = f"VIX={vix:.1f} (calm) — spreads near historical tights."

    # Recommended action string
    if event_risk.level == "high" and event_risk.days_away == 0:
        action = f"WAIT — {event_risk.name} today. Re-evaluate tomorrow."
    elif event_risk.level == "high" and (event_risk.days_away or 99) <= 2:
        action = (f"Either enter NOW before {event_risk.name}, "
                  f"or wait {event_risk.days_away} days for clarity.")
    elif urgency == Urgency.IMMEDIATE:
        action = f"Enter during {window_info['window']}. Do not wait past today."
    elif urgency == Urgency.SHORT:
        action = f"Enter in {window_info['window']} window within 1–3 days."
    elif urgency == Urgency.MEDIUM:
        action = f"No rush — target entry at {window_info['window']}. Watch for better price."
    else:
        action = f"Patient setup — wait for signal to strengthen. No immediate entry needed."

    horizon_labels = {1: "intraday", 2: "2 days", 3: "3 days", 5: "1 week",
                      10: "2 weeks", 20: "1 month"}
    h_label = horizon_labels.get(horizon_days) or f"{horizon_days} days"

    return TimingRecommendation(
        urgency=urgency,
        urgency_label=URGENCY_LABELS[urgency],
        urgency_color=URGENCY_BADGE_COLORS[urgency],
        optimal_entry=window_info["window"],
        entry_reason=window_info["reason"],
        avoid_window=avoid,
        event_risk=event_risk,
        spread_note=spread_note,
        recommended_action=action,
        horizon_label=h_label,
    )
