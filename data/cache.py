"""
kairon/data/cache.py
Thread-safe in-memory cache with TTL. Used when Redis is not running.
Same interface as a Redis wrapper so the data layer never cares which backend is active.
"""
import time
import threading
import logging
from typing import Any, Optional

logger = logging.getLogger("kairon.cache")


class MemoryCache:
    """Thread-safe TTL cache backed by a plain dict."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}   # key → (value, expires_at)
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at and time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 900) -> None:
        with self._lock:
            expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else 0
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        with self._lock:
            return [k for k in self._store if k.startswith(prefix)]

    def flush(self) -> None:
        with self._lock:
            self._store.clear()

    def purge_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if exp and now > exp]
            for k in expired:
                del self._store[k]
        return len(expired)

    def stats(self) -> dict:
        with self._lock:
            return {"total_keys": len(self._store)}


# TTL constants (seconds) — mirror the Redis key design from Document 11
TTL = {
    "prices":      900,   # 15 minutes
    "indicators":  900,
    "gdelt":       900,
    "news":        1800,  # 30 minutes
    "macro":       3600,  # 1 hour
    "signals":     900,
    "moves":       900,
    "regime":      900,
    "sentiment":   900,
    "session":     86400, # 24 hours
    "kb_similar":  300,   # 5 minutes
}

# Singleton cache instance
_cache = MemoryCache()


def get(key: str) -> Optional[Any]:
    return _cache.get(key)


def set(key: str, value: Any, ttl: int = 900) -> None:
    _cache.set(key, value, ttl)


def delete(key: str) -> None:
    _cache.delete(key)


def cache_key(*parts) -> str:
    """Build a namespaced cache key: cache_key('prices', 'GC=F') → 'prices:GC=F'"""
    return ":".join(str(p) for p in parts)


def get_price(ticker: str) -> Optional[dict]:
    return get(cache_key("prices", ticker))


def set_price(ticker: str, data: dict) -> None:
    set(cache_key("prices", ticker), data, TTL["prices"])


def get_indicators(ticker: str) -> Optional[dict]:
    return get(cache_key("indicators", ticker))


def set_indicators(ticker: str, data: dict) -> None:
    set(cache_key("indicators", ticker), data, TTL["indicators"])


def get_macro(series_id: str) -> Optional[dict]:
    return get(cache_key("macro", series_id))


def set_macro(series_id: str, data: dict) -> None:
    set(cache_key("macro", series_id), data, TTL["macro"])


def get_regime() -> Optional[dict]:
    return get("regime:current")


def set_regime(data: dict) -> None:
    set("regime:current", data, TTL["regime"])


def get_news(asset: str) -> Optional[list]:
    return get(cache_key("news", asset))


def set_news(asset: str, data: list) -> None:
    set(cache_key("news", asset), data, TTL["news"])


def stats() -> dict:
    return _cache.stats()
