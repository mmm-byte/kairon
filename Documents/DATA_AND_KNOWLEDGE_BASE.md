# CapitalFlow — Data Sources & Knowledge Base Specification
## Everything the System Reads and Learns

---

# Part 1: Data Sources

## 1.1 Price Data Sources

### Yahoo Finance (Primary — Free, No Key Required)
The backbone of all price data. Reliable, covers 50+ years of history for major assets.

**What to fetch:**
```python
import yfinance as yf

# Daily data — 20 years back
ticker = yf.Ticker("GC=F")  # Gold futures
hist = ticker.history(period="20y", interval="1d")

# Intraday — last 60 days at 1-minute resolution
hist_1m = ticker.history(period="60d", interval="1m")

# Metadata
info = ticker.info  # P/E, market cap, sector, etc.
```

**Coverage:**
- US stocks: All NYSE, NASDAQ, AMEX listed securities
- International stocks: LSE (London), TSE (Tokyo), SSE (Shanghai), FSE (Frankfurt), NSE (India)
- ETFs: SPY, QQQ, VNQ, LQD, HYG, GLD, SLV, USO
- Futures: GC=F (Gold), CL=F (Oil), ZW=F (Wheat), HG=F (Copper)
- Forex: All major and minor pairs via =X suffix
- Crypto: All top 100 via -USD suffix
- Bonds: ^TNX (10Y), ^IRX (2Y), ^TYX (30Y)
- Indices: ^GSPC (S&P), ^N225 (Nikkei), ^FTSE (FTSE), ^GDAXI (DAX), 000001.SS (Shanghai)

---

### FRED — Federal Reserve Economic Data (Free, Key Required)
The most comprehensive source of macroeconomic data globally. 800,000+ time series.

**Key series for CapitalFlow:**
```python
from fredapi import Fred
fred = Fred(api_key='your_key')

# Interest rates
fed_funds_rate = fred.get_series('FEDFUNDS')
us_10y_yield   = fred.get_series('DGS10')
us_2y_yield    = fred.get_series('DGS2')
yield_spread   = fred.get_series('T10Y2Y')  # 10Y minus 2Y

# Inflation
cpi            = fred.get_series('CPIAUCSL')   # US CPI
pce            = fred.get_series('PCE')         # Fed's preferred measure
breakeven_10y  = fred.get_series('T10YIE')      # Market inflation expectations

# Economic activity
gdp            = fred.get_series('GDPC1')       # Real GDP
unemployment   = fred.get_series('UNRATE')
ism_mfg        = fred.get_series('MANEMP')      # Manufacturing employment
retail_sales   = fred.get_series('RSAFS')

# International
ecb_rate       = fred.get_series('ECBDFR')      # ECB deposit facility rate
boj_rate       = fred.get_series('IRSTCB01JPM156N')  # Bank of Japan rate
china_cpi      = fred.get_series('CHNCPIALLMINMEI')

# Credit and financial conditions
hy_spread      = fred.get_series('BAMLH0A0HYM2') # High yield spread
ig_spread      = fred.get_series('BAMLC0A0CM')    # Investment grade spread
vix            = fred.get_series('VIXCLS')         # VIX
dollar_index   = fred.get_series('DTWEXBGS')       # DXY equivalent
```

---

### GDELT Global News (Primary News Source — Free, No Key)
The single most powerful free data source for global event intelligence.

**What GDELT is:**
- Monitors news from every country in 65 languages
- Updated every 15 minutes
- Covers print, broadcast, and online sources
- Extracts: who did what to whom, where, when, with what tone

**Key fields:**
```
Actor1Name:         Who did the action (e.g., "United States", "OPEC")
Actor2Name:         Who received the action (e.g., "Russia", "oil market")
EventCode:          Standardized event type (CAMEO code: e.g., 0231 = "Appeal for military")
GoldsteinScale:     How impactful: -10 (war) to +10 (cooperation agreement)
NumMentions:        How many sources covered this (proxy for importance)
NumSources:         Distinct sources (news outlets, not articles)
AvgTone:            Sentiment of coverage (-100 to +100)
ActionGeo_CountryCode: Where the event happened
```

**Fetching approach:**
```python
import requests
import zipfile
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta

def fetch_gdelt_events(keywords: list[str], days_back: int = 3) -> pd.DataFrame:
    """
    Download recent GDELT event files and filter for keywords.
    Free, no API key needed, but requires downloading zip files.
    """
    base_url = "http://data.gdeltproject.org/events/"
    all_events = []

    for i in range(days_back):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")

        # Each day has many 15-minute files — use the daily aggregate
        url = f"{base_url}{date}.export.CSV.zip"
        try:
            r = requests.get(url, timeout=30)
            with zipfile.ZipFile(BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f, sep='\t', header=None,
                                     names=GDELT_COLUMNS, low_memory=False)
                    # Filter for relevant keywords in Actor fields
                    mask = (
                        df['Actor1Name'].str.contains('|'.join(keywords), case=False, na=False) |
                        df['Actor2Name'].str.contains('|'.join(keywords), case=False, na=False)
                    )
                    all_events.append(df[mask])
        except Exception as e:
            print(f"GDELT fetch failed for {date}: {e}")

    return pd.concat(all_events) if all_events else pd.DataFrame()


def compute_gdelt_signal(events: pd.DataFrame) -> dict:
    """Aggregate GDELT events into a single sentiment signal."""
    if events.empty:
        return {"signal": 0.0, "n_events": 0, "confidence": 0.0}

    # Weight by NumMentions (importance) and recency
    total_mentions  = events['NumMentions'].sum()
    weighted_tone   = (events['AvgTone'] * events['NumMentions']).sum() / (total_mentions + 1)
    weighted_impact = (events['GoldsteinScale'] * events['NumMentions']).sum() / (total_mentions + 1)

    # Normalize to [-1, +1]
    tone_signal   = weighted_tone / 100
    impact_signal = weighted_impact / 10
    combined      = 0.6 * impact_signal + 0.4 * tone_signal

    return {
        "signal":     round(max(-1.0, min(1.0, combined)), 4),
        "n_events":   len(events),
        "n_mentions": int(total_mentions),
        "avg_tone":   round(weighted_tone, 2),
        "avg_impact": round(weighted_impact, 2),
        "confidence": min(1.0, total_mentions / 100),  # higher mentions = higher confidence
    }
```

---

### NewsAPI (English News — Free Tier: 100 calls/day)
Best for English-language financial news with full article text.

```python
import requests

def fetch_news(query: str, from_date: str, api_key: str) -> list[dict]:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "relevancy",
        "language": "en",
        "pageSize": 20,
        "apiKey":   api_key,
    }
    r = requests.get(url, params=params, timeout=10)
    articles = r.json().get("articles", [])
    return [{"title": a["title"], "description": a["description"],
             "published": a["publishedAt"], "source": a["source"]["name"]}
            for a in articles if a.get("title")]
```

---

### Reddit Social Sentiment (Free via PRAW)
Retail investor sentiment — leading indicator for meme stocks and crypto.

```python
import praw

reddit = praw.Reddit(client_id='...', client_secret='...', user_agent='CapitalFlow/1.0')

def get_reddit_sentiment(subreddit: str, keywords: list[str], limit: int = 100) -> dict:
    sub = reddit.subreddit(subreddit)
    posts = []
    for submission in sub.hot(limit=limit):
        if any(kw.lower() in submission.title.lower() for kw in keywords):
            posts.append({
                "title":  submission.title,
                "score":  submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "num_comments": submission.num_comments,
            })
    return posts

# Key subreddits by market
SUBREDDITS = {
    "stocks":      ["stocks", "investing", "SecurityAnalysis", "ValueInvesting"],
    "crypto":      ["CryptoCurrency", "Bitcoin", "ethereum", "CryptoMarkets"],
    "forex":       ["Forex", "Forex_Algotrading"],
    "commodities": ["commodities", "energy", "Gold"],
    "real_estate": ["realestateinvesting", "REITs"],
}
```

---

### SEC EDGAR (US Company Filings — Free, No Key)
The most authoritative source for US company fundamentals.

```python
import requests

def get_company_facts(cik: str) -> dict:
    """Fetch all reported financials for a company."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers={"User-Agent": "CapitalFlow research@email.com"})
    return r.json()

def get_recent_filings(ticker: str) -> list:
    """Get list of recent SEC filings."""
    url = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&dateRange=custom&startdt=2024-01-01"
    r = requests.get(url, headers={"User-Agent": "CapitalFlow research@email.com"})
    return r.json().get("hits", {}).get("hits", [])
```

---

### Central Bank Feeds (Free RSS/API)
Official policy statements — the highest-credibility macro signal.

```python
CENTRAL_BANK_FEEDS = {
    "Federal Reserve":         "https://www.federalreserve.gov/feeds/press_all.xml",
    "European Central Bank":   "https://www.ecb.europa.eu/rss/press.html",
    "Bank of Japan":           "https://www.boj.or.jp/en/rss/news.xml",
    "Bank of England":         "https://www.bankofengland.co.uk/rss/news",
    "People's Bank of China":  "http://www.pbc.gov.cn/rss/en/en.xml",
    "Reserve Bank of Australia": "https://www.rba.gov.au/rss/rba-content.xml",
}

# Parse with feedparser
import feedparser

def get_central_bank_news(bank_name: str) -> list[dict]:
    feed = feedparser.parse(CENTRAL_BANK_FEEDS[bank_name])
    return [{"title": e.title, "summary": e.summary, "published": e.published}
            for e in feed.entries[:10]]
```

---

## 1.2 Data We DO NOT Use (And Why)

**Bloomberg Terminal** — $24,000/year. Out of scope. yfinance covers 90% of what we need.

**Refinitiv Eikon** — Similar cost. Same issue.

**Tick data** — We are not building a high-frequency trading system. Daily and hourly data is sufficient for our time horizons (days to weeks).

**Proprietary earnings call transcripts** — Available free via SEC EDGAR. No need to pay.

**Alternative data (satellite imagery, credit card data)** — Too expensive for initial build. Can add later via Quandl/Nasdaq Data Link.

---

# Part 2: Knowledge Base Specification

## 2.1 Architecture Overview

The knowledge base is a **dual-database system:**

```
ChromaDB (Vector Database)
  Purpose: Semantic similarity search
  Stores: Prediction records as embeddings
  Query: "Find the 10 most similar market situations to now"
  Index: Cosine similarity over market state vectors

SQLite / PostgreSQL (Relational Database)
  Purpose: Structured analytics and accuracy tracking
  Stores: Prediction outcomes, agent performance, asset statistics
  Query: "What is my accuracy on Gold when RSI > 60?"
  Index: Standard SQL indexes on asset, market, date, outcome
```

## 2.2 What Gets Stored — Schema

### Table: predictions
```sql
CREATE TABLE predictions (
    id              TEXT PRIMARY KEY,       -- UUID
    timestamp       DATETIME NOT NULL,
    asset           TEXT NOT NULL,
    market          TEXT NOT NULL,
    ticker          TEXT NOT NULL,

    -- Market state at prediction time
    price           REAL,
    rsi             REAL,
    macd            REAL,
    bb_position     REAL,
    volatility_20d  REAL,
    volume_ratio    REAL,
    trend           TEXT,

    -- Macro context
    macro_regime    TEXT,
    vix             REAL,
    dxy             REAL,
    fed_rate        REAL,
    yield_curve     TEXT,

    -- News context
    gdelt_tone_3d   REAL,
    news_impact     REAL,
    n_news_mentions INTEGER,

    -- Cross-market context
    spx_5d_return   REAL,
    crypto_24h      REAL,

    -- Agent signals
    technical_score REAL,
    fundamental_score REAL,
    news_score      REAL,
    macro_score     REAL,
    cross_market_score REAL,
    bull_score      REAL,
    bear_score      REAL,

    -- Final decision
    signal          TEXT,                   -- UP | DOWN | HOLD
    confidence      REAL,
    horizon_days    INTEGER,

    -- LLM reasoning (stored as text)
    bull_argument   TEXT,
    bear_argument   TEXT,
    trader_reasoning TEXT,

    -- Outcome (filled in later by background job)
    actual_return   REAL,                   -- NULL until horizon reached
    prediction_correct INTEGER,             -- NULL | 0 | 1
    outcome_date    DATETIME,
    outcome_notes   TEXT,

    -- Cost calculation
    capital_usd     REAL,
    total_cost_usd  REAL,
    net_profit_usd  REAL,
    cost_breakdown  TEXT                    -- JSON string
);
```

### Table: agent_performance
```sql
CREATE TABLE agent_performance (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    asset           TEXT NOT NULL,
    market          TEXT NOT NULL,
    prediction_id   TEXT REFERENCES predictions(id),
    signal_score    REAL,
    was_correct     INTEGER,                -- 0 | 1 | NULL
    timestamp       DATETIME
);
```

### Table: knowledge_lessons
```sql
CREATE TABLE knowledge_lessons (
    id              TEXT PRIMARY KEY,
    pattern_type    TEXT,                   -- "technical_setup" | "macro_event" | "news_catalyst"
    description     TEXT,
    assets          TEXT,                   -- JSON array of affected assets
    conditions      TEXT,                   -- JSON dict of required conditions
    outcome         TEXT,
    confidence      REAL,
    n_observations  INTEGER,
    created_at      DATETIME,
    last_updated    DATETIME
);
```

## 2.3 ChromaDB Vector Store

Each prediction record is embedded as a vector for semantic similarity search.

### What gets embedded
```python
def embed_market_state(record: dict) -> list[float]:
    """
    Create a numerical vector representing the market state.
    This is what gets stored in ChromaDB for similarity search.
    """
    # Normalize all values to [0, 1] range
    features = [
        normalize(record["rsi"], 0, 100),
        normalize(record["macd"], -10, 10),       # approximate bounds
        record["bb_position"],                     # already 0-1
        normalize(record["volatility_20d"], 0, 0.05),
        normalize(record["volume_ratio"], 0, 3),
        1.0 if record["trend"] == "bullish" else 0.0,
        normalize(record["vix"], 10, 80),
        normalize(record["dxy"], 90, 120),
        normalize(record["gdelt_tone_3d"], -100, 100),
        normalize(record["news_impact"], -1, 1),
        # Macro regime as one-hot
        1.0 if record["macro_regime"] == "Risk-On" else 0.0,
        1.0 if record["macro_regime"] == "Risk-Off" else 0.0,
        1.0 if record["macro_regime"] == "Inflationary" else 0.0,
        1.0 if record["macro_regime"] == "Deflationary" else 0.0,
        1.0 if record["macro_regime"] == "Crisis" else 0.0,
    ]
    return features


def query_similar_situations(current_state: dict, asset: str,
                              n_results: int = 10) -> list[dict]:
    """
    Find the N most historically similar market situations.
    Only returns situations where the outcome is known.
    """
    query_vector = embed_market_state(current_state)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results * 2,  # get more, then filter
        where={"asset": asset, "prediction_correct": {"$ne": None}}
    )

    # Parse and return with outcomes
    return parse_chroma_results(results)[:n_results]
```

### Knowledge Base Query Results
```python
def build_kb_context(similar_situations: list[dict]) -> str:
    """
    Format historical similar situations as context for the Trader Agent.
    This is injected directly into the LLM prompt.
    """
    if not similar_situations:
        return "No similar historical situations found in knowledge base."

    correct = sum(1 for s in similar_situations if s["prediction_correct"] == 1)
    total   = len(similar_situations)
    accuracy = correct / total

    avg_return = sum(s["actual_return"] for s in similar_situations
                     if s["actual_return"] is not None) / total

    context = f"""
KNOWLEDGE BASE HISTORICAL CONTEXT:
Found {total} similar market situations in the knowledge base.

Historical accuracy in similar situations: {accuracy:.0%} ({correct}/{total} correct)
Average actual return in similar situations: {avg_return:+.2f}%

Most recent similar situations:
"""
    for i, s in enumerate(similar_situations[:5], 1):
        outcome = "CORRECT" if s["prediction_correct"] == 1 else "INCORRECT"
        context += f"""
{i}. Date: {s['timestamp'][:10]}
   Prediction: {s['signal']} (confidence: {s['confidence']:.0%})
   Result: {outcome} | Actual return: {s['actual_return']:+.2f}%
   Key conditions: RSI={s['rsi']:.0f}, Regime={s['macro_regime']}, VIX={s['vix']:.0f}
   Notes: {s['outcome_notes'] or 'None'}
"""
    return context
```

## 2.4 Outcome Recording Background Job

This is what makes the knowledge base grow automatically.

```python
import schedule
import time
from datetime import datetime, timedelta

def record_outcomes():
    """
    Runs daily. Finds predictions whose horizon has passed and
    records whether they were correct.
    """
    db = get_database()
    unresolved = db.execute("""
        SELECT * FROM predictions
        WHERE prediction_correct IS NULL
        AND datetime(timestamp, '+' || horizon_days || ' days') < datetime('now')
    """).fetchall()

    for pred in unresolved:
        try:
            # Fetch actual price at horizon date
            actual_price = fetch_price_at_date(
                pred["ticker"],
                pred["outcome_date"]
            )

            actual_return = (actual_price - pred["price"]) / pred["price"]
            predicted_up  = pred["signal"] == "UP"
            actually_up   = actual_return > 0
            correct       = int(predicted_up == actually_up)

            # Update prediction record
            db.execute("""
                UPDATE predictions
                SET actual_return = ?,
                    prediction_correct = ?,
                    outcome_date = ?
                WHERE id = ?
            """, [actual_return, correct, datetime.now().isoformat(), pred["id"]])

            # Update ChromaDB metadata
            update_chroma_metadata(pred["id"], {
                "prediction_correct": correct,
                "actual_return": actual_return,
            })

            print(f"Recorded outcome for {pred['asset']}: "
                  f"{'CORRECT' if correct else 'INCORRECT'} "
                  f"(predicted {pred['signal']}, actual {actual_return:+.2f}%)")

        except Exception as e:
            print(f"Failed to record outcome for {pred['id']}: {e}")

    db.commit()

# Run every day at 6am
schedule.every().day.at("06:00").do(record_outcomes)
```

## 2.5 How the Knowledge Base Grows Smarter

### Lesson Extraction
After 10+ similar situations have outcomes recorded:

```python
def extract_lesson(pattern_description: str, similar_situations: list[dict]) -> dict:
    """
    If a pattern shows > 70% accuracy over 10+ observations,
    create a formal lesson entry.
    """
    correct = sum(1 for s in similar_situations if s["prediction_correct"] == 1)
    accuracy = correct / len(similar_situations)

    if accuracy > 0.70 and len(similar_situations) >= 10:
        lesson = {
            "pattern": pattern_description,
            "accuracy": accuracy,
            "n_obs": len(similar_situations),
            "avg_return": mean([s["actual_return"] for s in similar_situations]),
            "confidence": "high" if len(similar_situations) > 20 else "medium",
        }
        # Store in knowledge_lessons table
        save_lesson(lesson)
        return lesson
    return None
```

### Example Lessons That Will Form Over Time
```
Lesson: "Gold up within 5 days when VIX > 25 AND macro regime = Risk-Off"
  Accuracy: 78% (47/60 observations)
  Average return: +1.9%

Lesson: "Bitcoin drops within 3 days when NASDAQ drops > 2% AND BTC/NASDAQ correlation > 0.75"
  Accuracy: 71% (29/41 observations)
  Average return: -3.2%

Lesson: "EUR/USD rises within 24 hours after ECB rate surprise above consensus"
  Accuracy: 82% (14/17 observations)
  Average return: +0.4%

Lesson: "Copper falls within 3 days when GDELT China manufacturing sentiment drops below -2.0"
  Accuracy: 68% (34/50 observations)
  Average return: -1.1%
```

These lessons become institutional knowledge — the system learns to be right more often over time.

---

*Data Sources & Knowledge Base Specification — CapitalFlow Intelligence System*
*Version 1.0, March 2026*
