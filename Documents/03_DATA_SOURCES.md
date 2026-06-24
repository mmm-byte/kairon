# Document 03 — Data Sources
## Every Data Source, What It Provides, How to Access It

---

## 1. Price Data — Yahoo Finance (Free, No Key Required)

### What it provides
- OHLCV (Open, High, Low, Close, Volume) for all assets
- 20+ years of daily history for major assets
- 1-minute intraday data (last 60 days)
- Corporate actions (splits, dividends) auto-adjusted
- Real-time quotes with ~15 min delay (free tier)

### Assets covered
```
Stocks:     AAPL, MSFT, NVDA, TSLA, AMZN, SPY, QQQ, DIA
Crypto:     BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD
Forex:      EURUSD=X, GBPUSD=X, JPY=X, AUDUSD=X, CHF=X, CAD=X
Commodities: GC=F (Gold), CL=F (Oil), SI=F (Silver), NG=F (Gas),
             ZW=F (Wheat), HG=F (Copper), ZC=F (Corn)
Bonds:      ^TNX (10Y), ^IRX (2Y), ^TYX (30Y), LQD, HYG
Real Estate: VNQ, IYR, PLD, AMT, EQIX
Indices:    ^GSPC (S&P), ^IXIC (NASDAQ), ^DJI (Dow),
            ^N225 (Nikkei), ^FTSE (FTSE), ^GDAXI (DAX),
            000001.SS (Shanghai)
```

### Update frequency
- Daily OHLCV: Updated after market close
- Intraday: Updated every 15 minutes during market hours
- Crypto: Updated continuously (24/7 market)

### Failure handling
If Yahoo Finance is unavailable: use last cached value, mark data as stale, show timestamp of last successful fetch on UI.

---

## 2. Global News — GDELT Project (Free, No Key Required)

### What it provides
The most important free data source in the system. GDELT monitors news from every country in 65 languages, updated every 15 minutes.

Key fields extracted:
```
Actor1Name:       Who performed the action (country, organization, person)
Actor2Name:       Who received the action
EventCode:        CAMEO code — standardized event type
GoldsteinScale:   Impact score from -10 (war) to +10 (cooperation)
NumMentions:      How many articles covered this event
NumSources:       How many distinct news outlets
AvgTone:          Sentiment of coverage (-100 to +100)
ActionGeo_Country: Where the event happened
```

### Why GDELT matters for Kairon
A news story about political instability in a copper-mining country, reported in Portuguese by 200 Brazilian sources with a Goldstein score of -6, is a strong signal for copper prices — even before English-language financial media covers it. GDELT catches this immediately.

### Access method
```python
# Full event stream (updated every 15 min)
url = "http://data.gdeltproject.org/events/YYYYMMDDHHMMSS.export.CSV.zip"

# Last update file (tells you what just changed)
url = "http://data.gdeltproject.org/events/lastupdate.txt"
```

### Asset keyword mapping
```python
GDELT_KEYWORDS = {
    "Gold":        ["gold price", "gold market", "XAU", "gold mining"],
    "Bitcoin":     ["bitcoin", "BTC", "cryptocurrency", "crypto market"],
    "Crude Oil":   ["crude oil", "WTI", "OPEC", "oil price", "petroleum"],
    "EUR/USD":     ["euro", "ECB", "European Central Bank", "eurozone"],
    "US 10Y":      ["Federal Reserve", "treasury yield", "Fed rate",
                    "interest rate", "bond market"],
    "S&P 500":     ["S&P 500", "Wall Street", "US stocks", "equity market"],
    "Wheat":       ["wheat price", "grain market", "food security", "USDA"],
    "Copper":      ["copper price", "copper mining", "industrial metals"],
}
```

### Signal computation
```python
def gdelt_signal(events_df):
    # Weight each event by number of mentions (importance proxy)
    total_mentions = events_df['NumMentions'].sum()
    weighted_tone = (events_df['AvgTone'] * events_df['NumMentions']).sum()
    weighted_impact = (events_df['GoldsteinScale'] * events_df['NumMentions']).sum()

    tone_signal   = (weighted_tone / total_mentions) / 100    # normalize -1 to +1
    impact_signal = (weighted_impact / total_mentions) / 10   # normalize -1 to +1
    combined      = 0.6 * impact_signal + 0.4 * tone_signal   # weighted blend

    return {
        "signal":     round(max(-1.0, min(1.0, combined)), 4),
        "confidence": min(1.0, total_mentions / 100),
        "n_events":   len(events_df),
        "n_mentions": int(total_mentions),
    }
```

---

## 3. Macro Data — FRED (Free, Key Required)

### Registration
Free API key at: https://fred.stlouisfed.org/docs/api/api_key.html

### Key series tracked

| Series ID | Name | Update Frequency |
|-----------|------|-----------------|
| `FEDFUNDS` | Federal funds rate | Monthly |
| `DGS10` | 10Y Treasury yield | Daily |
| `DGS2` | 2Y Treasury yield | Daily |
| `T10Y2Y` | Yield spread (10Y-2Y) | Daily |
| `CPIAUCSL` | CPI (inflation) | Monthly |
| `T10YIE` | 10Y inflation expectations | Daily |
| `UNRATE` | Unemployment rate | Monthly |
| `GDPC1` | Real GDP growth | Quarterly |
| `VIXCLS` | VIX fear index | Daily |
| `DTWEXBGS` | US Dollar Index (DXY proxy) | Daily |
| `BAMLH0A0HYM2` | High yield credit spread | Daily |
| `BAMLC0A0CM` | Investment grade spread | Daily |
| `ECBDFR` | ECB deposit rate | When changed |
| `IRSTCB01JPM156N` | Bank of Japan rate | Monthly |
| `CHNCPIALLMINMEI` | China CPI | Monthly |

### Regime detection logic (based on FRED data)
```
Calm / Risk-On:
  VIX < 20 AND 10Y-2Y spread > 0 AND CPI trending down

Risk-Off / Fear:
  VIX > 22 AND credit spreads widening AND equities falling

Inflationary:
  CPI > 3.5% AND rising AND 10Y real yield < 1.5%

Deflationary:
  CPI < 1% AND falling AND yield curve inverted

Stagflationary:
  CPI > 3% AND GDP growth < 1% simultaneously

Crisis:
  VIX > 35 AND cross-asset correlation > 0.8 AND credit spreads > 400bps
```

---

## 4. Financial News — NewsAPI (Free: 100 calls/day)

### Registration
Free API key at: https://newsapi.org

### What it provides
- English-language financial headlines
- Article titles, descriptions, publication date, source
- Up to 100 articles per query

### Usage in Kairon
Used as supplement to GDELT for English-language financial-specific coverage. Particularly useful for:
- Earnings announcements
- Regulatory news (SEC, CFTC)
- Company-specific events

### Fallback
If daily limit (100 calls) reached: use GDELT as primary, skip NewsAPI for that cycle.

---

## 5. Social Sentiment — Reddit PRAW (Free)

### Registration
Free OAuth credentials at: https://www.reddit.com/prefs/apps

### Subreddits monitored
```python
SUBREDDITS = {
    "stocks":      ["stocks", "investing", "SecurityAnalysis"],
    "crypto":      ["CryptoCurrency", "Bitcoin", "ethereum"],
    "forex":       ["Forex", "Forex_Algotrading"],
    "commodities": ["commodities", "Gold", "energy"],
    "real_estate": ["realestateinvesting", "REITs"],
}
```

### Signal extraction
- Post score (upvotes - downvotes) as proxy for community agreement
- Upvote ratio (how one-sided is the sentiment)
- Keyword sentiment scoring (positive vs negative financial language)

### Why Reddit matters
Reddit often leads price movements in crypto and meme stocks by 2-12 hours. It is also useful for detecting when retail investors are becoming crowded in a position (contrarian signal).

---

## 6. Company Filings — SEC EDGAR (Free, No Key)

### What it provides
- 10-K annual reports
- 10-Q quarterly reports
- 8-K current event filings (earnings surprises, leadership changes)
- Insider trading forms (Form 4)

### Access
```
Base URL: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
Filings search: https://efts.sec.gov/LATEST/search-index?q={ticker}
```

### Usage
- Trigger fundamental re-analysis when new 10-K or 10-Q filed
- Flag insider selling as risk signal
- Extract revenue and earnings data for Fundamental Analyst

---

## 7. Central Bank Statements — RSS Feeds (Free)

### Feeds monitored
```python
CB_FEEDS = {
    "Federal Reserve":          "https://www.federalreserve.gov/feeds/press_all.xml",
    "European Central Bank":    "https://www.ecb.europa.eu/rss/press.html",
    "Bank of Japan":            "https://www.boj.or.jp/en/rss/news.xml",
    "Bank of England":          "https://www.bankofengland.co.uk/rss/news",
    "People's Bank of China":   "http://www.pbc.gov.cn/rss/en/en.xml",
    "Reserve Bank of Australia":"https://www.rba.gov.au/rss/rba-content.xml",
}
```

### Why this matters
A central bank statement is the highest-credibility macro event. A single sentence from the Fed Chair can move forex markets by 1% instantly. These feeds are checked every 15 minutes.

---

## 8. Sentiment NLP — FinBERT (Free, HuggingFace)

### Model
```
ProsusAI/finbert — specifically trained on financial text
Classes: positive, negative, neutral
Available at: huggingface.co/ProsusAI/finbert
```

### Usage
Runs on all headlines from NewsAPI and central bank statements. GDELT has its own AvgTone score so FinBERT is not needed there.

### Fallback
Keyword-based sentiment (POSITIVE_WORDS vs NEGATIVE_WORDS dictionary) used if FinBERT cannot load (low memory environments).

---

## 9. Data Caching Strategy

| Data Type | Cache Duration | Storage |
|-----------|---------------|---------|
| Price data (daily) | 24 hours | Disk (SQLite) |
| Price data (intraday) | 15 minutes | Memory (Redis) |
| GDELT events | 15 minutes | Memory (Redis) |
| FRED macro data | 1 hour | Disk (SQLite) |
| NewsAPI headlines | 30 minutes | Memory (Redis) |
| Computed indicators | 15 minutes | Memory (Redis) |
| Agent analysis results | 15 minutes | Memory (Redis) |
| KB similarity queries | 5 minutes | Memory (Redis) |

---

## 10. Data Quality Checks

Every data fetch runs these checks before the data enters the pipeline:

```python
def validate_price_data(df):
    checks = [
        len(df) >= 30,                          # Minimum rows
        df['close'].isna().sum() / len(df) < 0.05,  # < 5% missing
        (df['close'] > 0).all(),                # No zero/negative prices
        df.index.is_monotonic_increasing,       # Dates in order
        (df['high'] >= df['low']).all(),        # High >= Low always
    ]
    return all(checks), [c for c in checks if not c]
```

If validation fails: use last cached good data, flag the data source as degraded, log the issue.

---

*Document 03 — Data Sources*
*Requires approval before proceeding to build*
