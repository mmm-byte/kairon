"""
kairon/db/database.py
SQLite database setup, all tables from Document 11.
Thread-safe connection management for both API server and background jobs.
"""
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger("kairon.db")

# Thread-local storage for connections
_local = threading.local()


def _get_db_path() -> str:
    import os
    url = os.getenv("DATABASE_URL", "sqlite:///kairon.db")
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return "kairon.db"


@contextmanager
def get_conn():
    """Context manager that always uses the current DATABASE_URL env var."""
    db_path = _get_db_path()
    # Don't reuse cached connection if the path has changed (e.g. in tests)
    cached_path = getattr(_local, "conn_path", None)
    if cached_path != db_path or not hasattr(_local, "conn") or _local.conn is None:
        if hasattr(_local, "conn") and _local.conn is not None:
            try:
                _local.conn.close()
            except Exception:
                pass
        _local.conn = sqlite3.connect(db_path, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn_path = db_path
    try:
        yield _local.conn
    except Exception:
        _local.conn.rollback()
        raise


SCHEMA_SQL = """
-- ── predictions ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    id                   TEXT PRIMARY KEY,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    asset                TEXT NOT NULL,
    ticker               TEXT NOT NULL,
    market               TEXT NOT NULL,
    -- Market state
    price                REAL NOT NULL,
    rsi                  REAL,
    macd                 REAL,
    macd_hist            REAL,
    bb_position          REAL,
    bb_width             REAL,
    volatility_20d       REAL,
    volume_ratio         REAL,
    atr_pct              REAL,
    momentum_10          REAL,
    z_score_20           REAL,
    trend                TEXT,
    -- Macro context
    macro_regime         TEXT,
    vix                  REAL,
    dxy                  REAL,
    fed_rate             REAL,
    real_yield_10y       REAL,
    yield_curve          TEXT,
    cpi_trend            TEXT,
    -- News context
    gdelt_tone_72h       REAL,
    gdelt_mentions       INTEGER,
    gdelt_goldstein      REAL,
    news_impact          REAL,
    n_headlines          INTEGER,
    sentiment_label      TEXT,
    -- Cross-market
    spx_5d_return        REAL,
    btc_24h              REAL,
    dxy_5d               REAL,
    gold_silver_ratio    REAL,
    -- Agent scores
    technical_score      REAL,
    fundamental_score    REAL,
    news_score           REAL,
    macro_score          REAL,
    cross_market_score   REAL,
    bull_score           REAL,
    bear_score           REAL,
    -- LLM reasoning
    bull_argument        TEXT,
    bear_argument        TEXT,
    trader_reasoning     TEXT,
    key_risks            TEXT,
    llm_explanation      TEXT,
    -- Decision
    signal               TEXT NOT NULL,
    confidence           REAL NOT NULL,
    composite_score      REAL NOT NULL,
    horizon_days         INTEGER NOT NULL,
    force_type           TEXT,
    timing_window        TEXT,
    urgency              TEXT,
    -- Costs
    capital_usd          REAL,
    broker_cost          REAL,
    spread_cost          REAL,
    slippage_cost        REAL,
    fx_cost              REAL,
    gas_cost             REAL,
    wire_cost            REAL,
    tax_cost             REAL,
    total_cost_usd       REAL,
    net_profit_projected REAL,
    -- Position sizing
    position_usd         REAL,
    position_pct         REAL,
    stop_loss_pct        REAL,
    stop_loss_price      REAL,
    take_profit_pct      REAL,
    risk_reward_ratio    REAL,
    -- User decision
    user_decision        TEXT,
    user_decision_at     TIMESTAMP,
    user_notes           TEXT,
    user_capital_deployed REAL,
    -- Outcome
    outcome_date         TIMESTAMP,
    actual_price         REAL,
    actual_return        REAL,
    prediction_correct   INTEGER,
    actual_net_profit    REAL,
    outcome_notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_pred_asset    ON predictions(asset);
CREATE INDEX IF NOT EXISTS idx_pred_market   ON predictions(market);
CREATE INDEX IF NOT EXISTS idx_pred_regime   ON predictions(macro_regime);
CREATE INDEX IF NOT EXISTS idx_pred_signal   ON predictions(signal);
CREATE INDEX IF NOT EXISTS idx_pred_correct  ON predictions(prediction_correct);
CREATE INDEX IF NOT EXISTS idx_pred_created  ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pred_outcome  ON predictions(outcome_date);

-- ── lessons ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lessons (
    id              TEXT PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    asset           TEXT,
    market          TEXT,
    macro_regime    TEXT,
    pattern_type    TEXT NOT NULL,
    pattern_code    TEXT NOT NULL,
    description     TEXT NOT NULL,
    conditions      TEXT NOT NULL,
    n_observations  INTEGER NOT NULL DEFAULT 0,
    n_correct       INTEGER NOT NULL DEFAULT 0,
    accuracy        REAL NOT NULL DEFAULT 0.0,
    avg_return      REAL NOT NULL DEFAULT 0.0,
    avg_return_correct REAL,
    std_return      REAL,
    confidence_level TEXT NOT NULL DEFAULT 'low',
    is_negative     INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_lessons_asset   ON lessons(asset);
CREATE INDEX IF NOT EXISTS idx_lessons_regime  ON lessons(macro_regime);
CREATE INDEX IF NOT EXISTS idx_lessons_active  ON lessons(active);

-- ── agent_performance ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_performance (
    id            TEXT PRIMARY KEY,
    prediction_id TEXT NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    agent_name    TEXT NOT NULL,
    asset         TEXT NOT NULL,
    market        TEXT NOT NULL,
    macro_regime  TEXT,
    signal_score  REAL NOT NULL,
    signal_direction TEXT,
    was_correct   INTEGER,
    actual_return REAL
);

CREATE INDEX IF NOT EXISTS idx_ap_agent   ON agent_performance(agent_name);
CREATE INDEX IF NOT EXISTS idx_ap_asset   ON agent_performance(asset);
CREATE INDEX IF NOT EXISTS idx_ap_pred    ON agent_performance(prediction_id);

-- ── market_snapshots ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_snapshots (
    id          TEXT PRIMARY KEY,
    captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ticker      TEXT NOT NULL,
    asset       TEXT NOT NULL,
    market      TEXT NOT NULL,
    price       REAL NOT NULL,
    open_p      REAL,
    high_p      REAL,
    low_p       REAL,
    volume      INTEGER,
    rsi         REAL,
    macd        REAL,
    sma_20      REAL,
    sma_50      REAL,
    bb_upper    REAL,
    bb_lower    REAL,
    atr         REAL,
    volume_ratio REAL,
    signal      TEXT,
    confidence  REAL
);

CREATE INDEX IF NOT EXISTS idx_snap_ticker ON market_snapshots(ticker);
CREATE INDEX IF NOT EXISTS idx_snap_time   ON market_snapshots(captured_at DESC);

-- ── news_events ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_events (
    id              TEXT PRIMARY KEY,
    fetched_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source          TEXT NOT NULL,
    source_url      TEXT,
    headline        TEXT,
    summary         TEXT,
    published_at    TIMESTAMP,
    event_code      TEXT,
    actor1          TEXT,
    actor2          TEXT,
    goldstein_scale REAL,
    num_mentions    INTEGER,
    avg_tone        REAL,
    geo_country     TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    relevant_assets TEXT,
    impact_score    REAL
);

CREATE INDEX IF NOT EXISTS idx_news_source    ON news_events(source);
CREATE INDEX IF NOT EXISTS idx_news_fetched   ON news_events(fetched_at DESC);

-- ── macro_readings ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS macro_readings (
    id               TEXT PRIMARY KEY,
    series_id        TEXT NOT NULL,
    series_name      TEXT NOT NULL,
    value            REAL NOT NULL,
    observation_date DATE NOT NULL,
    fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    units            TEXT,
    frequency        TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_unique ON macro_readings(series_id, observation_date);
CREATE INDEX IF NOT EXISTS idx_macro_series        ON macro_readings(series_id);

-- ── regime_history ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS regime_history (
    id              TEXT PRIMARY KEY,
    detected_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regime          TEXT NOT NULL,
    previous_regime TEXT,
    vix             REAL,
    dxy             REAL,
    hy_spread       REAL,
    trigger         TEXT,
    confidence      REAL
);

CREATE INDEX IF NOT EXISTS idx_regime_time ON regime_history(detected_at DESC);

-- ── portfolio_sessions ────────────────────────────────────────────────────
-- Only tickers and non-personal preferences stored — see Document 20.
CREATE TABLE IF NOT EXISTS portfolio_sessions (
    id               TEXT PRIMARY KEY,
    session_token    TEXT NOT NULL UNIQUE,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    starting_capital REAL NOT NULL DEFAULT 100000.0,
    current_capital  REAL NOT NULL DEFAULT 100000.0,
    regime_override  TEXT,
    tickers          TEXT,    -- JSON array of ticker strings only (no quantities/prices)
    trades_executed  INTEGER NOT NULL DEFAULT 0,
    trades_passed    INTEGER NOT NULL DEFAULT 0,
    simulated_pnl    REAL NOT NULL DEFAULT 0.0,
    expires_at       TIMESTAMP NOT NULL,
    server_sync_enabled INTEGER NOT NULL DEFAULT 0  -- 0=browser-only, 1=server-sync opt-in
);

CREATE INDEX IF NOT EXISTS idx_sess_token   ON portfolio_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sess_expires ON portfolio_sessions(expires_at);

-- ── correlation_snapshots ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS correlation_snapshots (
    id               TEXT PRIMARY KEY,
    captured_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regime           TEXT NOT NULL,
    correlations     TEXT NOT NULL,
    eigenvalue_ratio REAL,
    spx_btc          REAL,
    spx_gold         REAL,
    spx_oil          REAL,
    gold_dxy         REAL,
    btc_eth          REAL
);

CREATE INDEX IF NOT EXISTS idx_corr_time   ON correlation_snapshots(captured_at DESC);
"""


def init_db() -> None:
    """Create all tables if they don't exist."""
    db_path = _get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    logger.info(f"Database initialised at {db_path}")


def execute(sql: str, params: tuple = ()) -> list:
    """Run a query and return all rows as dicts."""
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        if cur.description:
            return [dict(row) for row in cur.fetchall()]
        return []


def execute_one(sql: str, params: tuple = ()) -> Optional[dict]:
    """Run a query and return one row as dict or None."""
    rows = execute(sql, params)
    return rows[0] if rows else None


def insert(table: str, data: dict) -> str:
    """Insert a row; return its id."""
    keys = list(data.keys())
    placeholders = ", ".join("?" * len(keys))
    cols = ", ".join(keys)
    sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"
    with get_conn() as conn:
        conn.execute(sql, [data[k] for k in keys])
        conn.commit()
    return data.get("id", "")
