# Document 11 — Database Schema
## Complete Database Design — Tables, Indexes, Relationships

---

## 1. Overview

Kairon uses two databases working together:

- **SQLite** (development) → **PostgreSQL** (production): relational data — predictions, outcomes, lessons, portfolio sessions
- **ChromaDB**: vector database — prediction embeddings for semantic similarity search

---

## 2. SQLite / PostgreSQL Schema

### Table: `predictions`
The core table. Every prediction made is stored here with its full context.

```sql
CREATE TABLE predictions (
    -- Identity
    id                      TEXT        PRIMARY KEY,  -- UUID v4
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Asset info
    asset                   TEXT        NOT NULL,     -- "Gold"
    ticker                  TEXT        NOT NULL,     -- "GC=F"
    market                  TEXT        NOT NULL,     -- "commodities"

    -- Market state at prediction time
    price                   REAL        NOT NULL,
    rsi                     REAL,
    macd                    REAL,
    macd_hist               REAL,
    bb_position             REAL,
    bb_width                REAL,
    volatility_20d          REAL,
    volume_ratio            REAL,
    atr_pct                 REAL,
    momentum_10             REAL,
    z_score_20              REAL,
    trend                   TEXT,       -- "bullish" | "bearish" | "neutral"

    -- Macro context
    macro_regime            TEXT,       -- "Risk-On" | "Risk-Off" | "Inflationary" | ...
    vix                     REAL,
    dxy                     REAL,
    fed_rate                REAL,
    real_yield_10y          REAL,
    yield_curve             TEXT,       -- "normal" | "flat" | "inverted"
    cpi_trend               TEXT,       -- "rising" | "falling" | "stable"

    -- News context
    gdelt_tone_72h          REAL,
    gdelt_mentions          INTEGER,
    gdelt_goldstein         REAL,
    news_impact             REAL,
    n_headlines             INTEGER,
    sentiment_label         TEXT,       -- "bullish" | "bearish" | "neutral"

    -- Cross-market context
    spx_5d_return           REAL,
    btc_24h                 REAL,
    dxy_5d                  REAL,
    gold_silver_ratio       REAL,

    -- Individual agent scores
    technical_score         REAL,
    fundamental_score       REAL,
    news_score              REAL,
    macro_score             REAL,
    cross_market_score      REAL,
    bull_score              REAL,
    bear_score              REAL,

    -- LLM reasoning (stored as text)
    bull_argument           TEXT,
    bear_argument           TEXT,
    trader_reasoning        TEXT,
    key_risks               TEXT,       -- JSON array stored as string
    llm_explanation         TEXT,

    -- Final decision
    signal                  TEXT        NOT NULL,     -- "UP" | "DOWN" | "HOLD"
    confidence              REAL        NOT NULL,
    composite_score         REAL        NOT NULL,
    horizon_days            INTEGER     NOT NULL,
    force_type              TEXT,       -- "macro_shift" | "news_catalyst" | ...
    timing_window           TEXT,       -- "hours" | "1-3 days" | "1-2 weeks"
    urgency                 TEXT,       -- "high" | "moderate" | "low"

    -- Cost context
    capital_usd             REAL,
    broker_cost             REAL,
    spread_cost             REAL,
    slippage_cost           REAL,
    fx_cost                 REAL,
    gas_cost                REAL,
    wire_cost               REAL,
    tax_cost                REAL,
    total_cost_usd          REAL,
    net_profit_projected    REAL,

    -- Position sizing
    position_usd            REAL,
    position_pct            REAL,
    stop_loss_pct           REAL,
    stop_loss_price         REAL,
    take_profit_pct         REAL,
    risk_reward_ratio       REAL,

    -- User decision (logged when user clicks Execute/Pass)
    user_decision           TEXT,       -- "execute" | "pass" | NULL (pending)
    user_decision_at        TIMESTAMP,
    user_notes              TEXT,
    user_capital_deployed   REAL,       -- actual amount user said they used

    -- Outcome (filled in by background job at horizon date)
    outcome_date            TIMESTAMP,
    actual_price            REAL,
    actual_return           REAL,
    prediction_correct      INTEGER,    -- 0 | 1 | NULL (pending)
    actual_net_profit       REAL,
    outcome_notes           TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_predictions_asset       ON predictions(asset);
CREATE INDEX idx_predictions_market      ON predictions(market);
CREATE INDEX idx_predictions_regime      ON predictions(macro_regime);
CREATE INDEX idx_predictions_signal      ON predictions(signal);
CREATE INDEX idx_predictions_correct     ON predictions(prediction_correct);
CREATE INDEX idx_predictions_created     ON predictions(created_at DESC);
CREATE INDEX idx_predictions_outcome     ON predictions(outcome_date);
CREATE INDEX idx_predictions_force       ON predictions(force_type);
CREATE INDEX idx_predictions_horizon     ON predictions(created_at, horizon_days);
```

---

### Table: `lessons`
Patterns extracted from prediction history that guide future analysis.

```sql
CREATE TABLE lessons (
    id              TEXT        PRIMARY KEY,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Pattern definition
    asset           TEXT,       -- NULL = applies to all assets
    market          TEXT,       -- NULL = applies to all markets
    macro_regime    TEXT,       -- NULL = applies to all regimes
    pattern_type    TEXT        NOT NULL, -- "technical" | "macro" | "news" | "cross_market"
    pattern_code    TEXT        NOT NULL, -- machine-readable pattern key
    description     TEXT        NOT NULL, -- human-readable description

    -- Conditions that define this pattern (stored as JSON)
    conditions      TEXT        NOT NULL, -- JSON: {"rsi_min": 55, "rsi_max": 70, ...}

    -- Performance statistics
    n_observations  INTEGER     NOT NULL DEFAULT 0,
    n_correct       INTEGER     NOT NULL DEFAULT 0,
    accuracy        REAL        NOT NULL DEFAULT 0.0,
    avg_return      REAL        NOT NULL DEFAULT 0.0,
    avg_return_correct REAL,
    std_return      REAL,

    -- Meta
    confidence_level TEXT       NOT NULL DEFAULT 'low', -- "low" | "medium" | "high"
    is_negative     BOOLEAN     NOT NULL DEFAULT FALSE,  -- TRUE = pattern to AVOID
    active          BOOLEAN     NOT NULL DEFAULT TRUE,

    CONSTRAINT min_accuracy CHECK (accuracy >= 0.0 AND accuracy <= 1.0)
);

CREATE INDEX idx_lessons_asset   ON lessons(asset);
CREATE INDEX idx_lessons_regime  ON lessons(macro_regime);
CREATE INDEX idx_lessons_pattern ON lessons(pattern_type);
CREATE INDEX idx_lessons_active  ON lessons(active);
```

---

### Table: `agent_performance`
Track each agent's individual prediction accuracy over time.

```sql
CREATE TABLE agent_performance (
    id              TEXT        PRIMARY KEY,
    prediction_id   TEXT        NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Agent info
    agent_name      TEXT        NOT NULL, -- "technical" | "fundamental" | ...
    asset           TEXT        NOT NULL,
    market          TEXT        NOT NULL,
    macro_regime    TEXT,

    -- Agent's signal for this prediction
    signal_score    REAL        NOT NULL,
    signal_direction TEXT,

    -- Outcome (filled when prediction outcome is recorded)
    was_correct     INTEGER,    -- 0 | 1 | NULL (pending)
    actual_return   REAL
);

CREATE INDEX idx_agent_perf_agent    ON agent_performance(agent_name);
CREATE INDEX idx_agent_perf_asset    ON agent_performance(asset);
CREATE INDEX idx_agent_perf_correct  ON agent_performance(was_correct);
CREATE INDEX idx_agent_perf_pred     ON agent_performance(prediction_id);
```

---

### Table: `market_snapshots`
Historical record of market state at each analysis run.

```sql
CREATE TABLE market_snapshots (
    id              TEXT        PRIMARY KEY,
    captured_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Asset
    ticker          TEXT        NOT NULL,
    asset           TEXT        NOT NULL,
    market          TEXT        NOT NULL,

    -- Price data
    price           REAL        NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    volume          BIGINT,

    -- Key indicators (full set stored in predictions table, subset here for charting)
    rsi             REAL,
    macd            REAL,
    sma_20          REAL,
    sma_50          REAL,
    bb_upper        REAL,
    bb_lower        REAL,
    atr             REAL,
    volume_ratio    REAL,

    -- Signal at this snapshot
    signal          TEXT,
    confidence      REAL
);

CREATE INDEX idx_snapshots_ticker  ON market_snapshots(ticker);
CREATE INDEX idx_snapshots_time    ON market_snapshots(captured_at DESC);
CREATE INDEX idx_snapshots_both    ON market_snapshots(ticker, captured_at DESC);
```

---

### Table: `news_events`
Stores GDELT and NewsAPI events for the live feed and audit trail.

```sql
CREATE TABLE news_events (
    id              TEXT        PRIMARY KEY,
    fetched_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Source
    source          TEXT        NOT NULL, -- "GDELT" | "NewsAPI" | "CentralBank" | "Reddit"
    source_url      TEXT,

    -- Content
    headline        TEXT,
    summary         TEXT,
    published_at    TIMESTAMP,

    -- GDELT-specific fields
    event_code      TEXT,
    actor1          TEXT,
    actor2          TEXT,
    goldstein_scale REAL,
    num_mentions    INTEGER,
    avg_tone        REAL,
    geo_country     TEXT,

    -- Computed sentiment
    sentiment_score REAL,
    sentiment_label TEXT,

    -- Asset relevance (which assets does this affect?)
    relevant_assets TEXT,       -- JSON array: ["Gold", "USD", "Bonds"]
    impact_score    REAL        -- computed importance score
);

CREATE INDEX idx_news_source    ON news_events(source);
CREATE INDEX idx_news_fetched   ON news_events(fetched_at DESC);
CREATE INDEX idx_news_sentiment ON news_events(sentiment_score);
```

---

### Table: `macro_readings`
Time series of FRED macro indicator values.

```sql
CREATE TABLE macro_readings (
    id              TEXT        PRIMARY KEY,
    series_id       TEXT        NOT NULL, -- "FEDFUNDS", "DGS10", "CPIAUCSL", ...
    series_name     TEXT        NOT NULL,
    value           REAL        NOT NULL,
    observation_date DATE       NOT NULL,
    fetched_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    units           TEXT,
    frequency       TEXT        -- "Daily" | "Monthly" | "Quarterly"
);

CREATE UNIQUE INDEX idx_macro_series_date ON macro_readings(series_id, observation_date);
CREATE INDEX idx_macro_series            ON macro_readings(series_id);
CREATE INDEX idx_macro_date              ON macro_readings(observation_date DESC);
```

---

### Table: `regime_history`
Track regime changes over time.

```sql
CREATE TABLE regime_history (
    id              TEXT        PRIMARY KEY,
    detected_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regime          TEXT        NOT NULL,
    previous_regime TEXT,
    vix             REAL,
    dxy             REAL,
    hy_spread       REAL,
    eigenvalue_ratio REAL,
    trigger         TEXT,       -- what caused the regime change
    confidence      REAL
);

CREATE INDEX idx_regime_time ON regime_history(detected_at DESC);
```

---

### Table: `portfolio_sessions`
Stores simulated portfolio state for the current browser session.

```sql
CREATE TABLE portfolio_sessions (
    id              TEXT        PRIMARY KEY,
    session_token   TEXT        NOT NULL UNIQUE,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Portfolio configuration
    starting_capital REAL       NOT NULL DEFAULT 100000.0,
    current_capital  REAL       NOT NULL DEFAULT 100000.0,
    regime_override  TEXT,      -- NULL = auto-detect

    -- Holdings (stored as JSON — no sensitive data, tickers only)
    holdings        TEXT,       -- JSON: [{"ticker": "AAPL", "qty": 50, "days_held": 373}]

    -- Session stats
    trades_executed  INTEGER    NOT NULL DEFAULT 0,
    trades_passed    INTEGER    NOT NULL DEFAULT 0,
    simulated_pnl    REAL       NOT NULL DEFAULT 0.0,

    -- Expiry (sessions auto-delete after 7 days of inactivity)
    expires_at      TIMESTAMP   NOT NULL
);

CREATE INDEX idx_sessions_token   ON portfolio_sessions(session_token);
CREATE INDEX idx_sessions_expires ON portfolio_sessions(expires_at);
```

---

### Table: `correlation_snapshots`
Daily snapshots of the dynamic correlation matrix.

```sql
CREATE TABLE correlation_snapshots (
    id              TEXT        PRIMARY KEY,
    captured_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regime          TEXT        NOT NULL,

    -- Pairwise correlations (stored as JSON for flexibility)
    -- Format: {"SPX_BTC": 0.35, "SPX_Gold": -0.20, ...}
    correlations    TEXT        NOT NULL,

    -- Eigenvalue ratio (regime indicator)
    eigenvalue_ratio REAL,

    -- Key pair values for quick querying
    spx_btc         REAL,
    spx_gold        REAL,
    spx_oil         REAL,
    gold_dxy        REAL,
    btc_eth         REAL
);

CREATE INDEX idx_corr_time   ON correlation_snapshots(captured_at DESC);
CREATE INDEX idx_corr_regime ON correlation_snapshots(regime);
```

---

## 3. Key Analytical Queries

### Accuracy by asset and regime
```sql
SELECT
    asset,
    macro_regime,
    COUNT(*)                                          AS n_predictions,
    SUM(prediction_correct)                           AS n_correct,
    ROUND(AVG(prediction_correct) * 100, 1)          AS accuracy_pct,
    ROUND(AVG(actual_return) * 100, 2)               AS avg_return_pct,
    ROUND(AVG(CASE WHEN prediction_correct = 1
                   THEN actual_return END) * 100, 2) AS avg_return_when_correct
FROM predictions
WHERE prediction_correct IS NOT NULL
GROUP BY asset, macro_regime
HAVING COUNT(*) >= 5
ORDER BY accuracy_pct DESC;
```

### Agent calibration check
```sql
SELECT
    agent_name,
    COUNT(*)                               AS n,
    ROUND(AVG(was_correct) * 100, 1)      AS accuracy_pct,
    ROUND(AVG(ABS(signal_score)), 3)      AS avg_conviction
FROM agent_performance
WHERE was_correct IS NOT NULL
GROUP BY agent_name
ORDER BY accuracy_pct DESC;
```

### Predictions due for outcome recording
```sql
SELECT
    id, asset, ticker, signal, confidence,
    created_at,
    horizon_days,
    datetime(created_at, '+' || horizon_days || ' days') AS outcome_due
FROM predictions
WHERE prediction_correct IS NULL
  AND datetime(created_at, '+' || horizon_days || ' days') < datetime('now')
ORDER BY outcome_due ASC
LIMIT 100;
```

### Find most profitable force types
```sql
SELECT
    force_type,
    COUNT(*)                                          AS n,
    ROUND(AVG(prediction_correct) * 100, 1)          AS accuracy_pct,
    ROUND(AVG(CASE WHEN prediction_correct = 1
                   THEN actual_return END) * 100, 2) AS avg_win_return,
    ROUND(AVG(net_profit_projected), 2)              AS avg_projected_net
FROM predictions
WHERE prediction_correct IS NOT NULL
  AND force_type IS NOT NULL
GROUP BY force_type
ORDER BY accuracy_pct DESC;
```

### Daily summary for KB screen
```sql
SELECT
    DATE(created_at)                         AS prediction_date,
    COUNT(*)                                 AS total,
    SUM(CASE WHEN prediction_correct = 1 THEN 1 ELSE 0 END) AS correct,
    SUM(CASE WHEN prediction_correct = 0 THEN 1 ELSE 0 END) AS wrong,
    SUM(CASE WHEN prediction_correct IS NULL THEN 1 ELSE 0 END) AS pending,
    ROUND(SUM(actual_net_profit), 2)         AS total_pnl
FROM predictions
GROUP BY DATE(created_at)
ORDER BY prediction_date DESC
LIMIT 30;
```

---

## 4. ChromaDB Collections

### Collection: `predictions`
Stores vector embeddings of all predictions for similarity search.

```python
collection = chroma_client.get_or_create_collection(
    name="predictions",
    metadata={
        "hnsw:space":           "cosine",      # cosine similarity
        "hnsw:construction_ef": 200,
        "hnsw:M":               64,
    }
)

# Each document:
collection.add(
    ids=       [prediction.id],
    embeddings=[embed_prediction(prediction)],  # 32-dim vector
    metadatas= [{
        "asset":              prediction.asset,
        "market":             prediction.market,
        "macro_regime":       prediction.macro_regime,
        "signal":             prediction.signal,
        "confidence":         prediction.confidence,
        "prediction_correct": prediction.prediction_correct,  # updated after outcome
        "actual_return":      prediction.actual_return,       # updated after outcome
        "created_at":         prediction.created_at.isoformat(),
        "force_type":         prediction.force_type,
    }]
)
```

### Collection: `news_embeddings`
Stores embeddings of news events for semantic deduplication and relevance matching.

```python
news_collection = chroma_client.get_or_create_collection(
    name="news_embeddings",
    metadata={"hnsw:space": "cosine"}
)
```

---

## 5. Redis Cache Keys

```
prices:{ticker}              → JSON price data (TTL: 15 minutes)
indicators:{ticker}          → JSON all 25 indicators (TTL: 15 minutes)
gdelt:{asset_keyword}        → JSON GDELT signal (TTL: 15 minutes)
news:{asset}                 → JSON NewsAPI headlines (TTL: 30 minutes)
macro:{series_id}            → JSON FRED reading (TTL: 1 hour)
signals:{ticker}             → JSON all agent signals (TTL: 15 minutes)
moves:{capital}              → JSON ranked moves (TTL: 15 minutes)
regime:current               → JSON current regime (TTL: 15 minutes)
sentiment:{market}           → JSON market sentiment (TTL: 15 minutes)
session:{session_token}      → JSON portfolio session (TTL: 24 hours)
kb:similar:{hash}            → JSON similar situations (TTL: 5 minutes)
```

---

## 6. Migration Strategy

```
migrations/
  001_initial_schema.sql          → Creates all tables
  002_add_force_type.sql          → Adds force_type column
  003_add_agent_performance.sql   → Creates agent_performance table
  004_add_portfolio_sessions.sql  → Creates portfolio_sessions table
  005_add_correlation_snapshots.sql

Run migrations with:
  alembic upgrade head

Rollback with:
  alembic downgrade -1
```

---

## 7. Data Retention Policy

| Table | Retention | Reason |
|-------|-----------|--------|
| `predictions` | Permanent | Core learning data |
| `lessons` | Permanent | Institutional knowledge |
| `agent_performance` | Permanent | Calibration data |
| `market_snapshots` | 1 year | Charting and history |
| `news_events` | 90 days | News feed and audit |
| `macro_readings` | Permanent | Macro history |
| `regime_history` | Permanent | Regime analysis |
| `portfolio_sessions` | 7 days after last activity | Session data |
| `correlation_snapshots` | 1 year | Correlation history |

---

*Document 11 — Database Schema*
*Requires approval before proceeding to build*
