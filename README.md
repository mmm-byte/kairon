# Kairon — Financial Intelligence System

Multi-market AI agent platform. 8 agents. Real data. Zero required API keys.

## Quick Start (5 minutes)

```bash
# 1. Clone / copy project
cd kairon

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env file (all keys optional)
cp .env.example .env

# 4. Run
streamlit run kairon/ui/app.py
```

Open http://localhost:8501 — the system runs immediately with demo data.

---

## Optional Enhancements

| Feature | What to add | Where to get it |
|---------|-------------|-----------------|
| Real macro data | `FRED_API_KEY` in .env | fred.stlouisfed.org (free) |
| Multi-outlet news | `BRAVE_SEARCH_API_KEY` | api.search.brave.com (2000 free/mo) |
| Social sentiment | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps (free) |
| Local AI explanations | Install Ollama + `ollama pull llama3.2` | ollama.com (free) |
| Cloud AI explanations | `OPENAI_API_KEY` | platform.openai.com |

The system works with zero of these — but each one adds data quality.

---

## Architecture

```
kairon/
├── config.py              # All settings, zero-key defaults
├── db/
│   └── database.py        # SQLite schema (all Document 11 tables)
├── data/
│   ├── market_data.py     # Yahoo Finance → Binance → demo cascade
│   ├── indicators.py      # 25 technical indicators (pure numpy)
│   ├── news_fetcher.py    # GDELT + Brave + DuckDuckGo + CB RSS
│   ├── macro_data.py      # FRED → Yahoo proxy → fallback
│   ├── cache.py           # In-memory TTL cache (Redis optional)
│   └── source_status.py   # Health tracker for all data sources
├── agents/
│   ├── base_agent.py      # Abstract base, standard output schema
│   └── agents.py          # All 8 agents + Bull/Bear debate
├── engine/
│   ├── cost_engine.py     # All 7 cost types + tax optimisation
│   ├── risk_engine.py     # Kelly Criterion + position sizing
│   ├── analyzer.py        # Master orchestrator — runs full pipeline
│   └── moves.py           # Ranked move recommendations
├── intelligence/
│   ├── knowledge_base.py  # Similarity search + lesson extraction
│   └── llm_explainer.py   # Ollama → OpenAI → template fallback
└── ui/
    └── app.py             # Streamlit — all 6 screens
```

---

## How It Works

1. **Data Layer** fetches prices (Yahoo Finance), news (GDELT + web search), and macro data (FRED) with full fallback chains
2. **8 Agents** run in sequence: Technical, Fundamental, News, Macro, Cross-Market, Bull, Bear, Trader
3. **Cost Engine** calculates all 7 cost types (broker, spread, slippage, FX, gas, wire, tax)
4. **Risk Engine** sizes positions via Half-Kelly Criterion with market-type multipliers
5. **Knowledge Base** stores every prediction and learns from outcomes over time
6. **LLM Explainer** generates plain-English reasoning (Ollama local or OpenAI cloud)

---

## Screens

| # | Screen | Purpose |
|---|--------|---------|
| 1 | Mission Control | Global market overview, regime status |
| 2 | Move Recommendations | Ranked trade setups with full cost waterfall |
| 3 | Agent Intelligence | Individual agent scores + Bull/Bear debate |
| 4 | Knowledge Base | Accuracy tracking + lesson extraction |
| 5 | Cost Calculator | Exact cost breakdown for any trade |
| 6 | Connection Map | Causal chain from data to recommendation |

---

## Legal

Kairon is an **educational simulation tool**. It is not financial advice, not a registered investment adviser, and does not execute real trades. All recommendations are simulations based on publicly available data. You are solely responsible for any investment decisions you make.

Confidence scores reflect historical pattern matching in simulation data — not probability of profit. Past patterns may not repeat.

---
