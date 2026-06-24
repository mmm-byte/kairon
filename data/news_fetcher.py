"""
kairon/data/news_fetcher.py
Multi-source news aggregation (Document 03 revised).
Sources: GDELT · Brave Search · DuckDuckGo · Central Bank RSS · Reddit (stub)
All sources are free. No single source is a single point of failure.
"""
import json
import logging
import time
import urllib.request
import urllib.parse
import zipfile
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from kairon.data.source_status import source_status

logger = logging.getLogger("kairon.news")

# ── Asset keyword mapping (Document 03) ──────────────────────────────────────
ASSET_KEYWORDS = {
    "Gold":         ["gold price", "gold market", "XAU", "gold mining", "precious metals"],
    "Bitcoin":      ["bitcoin", "BTC", "cryptocurrency", "crypto market"],
    "Crude Oil":    ["crude oil", "WTI", "OPEC", "oil price", "petroleum"],
    "EUR/USD":      ["euro", "ECB", "European Central Bank", "eurozone", "EUR/USD"],
    "US 10Y":       ["Federal Reserve", "treasury yield", "Fed rate", "interest rate", "bond market"],
    "S&P 500":      ["S&P 500", "Wall Street", "US stocks", "equity market", "NYSE"],
    "Wheat":        ["wheat price", "grain market", "food security", "USDA"],
    "Copper":       ["copper price", "copper mining", "industrial metals"],
    "Silver":       ["silver price", "XAG", "silver market"],
    "Natural Gas":  ["natural gas price", "LNG", "gas market"],
    "Ethereum":     ["ethereum", "ETH", "DeFi", "smart contracts"],
    "REIT":         ["real estate investment", "REIT", "property market", "cap rate"],
    "macro":        ["Federal Reserve", "inflation", "CPI", "GDP", "recession", "interest rates"],
}

CENTRAL_BANK_FEEDS = {
    "Federal Reserve":          "https://www.federalreserve.gov/feeds/press_all.xml",
    "European Central Bank":    "https://www.ecb.europa.eu/rss/press.html",
    "Bank of Japan":            "https://www.boj.or.jp/en/rss/news.xml",
    "Bank of England":          "https://www.bankofengland.co.uk/rss/news",
}

# Source tier weights for credibility scoring (Document 04 Agent 3)
SOURCE_TIERS = {
    "Federal Reserve": 0.95, "ECB": 0.95, "Bank of Japan": 0.95,
    "Reuters": 0.80, "AP": 0.80, "Bloomberg": 0.80, "FT": 0.80, "WSJ": 0.80,
    "CNBC": 0.60, "MarketWatch": 0.60, "Forbes": 0.60,
    "Reddit": 0.30, "Twitter": 0.20,
    "GDELT": 0.50,  # aggregated — treated as tier 3
    "Unknown": 0.40,
}


def _get_source_tier(source_name: str) -> float:
    for key, weight in SOURCE_TIERS.items():
        if key.lower() in source_name.lower():
            return weight
    return SOURCE_TIERS["Unknown"]


def _simple_sentiment(text: str) -> float:
    """
    Keyword-based sentiment scorer (FinBERT fallback).
    Returns -1.0 to +1.0.
    """
    if not text:
        return 0.0
    text_lower = text.lower()

    positive = ["surges", "rises", "gains", "bullish", "strong", "beat", "growth",
                 "rally", "record", "recovery", "positive", "optimism", "upbeat",
                 "breakout", "jumped", "soared", "climbs", "advance"]
    negative = ["falls", "drops", "decline", "bearish", "weak", "miss", "recession",
                 "crash", "selloff", "concern", "risk", "fear", "uncertainty",
                 "plunges", "slumps", "tumbles", "retreats", "negative"]

    pos_count = sum(1 for w in positive if w in text_lower)
    neg_count = sum(1 for w in negative if w in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return round((pos_count - neg_count) / total, 3)


# ── GDELT ─────────────────────────────────────────────────────────────────────
GDELT_COLUMNS = [
    "GlobalEventID", "Day", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode",
    "QuadClass", "GoldsteinScale", "NumMentions", "NumSources",
    "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
    "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_Lat",
    "Actor1Geo_Long", "Actor1Geo_FeatureID", "Actor2Geo_Type",
    "Actor2Geo_FullName", "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code",
    "Actor2Geo_Lat", "Actor2Geo_Long", "Actor2Geo_FeatureID",
    "ActionGeo_Type", "ActionGeo_FullName", "ActionGeo_CountryCode",
    "ActionGeo_ADM1Code", "ActionGeo_Lat", "ActionGeo_Long",
    "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL",
]


def fetch_gdelt(asset: str, days_back: int = 3) -> list[dict]:
    """Fetch GDELT events for a given asset keyword set."""
    keywords = ASSET_KEYWORDS.get(asset, [asset])
    events = []

    for i in range(min(days_back, 3)):
        date_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y%m%d")
        url = f"http://data.gdeltproject.org/events/{date_str}.export.CSV.zip"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kairon/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read()
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                with zf.open(zf.namelist()[0]) as f:
                    df = pd.read_csv(f, sep="\t", header=None, names=GDELT_COLUMNS,
                                     low_memory=False, on_bad_lines="skip")

            mask = (
                df["Actor1Name"].astype(str).str.contains("|".join(keywords), case=False, na=False) |
                df["Actor2Name"].astype(str).str.contains("|".join(keywords), case=False, na=False)
            )
            matched = df[mask]

            for _, row in matched.head(50).iterrows():
                events.append({
                    "source": "GDELT",
                    "headline": f"{row.get('Actor1Name', '')} — {row.get('EventCode', '')}",
                    "goldstein_scale": row.get("GoldsteinScale"),
                    "num_mentions": row.get("NumMentions", 0),
                    "avg_tone": row.get("AvgTone"),
                    "geo_country": row.get("ActionGeo_CountryCode", ""),
                    "source_url": row.get("SOURCEURL", ""),
                    "published_at": str(row.get("Day", "")),
                    "sentiment_score": _simple_sentiment(str(row.get("AvgTone", 0))),
                    "tier": SOURCE_TIERS["GDELT"],
                })

            source_status.mark_healthy("gdelt")
        except Exception as e:
            logger.warning(f"GDELT fetch failed for day -{i}: {e}")
            source_status.mark_degraded("gdelt", str(e)[:80])

    return events


def _compute_gdelt_signal(events: list[dict]) -> dict:
    """Aggregate GDELT events into a single signal."""
    if not events:
        return {"signal": 0.0, "confidence": 0.0, "n_events": 0,
                "n_mentions": 0, "avg_tone": 0.0, "avg_goldstein": 0.0}

    total_mentions = sum(e.get("num_mentions", 1) for e in events)
    if total_mentions == 0:
        total_mentions = len(events)

    weighted_tone = sum(
        (e.get("avg_tone", 0) or 0) * (e.get("num_mentions", 1) or 1)
        for e in events
    ) / total_mentions

    weighted_goldstein = sum(
        (e.get("goldstein_scale", 0) or 0) * (e.get("num_mentions", 1) or 1)
        for e in events
    ) / total_mentions

    tone_signal      = max(-1.0, min(1.0, weighted_tone / 100))
    impact_signal    = max(-1.0, min(1.0, weighted_goldstein / 10))
    combined         = 0.6 * impact_signal + 0.4 * tone_signal
    confidence       = min(1.0, total_mentions / 100)

    return {
        "signal":         round(combined, 4),
        "confidence":     round(confidence, 3),
        "n_events":       len(events),
        "n_mentions":     int(total_mentions),
        "avg_tone":       round(weighted_tone, 2),
        "avg_goldstein":  round(weighted_goldstein, 2),
    }


# ── Brave Search ──────────────────────────────────────────────────────────────
def fetch_brave_news(query: str, count: int = 20) -> list[dict]:
    """Fetch news via Brave Search API (2000 free/month)."""
    from kairon.config import cfg
    if not cfg.brave_api_key:
        return []
    try:
        params = urllib.parse.urlencode({"q": query, "count": count, "freshness": "pd"})
        url = f"https://api.search.brave.com/res/v1/news/search?{params}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": cfg.brave_api_key,
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        articles = data.get("results", [])
        result = []
        for a in articles:
            text = f"{a.get('title', '')} {a.get('description', '')}"
            result.append({
                "source": a.get("meta_url", {}).get("hostname", "Unknown"),
                "headline": a.get("title", ""),
                "summary": a.get("description", ""),
                "source_url": a.get("url", ""),
                "published_at": a.get("age", ""),
                "sentiment_score": _simple_sentiment(text),
                "tier": _get_source_tier(a.get("meta_url", {}).get("hostname", "")),
            })
        source_status.mark_healthy("brave_search")
        return result
    except Exception as e:
        logger.warning(f"Brave Search failed: {e}")
        source_status.mark_degraded("brave_search", str(e)[:80])
        return []


# ── DuckDuckGo News (no key required) ────────────────────────────────────────
def fetch_ddg_news(query: str, max_results: int = 15) -> list[dict]:
    """Fetch news via DuckDuckGo (keyless, rate-limit friendly)."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                text = f"{r.get('title', '')} {r.get('body', '')}"
                results.append({
                    "source": r.get("source", "Unknown"),
                    "headline": r.get("title", ""),
                    "summary": r.get("body", ""),
                    "source_url": r.get("url", ""),
                    "published_at": r.get("date", ""),
                    "sentiment_score": _simple_sentiment(text),
                    "tier": _get_source_tier(r.get("source", "")),
                })
        source_status.mark_healthy("duckduckgo")
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo news failed: {e}")
        source_status.mark_degraded("duckduckgo", str(e)[:80])
        return []


# ── Central Bank RSS ──────────────────────────────────────────────────────────
def fetch_central_bank_rss() -> list[dict]:
    """Parse RSS feeds from major central banks."""
    results = []
    try:
        import xml.etree.ElementTree as ET
        for bank_name, feed_url in CENTRAL_BANK_FEEDS.items():
            try:
                req = urllib.request.Request(feed_url, headers={"User-Agent": "kairon/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content = resp.read()
                root = ET.fromstring(content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                # Try RSS items first, then Atom entries
                items = root.findall(".//item") or root.findall(".//atom:entry", ns)
                for item in items[:5]:
                    title = (item.findtext("title") or
                             item.findtext("atom:title", namespaces=ns) or "")
                    link  = (item.findtext("link") or
                             item.findtext("atom:link", namespaces=ns) or "")
                    desc  = (item.findtext("description") or
                             item.findtext("atom:summary", namespaces=ns) or "")
                    text  = f"{title} {desc}"
                    results.append({
                        "source": bank_name,
                        "headline": title,
                        "summary": desc[:300],
                        "source_url": link,
                        "published_at": "",
                        "sentiment_score": _simple_sentiment(text),
                        "tier": 0.95,  # Central bank = Tier 1
                    })
            except Exception as e:
                logger.debug(f"RSS fetch failed for {bank_name}: {e}")
        if results:
            source_status.mark_healthy("central_banks")
    except Exception as e:
        source_status.mark_degraded("central_banks", str(e)[:80])
    return results


# ── Master aggregator ─────────────────────────────────────────────────────────
def get_news_signal(asset: str) -> dict:
    """
    Aggregate news from all sources and return a unified signal.
    This is what agents consume — a single clean signal dict.
    """
    # Build a search query from asset keywords
    keywords = ASSET_KEYWORDS.get(asset, [asset])
    query = " OR ".join(f'"{kw}"' for kw in keywords[:3])

    all_articles: list[dict] = []

    # 1. GDELT — global, 65 languages
    gdelt_events = fetch_gdelt(asset, days_back=3)
    gdelt_sig    = _compute_gdelt_signal(gdelt_events)
    all_articles.extend(gdelt_events)

    # 2. Brave Search (if key configured)
    brave_articles = fetch_brave_news(query, count=20)
    all_articles.extend(brave_articles)

    # 3. DuckDuckGo fallback (always try)
    if not brave_articles:
        ddg_articles = fetch_ddg_news(query, max_results=15)
        all_articles.extend(ddg_articles)

    # 4. Central bank RSS (always)
    cb_articles = fetch_central_bank_rss()
    all_articles.extend(cb_articles)

    # Deduplicate by headline similarity (simple)
    seen_headlines: set[str] = set()
    unique: list[dict] = []
    for a in all_articles:
        h = a.get("headline", "")[:60].lower().strip()
        if h and h not in seen_headlines:
            seen_headlines.add(h)
            unique.append(a)

    # Weighted sentiment fusion
    if not unique:
        return {
            "signal": 0.0,
            "confidence": 0.0,
            "n_sources": 0,
            "gdelt_tone_72h": gdelt_sig["avg_tone"],
            "gdelt_mentions": gdelt_sig["n_mentions"],
            "gdelt_goldstein": gdelt_sig.get("avg_goldstein", 0.0),
            "top_headlines": [],
            "sentiment_label": "neutral",
        }

    weighted_sum = sum(a.get("sentiment_score", 0) * a.get("tier", 0.5) for a in unique)
    total_weight = sum(a.get("tier", 0.5) for a in unique)
    fused_score  = weighted_sum / total_weight if total_weight > 0 else 0.0
    confidence   = min(1.0, len(unique) / 50)

    if fused_score > 0.15:
        label = "bullish"
    elif fused_score < -0.15:
        label = "bearish"
    else:
        label = "neutral"

    top_headlines = [
        {"headline": a["headline"], "source": a["source"],
         "sentiment": a["sentiment_score"], "tier": a["tier"]}
        for a in sorted(unique, key=lambda x: x.get("tier", 0), reverse=True)[:10]
    ]

    return {
        "signal":          round(fused_score, 4),
        "confidence":      round(confidence, 3),
        "n_sources":       len(unique),
        "n_outlets":       len({a.get("source", "") for a in unique}),
        "gdelt_tone_72h":  gdelt_sig["avg_tone"],
        "gdelt_mentions":  gdelt_sig["n_mentions"],
        "gdelt_goldstein": gdelt_sig.get("avg_goldstein", 0.0),
        "top_headlines":   top_headlines,
        "sentiment_label": label,
    }
