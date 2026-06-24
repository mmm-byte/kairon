# Document 02 — System Architecture
## How Everything Connects

---

## 1. The Four Layers

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 4 — PRESENTATION LAYER                                   │
│  5 screens · Streamlit (v1) → React (v2) · No user data stored  │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 3 — DECISION LAYER                                       │
│  Capital Allocation Engine · Cost Engine · Risk Manager         │
│  Move Ranker · Timing Recommender · LLM Explainer               │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 2 — INTELLIGENCE LAYER                                   │
│  8 AI Agents · ML Models · Knowledge Base · Regime Detector     │
│  Correlation Engine · Signal Fusion                             │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — DATA LAYER                                           │
│  Yahoo Finance · GDELT · FRED · NewsAPI · Reddit · SEC · CBanks  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Data Flow

```
Every 15 minutes:

World Event Occurs
      │
      ▼
GDELT picks up news in 65 languages ──────────────────────┐
      │                                                    │
      ▼                                                    ▼
Yahoo Finance: price data                      NewsAPI: English headlines
FRED: macro data (CPI, rates, GDP)             Reddit: social sentiment
Central bank RSS: policy statements            SEC EDGAR: filings
      │                                                    │
      └────────────────────┬───────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   DATA NORMALIZER      │
              │  Clean · Validate      │
              │  Standardize · Cache   │
              └────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────────┐
         │        AGENT TEAM (runs in parallel)    │
         │                                         │
         │  Technical   Fundamental   News         │
         │  Analyst     Analyst       Analyst      │
         │     │            │            │         │
         │  Macro       Cross-Market              │
         │  Agent       Agent                     │
         │     │            │                     │
         │     └────────────┘                     │
         │           │                            │
         │     Bull/Bear Debate                   │
         │           │                            │
         │     Trader Agent                       │
         └─────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   KNOWLEDGE BASE       │
              │  ChromaDB + SQLite     │
              │  Query similar past    │
              │  situations            │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   SIGNAL FUSION        │
              │  Weight × Regime       │
              │  × Agreement bonus     │
              │  → Composite score     │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   COST ENGINE          │
              │  All 7 cost types      │
              │  Tax optimization      │
              │  Net profit calc       │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   RISK ENGINE          │
              │  Kelly Criterion       │
              │  Position sizing       │
              │  Drawdown protection   │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   LLM EXPLAINER        │
              │  OpenAI / Anthropic    │
              │  / Ollama (your choice)│
              │  Plain English output  │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   5 UI SCREENS         │
              │  User sees & decides   │
              │  Decision logged to KB │
              └────────────────────────┘
```

---

## 3. Background Scheduler (Runs Continuously)

```
APScheduler runs these jobs:

Every 15 minutes:
  - Fetch latest prices for all assets
  - Fetch GDELT news events
  - Update technical indicators
  - Re-run all agent analyses
  - Update sentiment scores
  - Refresh move recommendations

Every 1 hour:
  - Fetch FRED macro data (when new releases available)
  - Check central bank RSS feeds
  - Update correlation matrix
  - Re-evaluate macro regime

Every 24 hours:
  - Record outcomes for predictions whose horizon has passed
  - Update KB accuracy statistics
  - Extract new lessons from recently completed predictions
  - Send daily summary (future feature)

On every user decision (execute/pass):
  - Immediately log to knowledge base
  - Update agent weight calibration
  - Schedule outcome check at horizon date
```

---

## 4. Module Map

```
kairon/
│
├── data/
│   ├── market_data.py          Prices for all 6 markets (Yahoo Finance)
│   ├── news_fetcher.py         GDELT + NewsAPI + Reddit + central banks
│   ├── macro_data.py           FRED macro indicators
│   ├── indicators.py           25 technical indicators computed from OHLCV
│   └── data_cache.py           In-memory + disk cache to avoid re-fetching
│
├── agents/
│   ├── technical.py            Technical Analyst agent
│   ├── fundamental.py          Fundamental Analyst agent
│   ├── news_agent.py           News Analyst agent
│   ├── macro_agent.py          Macro Agent
│   ├── cross_market.py         Cross-Market Contagion Agent
│   ├── bull_bear.py            Bull + Bear Researcher agents + debate
│   ├── trader.py               Trader Agent (final decision)
│   └── base_agent.py           Abstract base class all agents inherit
│
├── intelligence/
│   ├── signal_fusion.py        Combines all agent signals into one score
│   ├── regime_detector.py      Detects current macro regime (6 regimes)
│   ├── correlation_engine.py   Dynamic correlation matrix (updates daily)
│   └── knowledge_base.py       ChromaDB + SQLite knowledge store
│
├── engine/
│   ├── cost_engine.py          All 7 cost types calculated
│   ├── risk_engine.py          Kelly Criterion + drawdown protection
│   ├── allocation_engine.py    Ranks all opportunities by net profit
│   └── timing_engine.py        Recommends when to act (minutes/days/weeks)
│
├── utils/
│   ├── llm_provider.py         OpenAI / Anthropic / Ollama abstraction
│   ├── scheduler.py            APScheduler background jobs
│   └── logger.py               Structured logging
│
├── api/
│   ├── main.py                 FastAPI application
│   ├── routes/
│   │   ├── markets.py          /api/markets endpoints
│   │   ├── signals.py          /api/signals endpoints
│   │   ├── moves.py            /api/moves endpoints
│   │   ├── agents.py           /api/agents endpoints
│   │   ├── kb.py               /api/kb endpoints
│   │   └── costs.py            /api/costs endpoints
│   └── websocket.py            Real-time price updates via WebSocket
│
├── ui/
│   ├── app.py                  Streamlit main app (v1)
│   ├── screens/
│   │   ├── overview.py         Screen 1 — Mission Control
│   │   ├── moves.py            Screen 2 — Move Recommendations
│   │   ├── agents.py           Screen 3 — Agent Intelligence
│   │   ├── kb.py               Screen 4 — Knowledge Base
│   │   └── costs.py            Screen 5 — Cost Calculator
│   └── components/             Reusable UI components
│
├── db/
│   ├── models.py               SQLAlchemy models
│   ├── migrations/             Database schema migrations
│   └── seed.py                 Initial seed data
│
├── tests/
│   ├── test_agents.py
│   ├── test_costs.py
│   ├── test_signals.py
│   └── test_kb.py
│
├── .env.example                All required environment variables
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 5. Technology Stack

### Backend
| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | Best ML/finance ecosystem |
| API Framework | FastAPI | Async, fast, auto docs |
| ML Models | PyTorch + scikit-learn | LSTM + classical ensemble |
| Agents | LangGraph | Stateful multi-agent orchestration |
| LLM Interface | LangChain | Swap providers via .env |
| Vector DB | ChromaDB | Semantic similarity for KB |
| Relational DB | SQLite → PostgreSQL | Structured prediction records |
| Scheduler | APScheduler | Background data refresh jobs |
| WebSockets | FastAPI WebSocket | Live price streaming to UI |
| Portfolio Optimization | CVXPY | Quadratic programming for allocation |

### Frontend (v1 — rapid iteration)
| Component | Technology |
|-----------|-----------|
| Framework | Streamlit |
| Charts | Plotly |
| Deployment | Docker |

### Frontend (v2 — production)
| Component | Technology |
|-----------|-----------|
| Framework | React + TypeScript |
| Charts | Recharts + D3 |
| State | Zustand |
| Styling | Tailwind CSS |

### LLM Support
| Provider | Model | Use case |
|---------|-------|---------|
| OpenAI | gpt-4o | Best quality reasoning |
| Anthropic | claude-3-5-sonnet | Long context analysis |
| Google | gemini-1.5-pro | Fast + cost effective |
| Ollama (local) | llama3 / mistral | Free, fully private |

---

## 6. Deployment Architecture

```
Production deployment:

         Users
           │
           ▼
      [Nginx / Caddy]
      Reverse proxy + SSL
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
[Streamlit]   [FastAPI]
  UI server    API server
    │             │
    └──────┬──────┘
           │
    [Redis Cache]
    Price data (5min TTL)
    Signal cache (15min TTL)
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
[ChromaDB]    [PostgreSQL]
Vector store  Relational DB
           │
    [APScheduler]
    Background jobs
           │
    [External APIs]
    Yahoo Finance, GDELT,
    FRED, NewsAPI, OpenAI
```

---

## 7. Key Design Principles

### No user financial data stored
The platform operates in simulation mode. No real account balances, no real trades, no personal financial information. A session is anonymous.

### Fail gracefully
If any data source fails (Yahoo Finance, GDELT, FRED), the system continues with cached data and clearly labels which data is fresh vs cached. No silent failures.

### LLM is optional
If no LLM API key is configured, the system runs without AI explanations. All analysis, signals, and cost calculations still work. The LLM layer only adds plain-English explanations.

### Everything is configurable via .env
Capital amount, max position size, max drawdown, tax rates, minimum net profit threshold, LLM provider, data refresh frequency — all in .env, no code changes needed.

### The background never blocks the foreground
Background data refresh (every 15 minutes) never blocks the UI. The screen always shows the last computed result with a freshness timestamp. Users never see a loading spinner while agents are running.

---

*Document 02 — System Architecture*
*Requires approval before proceeding to build*
