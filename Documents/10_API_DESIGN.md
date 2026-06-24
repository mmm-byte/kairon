# Document 10 — API Design
## All Backend Endpoints, Request/Response Schemas, WebSocket Spec

---

## 1. Base Configuration

```
Base URL:        http://localhost:8000/api
API Version:     v1
Content-Type:    application/json
Auth:            None (simulation mode — no user accounts)
Rate Limiting:   60 requests/minute per IP
Error Format:    {"error": "message", "code": "ERROR_CODE", "detail": "..."}
```

---

## 2. Health & Status

### `GET /api/health`
System health check. Returns status of all subsystems.

**Response 200:**
```json
{
  "status": "ok",
  "timestamp": "2026-03-23T14:32:00Z",
  "subsystems": {
    "database":      {"status": "ok", "latency_ms": 2},
    "redis":         {"status": "ok", "latency_ms": 1},
    "chromadb":      {"status": "ok", "predictions_stored": 142},
    "yahoo_finance": {"status": "ok", "last_fetch": "2026-03-23T14:30:00Z"},
    "gdelt":         {"status": "ok", "last_fetch": "2026-03-23T14:28:00Z"},
    "fred":          {"status": "ok", "last_fetch": "2026-03-23T13:00:00Z"},
    "llm":           {"status": "ok", "provider": "openai", "model": "gpt-4o"}
  },
  "data_freshness": {
    "prices":    "2 minutes ago",
    "news":      "8 minutes ago",
    "macro":     "1 hour ago"
  }
}
```

### `GET /api/status/regime`
Current macro regime and key indicators.

**Response 200:**
```json
{
  "regime":       "Risk-Off",
  "confidence":   0.78,
  "vix":          14.2,
  "dxy":          103.9,
  "yield_curve":  "flattening",
  "credit_spread_hy": 342,
  "fear_greed":   62,
  "updated_at":   "2026-03-23T14:30:00Z"
}
```

---

## 3. Market Data Endpoints

### `GET /api/markets`
All markets and their current state.

**Response 200:**
```json
{
  "markets": [
    {
      "market":    "commodities",
      "asset":     "Gold",
      "ticker":    "GC=F",
      "price":     2847.30,
      "change_1d": 0.012,
      "change_5d": 0.021,
      "signal":    "BUY",
      "confidence": 0.82,
      "sentiment": 0.71,
      "updated_at": "2026-03-23T14:30:00Z"
    }
  ],
  "total": 8,
  "regime": "Risk-Off",
  "updated_at": "2026-03-23T14:30:00Z"
}
```

### `GET /api/markets/{ticker}`
Single asset full detail.

**Path params:** `ticker` — e.g., `GC=F`, `BTC-USD`, `AAPL`

**Response 200:**
```json
{
  "asset":   "Gold",
  "ticker":  "GC=F",
  "market":  "commodities",
  "price":   2847.30,
  "ohlcv": {
    "open":   2830.10,
    "high":   2851.40,
    "low":    2822.80,
    "close":  2847.30,
    "volume": 184200
  },
  "indicators": {
    "rsi":          61.4,
    "macd":         14.2,
    "macd_signal":  8.1,
    "macd_hist":    6.1,
    "sma_10":       2831.20,
    "sma_20":       2810.50,
    "sma_50":       2778.30,
    "bb_upper":     2880.40,
    "bb_lower":     2740.60,
    "bb_position":  0.71,
    "bb_width":     0.042,
    "atr":          28.40,
    "atr_pct":      0.010,
    "volume_ratio": 1.40,
    "momentum_10":  0.031,
    "z_score_20":   1.20
  },
  "history_30d": [
    {"date": "2026-02-21", "close": 2740.10, "volume": 162000},
    "..."
  ],
  "signal":      "BUY",
  "confidence":  0.82,
  "updated_at":  "2026-03-23T14:30:00Z"
}
```

### `GET /api/markets/{ticker}/history`
Price history for charting.

**Query params:**
- `period` — `7d` | `30d` | `90d` | `1y` | `5y` (default: `30d`)
- `interval` — `1d` | `1h` | `15m` (default: `1d`)

**Response 200:**
```json
{
  "ticker":   "GC=F",
  "period":   "30d",
  "interval": "1d",
  "data": [
    {"timestamp": "2026-02-21T00:00:00Z", "open": 2730.1, "high": 2748.2, "low": 2725.8, "close": 2740.1, "volume": 162000},
    "..."
  ]
}
```

### `GET /api/markets/sentiment`
Sentiment scores for all 6 market categories.

**Response 200:**
```json
{
  "sentiments": {
    "stocks":      {"score": 0.72, "direction": "bullish", "confidence": 0.75},
    "crypto":      {"score": 0.63, "direction": "bullish", "confidence": 0.68},
    "forex":       {"score": -0.38,"direction": "bearish", "confidence": 0.71},
    "commodities": {"score": 0.81, "direction": "bullish", "confidence": 0.80},
    "bonds":       {"score": 0.55, "direction": "bullish", "confidence": 0.65},
    "real_estate": {"score": 0.44, "direction": "neutral", "confidence": 0.55}
  },
  "fear_greed_index": 62,
  "updated_at": "2026-03-23T14:28:00Z"
}
```

---

## 4. Analysis Endpoints

### `POST /api/analyze`
Run full 8-agent analysis on a specific asset.

**Request body:**
```json
{
  "ticker":        "GC=F",
  "market":        "commodities",
  "capital_usd":   20000,
  "holding_days":  0,
  "unrealized_gain_pct": 0.0,
  "debate_rounds": 1
}
```

**Response 200 (may take 15-30 seconds):**
```json
{
  "prediction_id": "pred_8f3a92b1",
  "asset":   "Gold",
  "ticker":  "GC=F",
  "signal":  "UP",
  "confidence": 0.82,
  "composite_score": 0.81,
  "force_type": "macro_shift",
  "horizon_days": 5,

  "agent_signals": {
    "technical":    {"score": 0.78, "direction": "UP", "confidence": 0.76, "reasoning": "..."},
    "fundamental":  {"score": 0.65, "direction": "UP", "confidence": 0.60, "reasoning": "..."},
    "news":         {"score": 0.71, "direction": "UP", "confidence": 0.68, "reasoning": "..."},
    "macro":        {"score": 0.82, "direction": "UP", "confidence": 0.80, "reasoning": "..."},
    "cross_market": {"score": 0.58, "direction": "UP", "confidence": 0.55, "reasoning": "..."}
  },

  "debate": {
    "bull_score":   0.68,
    "bear_score":   0.42,
    "bull_argument": "...",
    "bear_argument": "...",
    "key_disagreements": ["Fed timing", "DXY trajectory"],
    "verdict": "proceed_with_caution"
  },

  "knowledge_base": {
    "similar_situations": 7,
    "accuracy":  0.857,
    "avg_return": 0.021,
    "top_matches": [
      {"date": "2023-10-14", "outcome": "CORRECT", "return": 0.023},
      "..."
    ]
  },

  "costs": {
    "broker_cost":        20.00,
    "spread_cost":        18.00,
    "slippage_cost":      14.00,
    "fx_conversion_cost": 0.00,
    "crypto_gas_cost":    0.00,
    "wire_cost":          0.00,
    "tax_cost":           28.00,
    "total_cost_usd":     80.00,
    "total_cost_pct":     0.40,
    "break_even_return_pct": 0.40,
    "tax_optimization":   null
  },

  "position": {
    "viable":           true,
    "position_usd":     15350.00,
    "position_pct":     0.25,
    "stop_loss_pct":    0.035,
    "stop_loss_price":  2747.44,
    "take_profit_pct":  0.070,
    "take_profit_price": 3046.61,
    "max_loss_usd":     537.25,
    "target_profit_usd": 1074.50,
    "risk_reward_ratio": 2.00
  },

  "llm_explanation": "Gold has a textbook Risk-Off setup...",
  "key_risks": ["CPI above 3.5% on Friday", "DXY breakout above 105"],
  "timing": {"window": "1-3 days", "urgency": "moderate", "reason": "..."},

  "connection_graph": {
    "nodes": [...],
    "edges": [...],
    "contributing_factors": [...]
  },

  "created_at": "2026-03-23T14:32:00Z"
}
```

### `GET /api/analyze/{prediction_id}`
Retrieve a previously stored analysis.

### `GET /api/analyze/{prediction_id}/connections`
Get the full connection graph for a prediction (for Screen 6 visualization).

**Response 200:**
```json
{
  "prediction_id": "pred_8f3a92b1",
  "nodes": [
    {"id": "n1", "type": "world_event", "label": "Fed rate hold signal", "value": -0.31, "source": "GDELT"},
    {"id": "n2", "type": "macro_indicator", "label": "Real yield 1.87%", "value": -0.13, "source": "FRED"},
    {"id": "n3", "type": "price_signal", "label": "RSI 61.4", "value": 0.65, "source": "Yahoo"},
    {"id": "n4", "type": "kb_match", "label": "6/7 similar correct", "value": 0.86, "source": "KB"},
    {"id": "n5", "type": "final_signal", "label": "BUY Gold", "value": 0.81, "source": "Fusion"}
  ],
  "edges": [
    {"source": "n1", "target": "n2", "weight": 0.74, "direction": "positive", "label": "causes real yield to fall"},
    {"source": "n2", "target": "n5", "weight": 0.82, "direction": "positive", "label": "lower real yield benefits gold"},
    {"source": "n3", "target": "n5", "weight": 0.78, "direction": "positive", "label": "technical momentum confirms"},
    {"source": "n4", "target": "n5", "weight": 0.86, "direction": "positive", "label": "history supports this setup"}
  ],
  "increasing_forces": [
    {"factor": "Real yield declining", "contribution": 0.27, "evidence": "FRED: 1.87% (was 2.03%)"},
    {"factor": "Risk-Off regime",      "contribution": 0.34, "evidence": "VIX rising 7-day trend"},
    {"factor": "Technical momentum",   "contribution": 0.22, "evidence": "MACD expanding day 4"}
  ],
  "decreasing_forces": [
    {"factor": "DXY above 103.5", "contribution": -0.08, "evidence": "DXY: 103.9"},
    {"factor": "CPI uncertainty",  "contribution": -0.06, "evidence": "Release in 2 days"}
  ]
}
```

---

## 5. Move Recommendations Endpoints

### `GET /api/moves`
Get ranked move recommendations.

**Query params:**
- `capital` — available capital in USD (default: 100000)
- `min_confidence` — minimum confidence threshold (default: 0.55)
- `min_net_profit_pct` — minimum net profit % (default: 0.005)
- `markets` — comma-separated list of markets to include (default: all)
- `max_results` — maximum number of moves (default: 10)

**Response 200:**
```json
{
  "moves": [
    {
      "rank":          1,
      "prediction_id": "pred_8f3a92b1",
      "from_asset":    "SPY",
      "from_market":   "stocks",
      "to_asset":      "Gold",
      "to_market":     "commodities",
      "to_ticker":     "GC=F",
      "capital_usd":   20000,
      "horizon_days":  5,
      "confidence":    0.82,
      "signal":        "UP",
      "urgency":       "1-3 days",
      "gross_return_pct":   0.021,
      "net_return_pct":     0.017,
      "gross_profit_usd":   420.00,
      "total_costs_usd":    80.00,
      "net_profit_usd":     340.00,
      "break_even_pct":     0.004,
      "kb_accuracy":        0.857,
      "kb_matches":         7,
      "force_type":         "macro_shift",
      "tax_optimization":   null,
      "agent_agreement":    1.0,
      "llm_summary":        "Gold has textbook Risk-Off setup..."
    }
  ],
  "total_net_profit_usd": 5180.00,
  "total_capital_required": 78000.00,
  "regime": "Risk-Off",
  "generated_at": "2026-03-23T14:30:00Z"
}
```

### `POST /api/moves/{prediction_id}/execute`
Log a move execution decision.

**Request body:**
```json
{
  "decision":    "execute",
  "capital_usd": 20000,
  "notes":       "Executing full position — all 5 agents aligned"
}
```

**Response 200:**
```json
{
  "logged":         true,
  "prediction_id":  "pred_8f3a92b1",
  "decision":       "execute",
  "outcome_check_scheduled": "2026-03-28T14:30:00Z",
  "message":        "Decision logged. Outcome will be recorded on 2026-03-28."
}
```

### `POST /api/moves/{prediction_id}/pass`
Log a pass decision.

**Request body:**
```json
{
  "decision": "pass",
  "reason":   "CPI release too close — waiting for data"
}
```

---

## 6. Agent Endpoints

### `GET /api/agents/signals`
Current signals from all agents across all markets.

**Response 200:**
```json
{
  "signals": {
    "technical":    {"overall": 0.62, "by_market": {"stocks": 0.71, "crypto": 0.85, "bonds": -0.20}},
    "fundamental":  {"overall": 0.48, "by_market": {"stocks": 0.65, "crypto": 0.20, "bonds": 0.62}},
    "news":         {"overall": 0.41, "by_market": {"stocks": 0.38, "crypto": 0.71, "bonds": 0.41}},
    "macro":        {"overall": 0.55, "by_market": {"stocks": 0.45, "crypto": -0.42, "bonds": 0.79}},
    "cross_market": {"overall": 0.44, "by_market": {"stocks": 0.38, "crypto": 0.55, "bonds": 0.33}}
  },
  "consensus": 0.52,
  "regime":    "Risk-Off",
  "updated_at": "2026-03-23T14:28:00Z"
}
```

### `GET /api/agents/{agent_name}/reasoning/{ticker}`
Get detailed reasoning from a specific agent for a specific asset.

**Path params:** `agent_name` — `technical` | `fundamental` | `news` | `macro` | `cross_market`

**Response 200:**
```json
{
  "agent":    "technical",
  "ticker":   "GC=F",
  "score":    0.78,
  "direction": "UP",
  "confidence": 0.76,
  "key_indicators": {
    "rsi":    61.4,
    "macd":   14.2,
    "trend":  "bullish",
    "volume_confirmation": true
  },
  "reasoning": "Price trending above all moving averages...",
  "support_level":    2798.00,
  "resistance_level": 2880.00,
  "updated_at": "2026-03-23T14:28:00Z"
}
```

---

## 7. Knowledge Base Endpoints

### `GET /api/kb/stats`
Overall knowledge base statistics.

**Response 200:**
```json
{
  "total_predictions":   142,
  "with_outcomes":       134,
  "overall_accuracy":    0.740,
  "accuracy_trend":      "+6% vs 30 days ago",
  "by_asset": [
    {"asset": "Gold",    "n": 31, "accuracy": 0.84, "avg_return": 0.019},
    {"asset": "Bitcoin", "n": 24, "accuracy": 0.71, "avg_return": 0.031}
  ],
  "by_regime": [
    {"regime": "Risk-Off",  "n": 48, "accuracy": 0.79},
    {"regime": "Risk-On",   "n": 56, "accuracy": 0.71}
  ],
  "total_lessons": 12,
  "updated_at": "2026-03-23T06:00:00Z"
}
```

### `GET /api/kb/lessons`
All extracted lessons.

**Response 200:**
```json
{
  "lessons": [
    {
      "id":          "lesson_001",
      "pattern":     "Gold + Risk-Off + VIX > 20 + DXY falling",
      "description": "Gold in Risk-Off regime with VIX above 20 and DXY weakening",
      "accuracy":    0.78,
      "n_obs":       47,
      "avg_return":  0.019,
      "confidence":  "high",
      "created_at":  "2026-01-15T06:00:00Z"
    }
  ]
}
```

### `GET /api/kb/predictions`
Paginated prediction log.

**Query params:** `page`, `per_page`, `asset`, `outcome`, `from_date`, `to_date`

### `GET /api/kb/similar`
Find similar historical situations to a given market state.

**Request body:**
```json
{
  "ticker":        "GC=F",
  "rsi":           61.4,
  "macro_regime":  "Risk-Off",
  "vix":           14.2,
  "gdelt_tone":    0.42,
  "n_results":     7
}
```

---

## 8. Cost Calculator Endpoint

### `POST /api/costs/calculate`
Calculate all costs for a proposed move.

**Request body:**
```json
{
  "amount_usd":            20000,
  "from_market":           "stocks",
  "to_market":             "commodities",
  "to_asset":              "GC=F",
  "holding_days":          0,
  "unrealized_gain_pct":   0.0,
  "vix":                   14.2,
  "is_news_event":         false,
  "is_on_chain_transfer":  false,
  "state":                 "TX",
  "tax_loss_carryforward": 0.0
}
```

**Response 200:**
```json
{
  "amount_usd":            20000,
  "broker_cost":           20.00,
  "spread_cost":           18.00,
  "slippage_cost":         14.00,
  "fx_conversion_cost":    0.00,
  "crypto_gas_cost":       0.00,
  "wire_cost":             0.00,
  "tax_cost":              28.00,
  "tax_type":              "Short-term (37%)",
  "total_cost_usd":        80.00,
  "total_cost_pct":        0.40,
  "break_even_return_pct": 0.40,
  "tax_optimization": null,
  "verdict":               "proceed",
  "verdict_message":       "Net profit positive after all costs"
}
```

---

## 9. WebSocket — Live Price Updates

### `WS /ws/prices`
Streams real-time price updates every 3 seconds.

**Connection:** `ws://localhost:8000/ws/prices`

**Subscribe message (send after connecting):**
```json
{
  "action": "subscribe",
  "tickers": ["GC=F", "BTC-USD", "^GSPC", "EURUSD=X"]
}
```

**Incoming price update (every 3 seconds):**
```json
{
  "type":      "price_update",
  "timestamp": "2026-03-23T14:32:15Z",
  "prices": {
    "GC=F":    {"price": 2848.10, "change_1d": 0.0124, "bid": 2847.80, "ask": 2848.40},
    "BTC-USD": {"price": 87512.00, "change_1d": 0.0291, "bid": 87500, "ask": 87524},
    "^GSPC":   {"price": 5726.40, "change_1d": 0.0043}
  }
}
```

**Signal update (when agent re-analysis completes, every 15 min):**
```json
{
  "type":   "signal_update",
  "ticker": "GC=F",
  "signal": "BUY",
  "confidence": 0.82,
  "composite_score": 0.81,
  "changed": false,
  "updated_at": "2026-03-23T14:30:00Z"
}
```

**Regime change alert (when detected):**
```json
{
  "type":        "regime_change",
  "old_regime":  "Risk-On",
  "new_regime":  "Risk-Off",
  "vix":         22.4,
  "trigger":     "VIX crossed 22 threshold",
  "timestamp":   "2026-03-23T14:35:00Z",
  "action_required": "Review all open recommendations"
}
```

---

## 10. Portfolio Loading Endpoints

### `POST /api/portfolio/validate`
Validate a set of holdings before loading.

**Request body:**
```json
{
  "holdings": [
    {"ticker": "AAPL",    "quantity": 50,   "avg_price": 148.20, "days_held": 373},
    {"ticker": "BTC-USD", "quantity": 0.25, "avg_price": 62000,  "days_held": 74},
    {"ticker": "GLD",     "quantity": 20,   "avg_price": 180.00, "days_held": 120}
  ]
}
```

**Response 200:**
```json
{
  "valid": true,
  "holdings": [
    {
      "ticker":          "AAPL",
      "name":            "Apple Inc.",
      "market":          "stocks",
      "quantity":        50,
      "avg_price":       148.20,
      "current_price":   209.00,
      "current_value":   10450.00,
      "unrealized_gain": 1210.00,
      "unrealized_pct":  0.163,
      "days_held":       373,
      "tax_rate":        0.20,
      "tax_type":        "Long-term",
      "valid":           true,
      "errors":          []
    }
  ],
  "total_value":     54850.00,
  "total_gain":      8420.00,
  "errors":          []
}
```

### `POST /api/portfolio/analyze`
Run full analysis on a loaded portfolio.

**Request body:** Same holdings array as `/portfolio/validate`

**Response:** Same as `/api/moves` but contextualized to the user's actual holdings.

---

## 11. Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `TICKER_NOT_FOUND` | 404 | Ticker not found in Yahoo Finance |
| `DATA_STALE` | 200 | Data returned but marked as stale |
| `ANALYSIS_TIMEOUT` | 504 | Agent analysis took too long (>60s) |
| `REGIME_UNAVAILABLE` | 503 | FRED data unavailable, regime unknown |
| `LLM_UNAVAILABLE` | 200 | LLM explanation skipped, rest of data returned |
| `INSUFFICIENT_HISTORY` | 422 | Not enough price history for indicators |
| `COST_NEGATIVE` | 422 | Calculated net profit negative — move rejected |
| `KB_EMPTY` | 200 | No similar situations found in KB yet |
| `RATE_LIMITED` | 429 | Too many requests |

---

*Document 10 — API Design*
*Requires approval before proceeding to build*
