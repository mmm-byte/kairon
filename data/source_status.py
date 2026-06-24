"""
kairon/data/source_status.py
Tracks health of every external data source.
Powers the global status bar and source status modal (Document 17).
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SourceState(str, Enum):
    HEALTHY    = "healthy"
    DEGRADED   = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN    = "unknown"


@dataclass
class SourceInfo:
    name: str
    display_name: str
    last_success: Optional[float] = None
    last_attempt: Optional[float] = None
    state: SourceState = SourceState.UNKNOWN
    message: str = ""
    retry_count: int = 0

    @property
    def last_success_ago_minutes(self) -> Optional[float]:
        if self.last_success is None:
            return None
        return round((time.time() - self.last_success) / 60, 1)

    @property
    def badge_color(self) -> str:
        return {
            SourceState.HEALTHY:    "green",
            SourceState.DEGRADED:   "amber",
            SourceState.UNAVAILABLE: "red",
            SourceState.UNKNOWN:    "gray",
        }[self.state]

    @property
    def status_label(self) -> str:
        if self.state == SourceState.HEALTHY:
            ago = self.last_success_ago_minutes
            return f"✓ {ago}min ago" if ago else "✓ Healthy"
        if self.state == SourceState.DEGRADED:
            return f"! {self.message or 'Degraded'}"
        if self.state == SourceState.UNAVAILABLE:
            return f"✗ Unavailable"
        return "? Unknown"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "state": self.state.value,
            "message": self.message,
            "badge_color": self.badge_color,
            "status_label": self.status_label,
            "last_success_ago_minutes": self.last_success_ago_minutes,
            "retry_count": self.retry_count,
        }


class SourceStatusRegistry:
    """Thread-safe registry of all data source health states."""

    SOURCES = {
        "yahoo_finance":  "Yahoo Finance (prices)",
        "binance":        "Binance (crypto backup)",
        "stooq":          "Stooq (intl equities)",
        "coingecko":      "CoinGecko (crypto meta)",
        "gdelt":          "GDELT (global news)",
        "brave_search":   "Brave Search (web news)",
        "duckduckgo":     "DuckDuckGo (news fallback)",
        "fred":           "FRED (macro data)",
        "reddit":         "Reddit (social sentiment)",
        "central_banks":  "Central Bank RSS feeds",
        "ollama":         "Ollama (local AI)",
        "openai":         "OpenAI (cloud AI)",
    }

    def __init__(self):
        self._lock = threading.RLock()
        self._sources: dict[str, SourceInfo] = {
            key: SourceInfo(name=key, display_name=display)
            for key, display in self.SOURCES.items()
        }

    def mark_healthy(self, name: str) -> None:
        with self._lock:
            s = self._sources.get(name)
            if s:
                s.state = SourceState.HEALTHY
                s.last_success = time.time()
                s.last_attempt = time.time()
                s.message = ""
                s.retry_count = 0

    def mark_degraded(self, name: str, message: str = "") -> None:
        with self._lock:
            s = self._sources.get(name)
            if s:
                s.state = SourceState.DEGRADED
                s.last_attempt = time.time()
                s.message = message

    def mark_unavailable(self, name: str, message: str = "") -> None:
        with self._lock:
            s = self._sources.get(name)
            if s:
                s.state = SourceState.UNAVAILABLE
                s.last_attempt = time.time()
                s.message = message
                s.retry_count += 1

    def get(self, name: str) -> Optional[SourceInfo]:
        with self._lock:
            return self._sources.get(name)

    def all_statuses(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._sources.values()]

    def overall_health(self) -> str:
        """Returns 'healthy', 'degraded', 'impaired', or 'critical'."""
        with self._lock:
            states = [s.state for s in self._sources.values()
                      if s.state != SourceState.UNKNOWN]
            unavail = sum(1 for s in states if s == SourceState.UNAVAILABLE)
            degraded = sum(1 for s in states if s == SourceState.DEGRADED)
            if unavail >= 3:
                return "critical"
            if unavail >= 1:
                return "impaired"
            if degraded >= 2:
                return "degraded"
            return "healthy"

    def has_price_data(self) -> bool:
        with self._lock:
            yf = self._sources.get("yahoo_finance")
            bn = self._sources.get("binance")
            return (yf and yf.state == SourceState.HEALTHY) or \
                   (bn and bn.state == SourceState.HEALTHY)

    def has_news_data(self) -> bool:
        with self._lock:
            for name in ("gdelt", "brave_search", "duckduckgo"):
                s = self._sources.get(name)
                if s and s.state == SourceState.HEALTHY:
                    return True
            return False


# Singleton
source_status = SourceStatusRegistry()
