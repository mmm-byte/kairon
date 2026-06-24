# Document 12 — Build Plan
## Phase-by-Phase Roadmap, Tech Stack, Timeline

---

## Guiding Principle

**Document first. Approve. Then build.**
Nothing gets coded that is not documented and approved. This document is the build contract.

---

## Phase 0: Foundation (Week 1-2)
**Goal:** Working project skeleton, data flowing, tests passing.

### Deliverables
- [ ] Project structure created (all folders, `__init__.py` files)
- [ ] `.env.example` with all required variables documented
- [ ] `requirements.txt` with all dependencies pinned
- [ ] `docker-compose.yml` that starts the full stack with one command
- [ ] Data fetcher for Yahoo Finance working (prices for all 6 markets)
- [ ] Technical indicators computing correctly (25 indicators)
- [ ] SQLite database created with all tables (see Document 11)
- [ ] Basic FastAPI server returning health check
- [ ] Unit tests for indicator calculations

### Success Criteria
`docker-compose up` starts everything. `GET /api/health` returns 200. `GET /api/markets/gold/price` returns current Gold price with all 25 indicators.

---

## Phase 1: Data Layer Complete (Week 3-4)
**Goal:** All data sources working and cached.

### Deliverables
- [ ] GDELT fetcher + signal computation
- [ ] FRED macro data fetcher (all key series)
- [ ] NewsAPI integration with fallback
- [ ] Reddit PRAW sentiment
- [ ] Central bank RSS feed parser
- [ ] FinBERT sentiment model loaded with keyword fallback
- [ ] Redis caching for all data sources
- [ ] APScheduler background jobs (15-min, 1-hour, daily)
- [ ] Data quality validation on all fetches

### Success Criteria
Background jobs run on schedule. Price data for all 30+ assets refreshes every 15 minutes. GDELT signals update every 15 minutes. FRED data updates when new releases available.

---

## Phase 2: Agent Layer (Week 5-8)
**Goal:** All 8 agents producing scores and reasoning.

### Deliverables
- [ ] Base agent class with standard interface
- [ ] Technical Analyst — all 25 indicators, scoring logic, output schema
- [ ] Fundamental Analyst — all 6 market types, data inputs, scoring
- [ ] News Analyst — 5-dimension scoring, GDELT integration
- [ ] Macro Agent — 6 regime detection, central bank parsing
- [ ] Cross-Market Agent — time-zone cascade, correlation matrix
- [ ] Bull Researcher — argument generation
- [ ] Bear Researcher — counter-argument generation
- [ ] Bull/Bear debate orchestration (LangGraph)
- [ ] Trader Agent — weighted aggregation, final decision
- [ ] LLM explainer (OpenAI / Anthropic / Ollama abstraction)
- [ ] All agents run in parallel (asyncio)

### Success Criteria
`POST /api/analyze` with `{asset: "gold", market: "commodities"}` returns full analysis from all 8 agents with reasoning, scores, and LLM explanation within 30 seconds.

---

## Phase 3: Intelligence Layer (Week 9-11)
**Goal:** Signal fusion, knowledge base, regime detection working.

### Deliverables
- [ ] Signal fusion engine (weighted aggregation + regime multipliers + agreement bonus)
- [ ] Regime detector (6 regimes, based on FRED + VIX + correlations)
- [ ] Dynamic correlation matrix (updates daily, separate normal/fear/crisis)
- [ ] ChromaDB vector store set up
- [ ] Knowledge base: store predictions, query similar situations
- [ ] Outcome recording background job
- [ ] Lesson extraction (patterns with >70% accuracy over 10+ observations)
- [ ] KB context injection into Trader Agent prompt

### Success Criteria
After 20+ simulated predictions are stored, KB queries return semantically similar historical situations. Agent confidence adjusts based on KB accuracy. System accuracy measurably improves from prediction 1 to prediction 50.

---

## Phase 4: Decision Layer (Week 12-14)
**Goal:** Cost engine, risk engine, allocation engine producing recommendations.

### Deliverables
- [ ] Cost engine — all 7 cost types, tax optimization, dynamic spread
- [ ] Risk engine — Kelly Criterion, drawdown protection, position sizing
- [ ] Timing engine — urgency classification (minutes/hours/days/weeks)
- [ ] Allocation engine — rank all opportunities by net profit
- [ ] Move recommendations API endpoint
- [ ] Tax optimization detector (alerts when waiting saves significant tax)

### Success Criteria
`GET /api/moves?capital=100000` returns 5 ranked move recommendations, each with complete cost waterfall and net profit. All costs accurate within 10% of real-world costs. Tax optimization alert fires correctly for positions held 340-364 days.

---

## Phase 5: UI Layer (Week 15-17)
**Goal:** All 5 screens working, connected to live API.

### Deliverables
- [ ] Screen 1: Mission Control — all components, real data
- [ ] Screen 2: Move Recommendations — full move cards, execute/pass
- [ ] Screen 3: Agent Intelligence — all agent cards, debate, contagion
- [ ] Screen 4: Knowledge Base — accuracy bars, lessons, log
- [ ] Screen 5: Cost Calculator — all inputs, instant recalculation
- [ ] WebSocket connection for live price updates (every 3 seconds)
- [ ] Regime switcher connected to API (not just frontend simulation)
- [ ] All execute/pass decisions logged to knowledge base

### Success Criteria
All 5 screens load with real data. Prices update every 3 seconds via WebSocket. Regime switch changes all analysis. Execute decision is saved to DB and reflected in KB screen.

---

## Phase 6: Testing & Polish (Week 18-20)
**Goal:** Reliable, accurate, production-ready.

### Deliverables
- [ ] Walk-forward backtest (no look-ahead bias, see Document 05)
- [ ] Accuracy validation on historical data
- [ ] Load testing (handles 50 concurrent users)
- [ ] All edge cases handled (API failure, stale data, empty KB)
- [ ] Error messages that help users understand what happened
- [ ] README with full setup instructions
- [ ] Video walkthrough of all 5 screens

### Success Criteria
System runs stably for 72 hours without crashes. KB accuracy on backtested data > 60% (better than random). All known edge cases handled gracefully. A new user can set it up in under 10 minutes following the README.

---

## Technology Dependencies

### Must Have (Phase 0)
```
yfinance==0.2.36
pandas==2.1.4
numpy==1.26.2
fastapi==0.109.0
uvicorn==0.27.0
sqlalchemy==2.0.25
python-dotenv==1.0.0
apscheduler==3.10.4
redis==5.0.1
```

### Phase 2 (Agents)
```
langchain==0.1.4
langgraph==0.0.26
openai==1.10.0
anthropic==0.14.0
torch==2.1.2
scikit-learn==1.3.2
transformers==4.36.2  (FinBERT)
```

### Phase 3 (Intelligence)
```
chromadb==0.4.22
cvxpy==1.4.1
scipy==1.11.4
```

### Phase 5 (UI)
```
streamlit==1.29.0
plotly==5.18.0
websockets==12.0
```

---

## Environment Variables Required

```bash
# LLM (choose one)
LLM_PROVIDER=openai          # openai | anthropic | ollama
LLM_MODEL=gpt-4o
OPENAI_API_KEY=               # if using OpenAI
ANTHROPIC_API_KEY=            # if using Anthropic
OLLAMA_BASE_URL=http://localhost:11434  # if using local

# Market data
ALPHA_VANTAGE_KEY=            # optional, enhances price data (free)
FRED_API_KEY=                 # macro data (free registration)

# News
NEWS_API_KEY=                 # English news (free, 100/day)
REDDIT_CLIENT_ID=             # social sentiment (free)
REDDIT_CLIENT_SECRET=

# Portfolio simulation
PORTFOLIO_CAPITAL=100000      # simulated starting capital
BASE_CURRENCY=USD
MAX_POSITION_PCT=0.25         # max 25% in any single asset
MAX_DRAWDOWN_PCT=0.10         # halt if portfolio drops 10%
MIN_NET_PROFIT_PCT=0.005      # only move if net profit > 0.5%

# Tax rates (US defaults)
SHORT_TERM_TAX_RATE=0.37
LONG_TERM_TAX_RATE=0.20
TAX_YEAR_DAYS=365

# Infrastructure
DATABASE_URL=sqlite:///kairon.db
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

---

## What Is NOT In Scope for v1.0

The following are explicitly out of scope for the initial build:

- Real broker API integration (Alpaca, Interactive Brokers)
- Real user authentication / accounts
- Real money trading execution
- Mobile app (web only in v1)
- Email / notification alerts
- Multi-user / team features
- Social features (sharing signals, leaderboards)
- Backtesting UI (runs in background, results shown in KB)
- Options / derivatives markets
- NFTs / alternative assets
- International tax systems (US only in v1)

---

## Approval Checklist

Before any code is written, confirm:

- [ ] Document 01 (Product Vision) — Approved
- [ ] Document 02 (Architecture) — Approved
- [ ] Document 03 (Data Sources) — Approved
- [ ] Document 04 (Agent Specs) — Approved
- [ ] Document 05 (Knowledge Base) — Approved
- [ ] Document 06 (Market Connections) — Approved
- [ ] Document 07 (Cost Engine) — Approved
- [ ] Document 08 (Risk Engine) — Approved
- [ ] Document 09 (UI Screens) — Approved
- [ ] Document 10 (API Design) — Approved
- [ ] Document 11 (Database Schema) — Approved
- [ ] Document 12 (Build Plan) — Approved

**Sign-off required on all 12 documents before Phase 0 begins.**

---

*Document 12 — Build Plan*
*This is the final document in the set. All documents require approval.*
