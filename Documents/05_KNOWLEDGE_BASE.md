# Document 05 — Knowledge Base
## How the System Learns, Stores Decisions, and Improves Over Time

---

## 1. What the Knowledge Base Is

The knowledge base is the memory of Kairon. Every prediction made, every outcome recorded, every lesson learned lives here. It is what makes Kairon get smarter over time instead of making the same mistakes repeatedly.

It is built on two databases working together:

- **ChromaDB** — vector database for semantic similarity search ("find me situations that looked like this one")
- **SQLite / PostgreSQL** — relational database for structured queries ("what is my accuracy on Gold when RSI > 60?")

---

## 2. What Gets Stored After Every Prediction

```python
@dataclass
class PredictionRecord:

    # Identity
    id:              str       # UUID
    timestamp:       datetime
    asset:           str       # "Gold"
    market:          str       # "commodities"
    ticker:          str       # "GC=F"

    # Market state snapshot at prediction time
    price:           float     # 2847.30
    rsi:             float     # 61.4
    macd:            float     # +14.2
    macd_hist:       float     # +8.1
    bb_position:     float     # 0.71
    bb_width:        float     # 0.042
    volatility_20d:  float     # 0.012
    volume_ratio:    float     # 1.40
    atr_pct:         float     # 0.011
    momentum_10:     float     # +0.031
    z_score_20:      float     # +1.2
    trend:           str       # "bullish"

    # Macro context
    macro_regime:    str       # "Risk-Off"
    vix:             float     # 14.2
    dxy:             float     # 103.9
    fed_rate:        float     # 4.75
    real_yield_10y:  float     # 1.87
    yield_curve:     str       # "flattening"
    cpi_trend:       str       # "falling"

    # News context
    gdelt_tone_72h:  float     # +0.42
    gdelt_mentions:  int       # 847
    gdelt_goldstein: float     # -4.2
    news_impact:     float     # +0.71
    n_headlines:     int       # 12
    sentiment_label: str       # "bullish"

    # Cross-market context
    spx_5d_return:   float     # -0.012
    btc_24h:         float     # +0.028
    dxy_5d:          float     # -0.009
    gold_silver_ratio: float   # 82.4

    # Agent signals
    technical_score:    float  # +0.78
    fundamental_score:  float  # +0.65
    news_score:         float  # +0.71
    macro_score:        float  # +0.82
    cross_market_score: float  # +0.58
    bull_score:         float  # +0.68
    bear_score:         float  # +0.42

    # LLM reasoning (stored as text)
    bull_argument:   str
    bear_argument:   str
    trader_reasoning: str
    key_risks:       list[str]

    # Final decision
    signal:          str       # "UP" | "DOWN" | "HOLD"
    confidence:      float     # 0.82
    composite_score: float     # +0.81
    horizon_days:    int       # 5
    force_type:      str       # "macro_shift" | "news_catalyst" | "technical_breakout"

    # Cost context (what was calculated at decision time)
    capital_usd:     float     # 20000.0
    total_cost_usd:  float     # 80.0
    net_profit_projected: float # 420.0

    # Outcome (filled in by background job at horizon date)
    actual_price_at_horizon: float  # filled later
    actual_return:           float  # filled later
    prediction_correct:      int    # 0 | 1 (filled later)
    outcome_date:            datetime
    outcome_notes:           str
    actual_net_profit:       float  # actual P&L if trade was executed
```

---

## 3. The Embedding Strategy (ChromaDB)

Every prediction record is converted into a numerical vector before being stored in ChromaDB. This vector captures the "market fingerprint" of the moment — what the world looked like when the prediction was made.

```python
def embed_prediction(record: PredictionRecord) -> list[float]:
    """
    Create a 32-dimensional vector representing the market state.
    All values normalized to [0, 1] for consistent distance calculation.
    """
    def norm(v, lo, hi): return max(0, min(1, (v - lo) / (hi - lo + 1e-9)))

    return [
        # Technical state (8 dims)
        norm(record.rsi, 0, 100),
        norm(record.macd, -20, 20),
        record.bb_position,                    # already 0-1
        norm(record.volatility_20d, 0, 0.05),
        norm(record.volume_ratio, 0, 3),
        norm(record.momentum_10, -0.15, 0.15),
        norm(record.z_score_20, -3, 3),
        1.0 if record.trend == "bullish" else 0.0,

        # Macro state (8 dims)
        norm(record.vix, 10, 80),
        norm(record.dxy, 90, 120),
        norm(record.real_yield_10y, -2, 5),
        norm(record.fed_rate, 0, 8),
        # Regime as one-hot (6 dims)
        1.0 if record.macro_regime == "Risk-On"      else 0.0,
        1.0 if record.macro_regime == "Risk-Off"     else 0.0,
        1.0 if record.macro_regime == "Inflationary" else 0.0,
        1.0 if record.macro_regime == "Deflationary" else 0.0,
        1.0 if record.macro_regime == "Stagflationary" else 0.0,
        1.0 if record.macro_regime == "Crisis"       else 0.0,

        # News state (4 dims)
        norm(record.gdelt_tone_72h, -5, 5),
        norm(record.gdelt_mentions, 0, 2000),
        norm(record.gdelt_goldstein, -10, 10),
        norm(record.news_impact, -1, 1),

        # Cross-market state (4 dims)
        norm(record.spx_5d_return, -0.10, 0.10),
        norm(record.btc_24h, -0.20, 0.20),
        norm(record.dxy_5d, -0.05, 0.05),
        norm(record.gold_silver_ratio, 60, 100),

        # Agent consensus (4 dims)
        norm(record.technical_score, -1, 1),
        norm(record.macro_score, -1, 1),
        norm(record.news_score, -1, 1),
        norm(record.composite_score, -1, 1),

        # Decision metadata (2 dims)
        norm(record.confidence, 0, 1),
        norm(record.horizon_days, 1, 30),
    ]
```

---

## 4. How Similarity Search Works

When making a new prediction for Gold, the system queries ChromaDB:

```python
def find_similar_situations(
    current_state: PredictionRecord,
    asset: str,
    n_results: int = 10,
    min_similarity: float = 0.80,
) -> list[dict]:
    """
    Find the N most similar historical market situations.
    Only returns situations where the outcome is already known.
    """
    query_vector = embed_prediction(current_state)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results * 2,         # over-fetch, then filter
        where={
            "$and": [
                {"asset": {"$eq": asset}},
                {"prediction_correct": {"$ne": None}},  # outcome known
                {"confidence": {"$gte": 0.50}},          # only decent predictions
            ]
        }
    )

    # Filter by minimum similarity threshold
    filtered = [
        r for r, dist in zip(results["metadatas"][0], results["distances"][0])
        if (1 - dist) >= min_similarity   # cosine similarity >= 0.80
    ]

    return filtered[:n_results]
```

### What the query returns (injected into Trader Agent prompt)

```
KNOWLEDGE BASE CONTEXT — 7 similar situations found

Overall accuracy in similar situations: 6/7 = 86%
Average actual return in similar situations: +2.07%

Similar situation #1 (similarity: 0.94)
  Date: Oct 14, 2023
  Market state: RSI 59, Risk-Off regime, VIX 18.2, DXY 105.3
  Our prediction: UP (confidence 76%)
  Result: CORRECT — Gold rose +2.3% in 5 days
  What happened: Fed pause confirmed, dollar weakened

Similar situation #2 (similarity: 0.91)
  Date: Mar 8, 2024
  Market state: RSI 63, Risk-Off regime, VIX 14.8, DXY 102.9
  Our prediction: UP (confidence 81%)
  Result: CORRECT — Gold rose +1.8% in 5 days
  What happened: Rate hold signal + geopolitical tension

[... 5 more similar situations ...]

The one WRONG prediction:
  Date: Jan 23, 2025
  Market state: RSI 62, Risk-Off regime, VIX 15.1, DXY 104.1
  Our prediction: UP (confidence 74%)
  Result: WRONG — Gold fell -0.4% in 5 days
  What went wrong: CPI came in at 3.7% (surprise), rate cut hopes vanished
  Lesson: When CPI is due within 3 days of a Gold BUY signal, reduce
          confidence by 10% and tighten stop-loss.
```

---

## 5. The Outcome Recording Background Job

```python
async def record_outcomes():
    """
    Runs daily at 06:00 UTC.
    Finds predictions whose horizon has passed and records outcomes.
    """
    db = get_database()

    # Find all predictions with no outcome yet, past their horizon
    unresolved = db.execute("""
        SELECT * FROM predictions
        WHERE prediction_correct IS NULL
          AND datetime(timestamp, '+' || horizon_days || ' days') < datetime('now')
        ORDER BY timestamp ASC
        LIMIT 100
    """).fetchall()

    for pred in unresolved:
        try:
            # Fetch actual price at the horizon date
            df = yf.download(
                pred['ticker'],
                start=pred['outcome_date'] - timedelta(days=1),
                end=pred['outcome_date'] + timedelta(days=1),
                progress=False
            )
            if df.empty:
                continue

            actual_price   = float(df['Close'].iloc[-1])
            actual_return  = (actual_price - pred['price']) / pred['price']
            predicted_up   = pred['signal'] == 'UP'
            actually_up    = actual_return > 0
            correct        = int(predicted_up == actually_up)

            # Update relational DB
            db.execute("""
                UPDATE predictions
                SET actual_price_at_horizon = ?,
                    actual_return = ?,
                    prediction_correct = ?,
                    outcome_date = datetime('now')
                WHERE id = ?
            """, [actual_price, actual_return, correct, pred['id']])

            # Update ChromaDB metadata (for future similarity queries)
            collection.update(
                ids=[pred['id']],
                metadatas=[{
                    **pred,
                    "prediction_correct": correct,
                    "actual_return": actual_return,
                }]
            )

            # Check if this outcome reveals a new lesson
            await check_for_lesson(pred, actual_return, correct)

            logger.info(
                f"Recorded: {pred['asset']} | "
                f"Predicted {pred['signal']} | "
                f"{'CORRECT' if correct else 'WRONG'} | "
                f"Actual: {actual_return:+.2%}"
            )

        except Exception as e:
            logger.error(f"Failed to record outcome for {pred['id']}: {e}")

    db.commit()
```

---

## 6. Lesson Extraction Algorithm

When enough similar situations have outcomes, the system extracts formal lessons:

```python
async def check_for_lesson(pred: dict, actual_return: float, correct: int):
    """
    After recording an outcome, check if a new lesson can be extracted.
    A lesson requires: 10+ observations, >70% accuracy, consistent pattern.
    """
    # Find all predictions with similar characteristics
    similar = db.execute("""
        SELECT * FROM predictions
        WHERE asset = ?
          AND macro_regime = ?
          AND rsi BETWEEN ? AND ?
          AND prediction_correct IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 50
    """, [
        pred['asset'],
        pred['macro_regime'],
        pred['rsi'] - 5,    # RSI ±5 band
        pred['rsi'] + 5,
    ]).fetchall()

    if len(similar) < 10:
        return   # not enough data yet

    n_correct = sum(s['prediction_correct'] for s in similar)
    accuracy  = n_correct / len(similar)
    avg_return = sum(s['actual_return'] for s in similar) / len(similar)

    if accuracy >= 0.70:
        lesson = {
            "id":          str(uuid4()),
            "asset":       pred['asset'],
            "pattern":     f"{pred['macro_regime']} regime + RSI {pred['rsi']:.0f}±5",
            "description": f"{pred['asset']} in {pred['macro_regime']} regime with RSI "
                           f"{pred['rsi']-5:.0f}-{pred['rsi']+5:.0f}",
            "accuracy":    round(accuracy, 3),
            "n_obs":       len(similar),
            "avg_return":  round(avg_return, 4),
            "confidence":  "high" if len(similar) >= 20 else "medium",
            "created_at":  datetime.utcnow().isoformat(),
        }
        save_lesson(lesson)
        logger.info(f"New lesson extracted: {lesson['description']} — {accuracy:.0%} accuracy")
```

### Examples of Lessons That Form Over Time

```
Lesson #1 (high confidence, 47 observations):
  Pattern: Gold + Risk-Off regime + VIX > 20 + DXY falling
  Accuracy: 78%
  Avg return when correct: +1.9%
  Learned: Risk-Off + weak dollar is Gold's most reliable setup

Lesson #2 (medium confidence, 14 observations):
  Pattern: EUR/USD + ECB rate surprise above consensus
  Accuracy: 82%
  Avg return when correct: +0.4% within 24 hours
  Learned: ECB surprises move EUR/USD quickly and reliably

Lesson #3 (high confidence, 29 observations):
  Pattern: Bitcoin + NASDAQ 5-day return < -2% + BTC/NASDAQ correlation > 0.75
  Accuracy: 71%
  Avg return when correct: -3.2%
  Learned: BTC follows NASDAQ down in high-correlation regimes

Lesson #4 (high confidence, 34 observations):
  Pattern: Copper + GDELT China manufacturing sentiment < -2.0
  Accuracy: 68%
  Avg return when correct: -1.1% within 3 days
  Learned: Chinese manufacturing news moves copper with 1-3 day lag

Lesson #5 (high confidence, 19 observations):
  Pattern: Gold BUY signal + CPI release within 3 days
  Accuracy: 47% (WORSE than random)
  Avg return when correct: +0.8%
  Learned: CPI uncertainty invalidates Gold BUY signals — wait for release
```

Lesson #5 is critical — it is a **negative lesson**, telling the system when NOT to trade.

---

## 7. Accuracy Analytics Queries

The KB exposes structured analytics for Screen 4:

```python
def get_accuracy_by_asset(min_predictions: int = 5) -> list[dict]:
    return db.execute("""
        SELECT
            asset,
            market,
            COUNT(*) as n_predictions,
            SUM(prediction_correct) as n_correct,
            ROUND(AVG(prediction_correct) * 100, 1) as accuracy_pct,
            ROUND(AVG(actual_return) * 100, 2) as avg_return_pct,
            ROUND(AVG(CASE WHEN prediction_correct = 1
                          THEN actual_return END) * 100, 2) as avg_return_when_correct,
            MAX(timestamp) as last_prediction
        FROM predictions
        WHERE prediction_correct IS NOT NULL
        GROUP BY asset, market
        HAVING COUNT(*) >= ?
        ORDER BY accuracy_pct DESC
    """, [min_predictions]).fetchall()


def get_accuracy_by_regime() -> list[dict]:
    return db.execute("""
        SELECT
            macro_regime,
            asset,
            COUNT(*) as n,
            ROUND(AVG(prediction_correct) * 100, 1) as accuracy_pct
        FROM predictions
        WHERE prediction_correct IS NOT NULL
        GROUP BY macro_regime, asset
        HAVING COUNT(*) >= 5
        ORDER BY macro_regime, accuracy_pct DESC
    """).fetchall()


def get_accuracy_by_force_type() -> list[dict]:
    """How accurate are we for each primary driving force?"""
    return db.execute("""
        SELECT
            force_type,
            COUNT(*) as n,
            ROUND(AVG(prediction_correct) * 100, 1) as accuracy_pct,
            ROUND(AVG(actual_return) * 100, 2) as avg_return_pct
        FROM predictions
        WHERE prediction_correct IS NOT NULL
          AND force_type IS NOT NULL
        GROUP BY force_type
        ORDER BY accuracy_pct DESC
    """).fetchall()
```

---

## 8. Knowledge Base Growth Targets

| Milestone | Predictions | Expected Accuracy |
|-----------|-------------|------------------|
| Cold start (no KB) | 0 | 55% (model priors only) |
| Early learning | 20 | 62% |
| First lessons | 50 | 67% |
| Established | 100 | 72% |
| Mature | 200 | 76% |
| Expert | 500+ | 80%+ |

The accuracy improvement comes from:
1. KB similarity queries grounding LLM reasoning in real history
2. Negative lessons (patterns to avoid) accumulated
3. Agent weight calibration improving with more feedback
4. Confidence scores becoming better calibrated

---

*Document 05 — Knowledge Base*
*Requires approval before proceeding to build*
