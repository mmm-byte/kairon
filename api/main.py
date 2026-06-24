"""
kairon/api/main.py
FastAPI application — all endpoints from Document 10.
Run with: uvicorn kairon.api.main:app --reload --port 8000
"""
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logger = logging.getLogger("kairon.api")

# ── Request / Response Models ─────────────────────────────────────────────────
if FASTAPI_AVAILABLE:
    class AnalyzeRequest(BaseModel):
        ticker:              str   = "GC=F"
        market:              str   = "commodities"
        capital_usd:         float = 20000.0
        holding_days:        int   = 0
        unrealized_gain_pct: float = 0.0
        from_market:         str   = "stocks"
        regime_override:     Optional[str] = None

    class DecisionRequest(BaseModel):
        decision:    str   = "execute"
        capital_usd: float = 0.0
        notes:       str   = ""

    class PassRequest(BaseModel):
        decision: str = "pass"
        reason:   str = ""

    class CostRequest(BaseModel):
        amount_usd:            float = 20000.0
        from_market:           str   = "stocks"
        to_market:             str   = "commodities"
        to_asset:              str   = "GC=F"
        holding_days:          int   = 0
        unrealized_gain_pct:   float = 0.0
        vix:                   float = 14.2
        is_news_event:         bool  = False
        is_on_chain_transfer:  bool  = False
        tax_region:            str   = "US"
        tax_loss_carryforward: float = 0.0

    class HoldingItem(BaseModel):
        ticker:    str
        quantity:  float
        avg_price: float
        days_held: int = 0

    class PortfolioRequest(BaseModel):
        holdings: List[HoldingItem]

    class SimilarRequest(BaseModel):
        ticker:      str   = "GC=F"
        rsi:         float = 50.0
        macro_regime:str   = "Risk-On"
        vix:         float = 14.2
        gdelt_tone:  float = 0.0
        n_results:   int   = 7


# ── Startup / shutdown ────────────────────────────────────────────────────────
def _startup():
    """Initialise DB and start background jobs."""
    from kairon.db.database import init_db
    init_db()
    logger.info("Kairon API started")


def _shutdown():
    logger.info("Kairon API shutting down")


if FASTAPI_AVAILABLE:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _startup()
        yield
        _shutdown()

    app = FastAPI(
        title="Kairon Financial Intelligence API",
        description="8-agent multi-market financial analysis system",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting (simple in-memory) ─────────────────────────────────────
    _request_counts: dict[str, list] = {}

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        ip  = request.client.host if request.client else "unknown"
        now = time.time()
        window = _request_counts.setdefault(ip, [])
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= 60:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "code": "RATE_LIMITED",
                         "detail": "60 requests per minute maximum"},
            )
        window.append(now)
        return await call_next(request)

    def _err(code: str, msg: str, detail: str = "") -> dict:
        return {"error": msg, "code": code, "detail": detail}

    # ─────────────────────────────────────────────────────────────────────────
    # HEALTH & STATUS
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/health")
    async def health():
        from kairon.data.source_status import source_status
        from kairon.config import cfg
        import sqlite3, time as _time

        t0 = _time.perf_counter()
        try:
            import sqlite3
            conn = sqlite3.connect(cfg.db_path)
            conn.execute("SELECT 1")
            conn.close()
            db_ms = round((_time.perf_counter() - t0) * 1000, 1)
            db_status = "ok"
        except Exception as e:
            db_ms = -1
            db_status = f"error: {e}"

        statuses = {s["name"]: s for s in source_status.all_statuses()}
        overall  = source_status.overall_health()

        return {
            "status":    overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subsystems": {
                "database":     {"status": db_status, "latency_ms": db_ms},
                "yahoo_finance":{"status": statuses.get("yahoo_finance",{}).get("state","unknown")},
                "gdelt":        {"status": statuses.get("gdelt",{}).get("state","unknown")},
                "brave_search": {"status": statuses.get("brave_search",{}).get("state","unknown")},
                "fred":         {"status": statuses.get("fred",{}).get("state","unknown")},
                "ollama":       {"status": statuses.get("ollama",{}).get("state","unknown")},
                "llm_provider": cfg.llm_provider,
                "llm_model":    cfg.llm_model,
            },
            "sources": source_status.all_statuses(),
        }

    @app.get("/api/status/regime")
    async def status_regime(override: Optional[str] = None):
        from kairon.data import macro_data as md
        macro  = md.get_macro_snapshot()
        regime = md.classify_regime(macro)
        if override:
            regime["regime"] = override
        vix = macro.get("vix") or 14.2
        fear_greed = max(0, min(100, int(100 - (vix - 10) * 3)))
        return {
            "regime":           regime["regime"],
            "confidence":       regime["confidence"],
            "vix":              vix,
            "dxy":              macro.get("dxy"),
            "yield_curve":      macro.get("yield_curve"),
            "credit_spread_hy": macro.get("hy_spread"),
            "fear_greed":       fear_greed,
            "reasoning":        regime.get("reasoning"),
            "favorable_markets":   regime.get("favorable_markets"),
            "unfavorable_markets": regime.get("unfavorable_markets"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # MARKETS
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/markets")
    async def get_markets():
        from kairon.data import market_data as mkt, macro_data as md
        from kairon.data.indicators import compute_all, score_technical

        macro  = md.get_macro_snapshot()
        regime = md.classify_regime(macro)
        results = []

        display = ["GC=F","BTC-USD","SPY","EURUSD=X","CL=F","TLT","VNQ","HG=F"]
        for ticker in display:
            info = mkt.ASSETS.get(ticker, {"name": ticker, "market": "unknown"})
            pd   = mkt.fetch_ohlcv(ticker, period="30d")
            df   = pd.get("df")
            if df is None or df.empty:
                continue
            ind  = compute_all(df, info["market"])
            score = score_technical(ind, info["market"])
            price  = float(df["close"].iloc[-1])
            chg_1d = float(df["close"].pct_change().iloc[-1])
            chg_5d = float(df["close"].pct_change(5).iloc[-1]) if len(df) >= 5 else 0.0

            results.append({
                "ticker":     ticker,
                "asset":      info["name"],
                "market":     info["market"],
                "price":      round(price, 4),
                "change_1d":  round(chg_1d, 4),
                "change_5d":  round(chg_5d, 4),
                "signal":     "BUY" if score > 0.3 else ("SELL" if score < -0.3 else "HOLD"),
                "confidence": round(abs(score) * 0.9, 3),
                "stale":      pd.get("stale", False),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        return {"markets": results, "total": len(results),
                "regime": regime["regime"],
                "updated_at": datetime.now(timezone.utc).isoformat()}

    @app.get("/api/markets/sentiment")
    async def get_sentiment():
        from kairon.data import macro_data as md
        macro  = md.get_macro_snapshot()
        regime = md.classify_regime(macro)["regime"]
        vix    = macro.get("vix") or 14.2

        REGIME_SENTIMENT = {
            "Risk-On":      {"stocks":0.72,"crypto":0.63,"forex":0.10,
                              "commodities":0.25,"bonds":-0.20,"real_estate":0.44},
            "Risk-Off":     {"stocks":-0.38,"crypto":-0.55,"forex":0.15,
                              "commodities":0.60,"bonds":0.65,"real_estate":-0.20},
            "Inflationary": {"stocks":0.15,"crypto":0.20,"forex":0.10,
                              "commodities":0.81,"bonds":-0.50,"real_estate":0.45},
            "Crisis":       {"stocks":-0.75,"crypto":-0.82,"forex":0.20,
                              "commodities":0.55,"bonds":0.72,"real_estate":-0.60},
            "Deflationary": {"stocks":-0.20,"crypto":-0.30,"forex":0.05,
                              "commodities":-0.40,"bonds":0.70,"real_estate":-0.20},
            "Stagflationary":{"stocks":-0.45,"crypto":-0.50,"forex":0.00,
                               "commodities":0.50,"bonds":-0.30,"real_estate":-0.25},
        }
        scores = REGIME_SENTIMENT.get(regime, REGIME_SENTIMENT["Risk-On"])
        fg     = max(0, min(100, int(100 - (vix - 10) * 3)))

        return {
            "sentiments": {
                m: {"score": s, "direction": "bullish" if s > 0.1 else ("bearish" if s < -0.1 else "neutral"),
                    "confidence": round(0.5 + abs(s) * 0.4, 3)}
                for m, s in scores.items()
            },
            "fear_greed_index": fg,
            "regime": regime,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/markets/{ticker}")
    async def get_market_detail(ticker: str):
        from kairon.data import market_data as mkt
        from kairon.data.indicators import compute_all, score_technical

        info = mkt.ASSETS.get(ticker)
        if not info:
            raise HTTPException(404, detail=_err("TICKER_NOT_FOUND", f"Ticker {ticker} not found"))

        pd_data = mkt.fetch_ohlcv(ticker, period="1y")
        df = pd_data.get("df")
        if df is None or df.empty:
            raise HTTPException(422, detail=_err("INSUFFICIENT_HISTORY", "Not enough price history"))

        ind   = compute_all(df, info["market"])
        score = score_technical(ind, info["market"])
        price = float(df["close"].iloc[-1])

        history_30d = []
        for ts, row in df.tail(30).iterrows():
            history_30d.append({
                "date":   str(ts)[:10],
                "close":  round(float(row["close"]), 4),
                "volume": int(row.get("volume", 0)),
            })

        return {
            "asset":   info["name"],
            "ticker":  ticker,
            "market":  info["market"],
            "price":   round(price, 4),
            "ohlcv":   {
                "open":   round(float(df["open"].iloc[-1]), 4) if "open" in df else None,
                "high":   round(float(df["high"].iloc[-1]), 4) if "high" in df else None,
                "low":    round(float(df["low"].iloc[-1]), 4)  if "low"  in df else None,
                "close":  round(price, 4),
                "volume": int(df["volume"].iloc[-1]) if "volume" in df else 0,
            },
            "indicators": {k: v for k, v in ind.items()
                           if k not in ("market_type",) and v is not None},
            "history_30d": history_30d,
            "signal":      "BUY" if score > 0.3 else ("SELL" if score < -0.3 else "HOLD"),
            "confidence":  round(abs(score) * 0.9, 3),
            "stale":       pd_data.get("stale", False),
            "updated_at":  datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/markets/{ticker}/history")
    async def get_price_history(ticker: str,
                                 period:   str = Query("30d", regex="^(7d|30d|90d|1y|5y)$"),
                                 interval: str = Query("1d",  regex="^(1d|1h|15m)$")):
        from kairon.data import market_data as mkt
        pd_data = mkt.fetch_ohlcv(ticker, period=period)
        df = pd_data.get("df")
        if df is None or df.empty:
            raise HTTPException(404, detail=_err("TICKER_NOT_FOUND", f"No data for {ticker}"))

        data = []
        for ts, row in df.iterrows():
            data.append({
                "timestamp": str(ts),
                "open":    round(float(row.get("open",  row["close"])), 4),
                "high":    round(float(row.get("high",  row["close"])), 4),
                "low":     round(float(row.get("low",   row["close"])), 4),
                "close":   round(float(row["close"]), 4),
                "volume":  int(row.get("volume", 0)),
            })

        return {"ticker": ticker, "period": period, "interval": interval, "data": data}

    # ─────────────────────────────────────────────────────────────────────────
    # ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────
    @app.post("/api/analyze")
    async def run_analysis(req: AnalyzeRequest):
        from kairon.engine.analyzer import analyze
        try:
            result = analyze(
                ticker=req.ticker,
                market=req.market,
                capital_usd=req.capital_usd,
                from_market=req.from_market,
                holding_days=req.holding_days,
                unrealized_gain_pct=req.unrealized_gain_pct,
                regime_override=req.regime_override,
            )
            return result
        except TimeoutError:
            raise HTTPException(504, detail=_err("ANALYSIS_TIMEOUT", "Analysis timed out (>60s)"))
        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            raise HTTPException(500, detail=_err("ANALYSIS_ERROR", str(e)))

    @app.get("/api/analyze/{prediction_id}")
    async def get_analysis(prediction_id: str):
        from kairon.db import database as db
        row = db.execute_one("SELECT * FROM predictions WHERE id=?", (prediction_id,))
        if not row:
            raise HTTPException(404, detail=_err("NOT_FOUND", f"Prediction {prediction_id} not found"))
        return row

    @app.get("/api/analyze/{prediction_id}/connections")
    async def get_connections(prediction_id: str):
        """Build the connection graph for Screen 6 visualization."""
        from kairon.db import database as db
        row = db.execute_one("SELECT * FROM predictions WHERE id=?", (prediction_id,))
        if not row:
            raise HTTPException(404, detail=_err("NOT_FOUND", f"Prediction {prediction_id} not found"))

        nodes, edges = _build_connection_graph(row)
        forces_up   = _extract_increasing_forces(row)
        forces_down = _extract_decreasing_forces(row)

        return {
            "prediction_id":    prediction_id,
            "asset":            row.get("asset"),
            "nodes":            nodes,
            "edges":            edges,
            "increasing_forces": forces_up,
            "decreasing_forces": forces_down,
        }

    def _build_connection_graph(row: dict) -> tuple[list, list]:
        nodes = [
            {"id":"n_gdelt",   "type":"world_event",    "label":f"GDELT tone {row.get('gdelt_tone_72h',0):.1f}",
             "value": row.get("gdelt_tone_72h") or 0, "source":"GDELT"},
            {"id":"n_macro",   "type":"macro_indicator","label":f"Regime: {row.get('macro_regime','?')}",
             "value": row.get("macro_score") or 0,    "source":"FRED"},
            {"id":"n_tech",    "type":"price_signal",   "label":f"RSI {row.get('rsi',0):.0f}" if row.get('rsi') else "Technical",
             "value": row.get("technical_score") or 0,"source":"Yahoo"},
            {"id":"n_kb",      "type":"kb_match",       "label":"KB Historical",
             "value": 0.0,                             "source":"KB"},
            {"id":"n_final",   "type":"final_signal",   "label":f"{row.get('signal','?')} {row.get('asset','?')}",
             "value": row.get("composite_score") or 0, "source":"Fusion"},
        ]
        edges = []
        for src, tgt, w, lbl in [
            ("n_gdelt",  "n_final", row.get("news_score") or 0,         "news signal"),
            ("n_macro",  "n_final", row.get("macro_score") or 0,        "macro signal"),
            ("n_tech",   "n_final", row.get("technical_score") or 0,    "technical signal"),
            ("n_kb",     "n_final", 0.5,                                 "KB precedent"),
        ]:
            if abs(w) > 0.05:
                edges.append({
                    "source": src, "target": tgt,
                    "weight": round(abs(w), 3),
                    "direction": "positive" if w > 0 else "negative",
                    "label": lbl,
                })
        return nodes, edges

    def _extract_increasing_forces(row: dict) -> list:
        forces = []
        for key, label, evidence_fn in [
            ("macro_score",       "Macro regime",         lambda r: f"Regime: {r.get('macro_regime')}"),
            ("technical_score",   "Technical momentum",   lambda r: f"RSI {r.get('rsi',0):.0f}, MACD {r.get('macd',0):+.2f}"),
            ("news_score",        "News sentiment",        lambda r: f"GDELT tone: {r.get('gdelt_tone_72h',0):+.1f}"),
            ("fundamental_score", "Fundamentals",          lambda r: "Real yield / valuation"),
            ("cross_market_score","Cross-market",          lambda r: f"DXY {r.get('dxy',0):.1f}, VIX {r.get('vix',0):.1f}"),
        ]:
            v = row.get(key) or 0.0
            if v > 0.05:
                forces.append({"factor": label, "contribution": round(v, 3),
                                "evidence": evidence_fn(row)})
        return sorted(forces, key=lambda x: x["contribution"], reverse=True)

    def _extract_decreasing_forces(row: dict) -> list:
        forces = []
        for key, label, evidence_fn in [
            ("macro_score",       "Macro headwind",   lambda r: f"Regime: {r.get('macro_regime')}"),
            ("technical_score",   "Technical warning",lambda r: f"RSI {r.get('rsi',0):.0f}"),
            ("news_score",        "News headwind",     lambda r: f"Tone: {r.get('gdelt_tone_72h',0):+.1f}"),
            ("cross_market_score","Cross-mkt headwind",lambda r: f"DXY {r.get('dxy',0):.1f}"),
        ]:
            v = row.get(key) or 0.0
            if v < -0.05:
                forces.append({"factor": label, "contribution": round(v, 3),
                                "evidence": evidence_fn(row)})
        return sorted(forces, key=lambda x: x["contribution"])

    # ─────────────────────────────────────────────────────────────────────────
    # MOVES
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/moves")
    async def get_moves(
        capital:           float = Query(100000.0),
        min_confidence:    float = Query(0.50),
        min_net_profit_pct:float = Query(0.005),
        max_results:       int   = Query(10),
        regime_override:   Optional[str] = None,
    ):
        from kairon.engine.moves import get_move_recommendations
        result = get_move_recommendations(
            capital_usd=capital,
            min_confidence=min_confidence,
            max_results=max_results,
            regime_override=regime_override,
        )
        return result

    @app.post("/api/moves/{prediction_id}/execute")
    async def execute_move(prediction_id: str, req: DecisionRequest):
        from kairon.engine.analyzer import log_user_decision
        from kairon.db import database as db
        from datetime import timedelta

        row = db.execute_one("SELECT horizon_days FROM predictions WHERE id=?", (prediction_id,))
        if not row:
            raise HTTPException(404, detail=_err("NOT_FOUND", f"Prediction {prediction_id} not found"))

        ok = log_user_decision(prediction_id, "execute", req.notes, req.capital_usd)
        if not ok:
            raise HTTPException(500, detail=_err("LOG_FAILED", "Could not log decision"))

        h    = row.get("horizon_days") or 5
        when = datetime.now(timezone.utc).replace(microsecond=0)
        due  = when.replace(day=when.day + h) if False else \
               datetime.fromtimestamp(time.time() + h * 86400, tz=timezone.utc)

        return {
            "logged":                  True,
            "prediction_id":           prediction_id,
            "decision":                "execute",
            "outcome_check_scheduled": due.isoformat(),
            "message": f"Decision logged. Outcome will be recorded on {due.date()}.",
        }

    @app.post("/api/moves/{prediction_id}/pass")
    async def pass_move(prediction_id: str, req: PassRequest):
        from kairon.engine.analyzer import log_user_decision
        ok = log_user_decision(prediction_id, "pass", req.reason)
        return {"logged": ok, "prediction_id": prediction_id, "decision": "pass"}

    # ─────────────────────────────────────────────────────────────────────────
    # AGENTS
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/agents/signals")
    async def get_agent_signals():
        from kairon.data import macro_data as md
        macro  = md.get_macro_snapshot()
        regime = md.classify_regime(macro)

        # Quick per-market signals from macro regime
        from kairon.agents.agents import MacroAgent
        results = {}
        for agent_name in ["technical", "fundamental", "news", "macro", "cross_market"]:
            results[agent_name] = {
                "overall": 0.0,
                "by_market": {m: 0.0 for m in
                               ["stocks","crypto","forex","commodities","bonds","real_estate"]},
            }

        # Use Macro Agent which has full per-market regime scores
        for mkt in ["stocks","crypto","forex","commodities","bonds","real_estate"]:
            ctx = {"market": mkt, "asset": mkt, "macro": macro,
                   "regime": regime, "indicators": {}, "news_signal": {},
                   "ohlcv_df": None, "kb_context": {}, "capital_usd": 0, "vix": macro.get("vix",14)}
            from kairon.agents.agents import MacroAgent
            sig = MacroAgent().run(ctx)
            results["macro"]["by_market"][mkt] = sig.signal

        for agent in results:
            vals = list(results[agent]["by_market"].values())
            results[agent]["overall"] = round(sum(vals) / len(vals), 4) if vals else 0.0

        return {
            "signals":    results,
            "consensus":  round(sum(r["overall"] for r in results.values()) / len(results), 4),
            "regime":     regime["regime"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/agents/{agent_name}/reasoning/{ticker}")
    async def get_agent_reasoning(agent_name: str, ticker: str):
        from kairon.data import market_data as mkt, indicators as ind_mod, macro_data as md
        from kairon.data.news_fetcher import get_news_signal
        from kairon.agents.agents import (TechnicalAnalyst, FundamentalAnalyst,
                                           NewsAnalyst, MacroAgent, CrossMarketAgent)

        AGENTS = {
            "technical":    TechnicalAnalyst,
            "fundamental":  FundamentalAnalyst,
            "news":         NewsAnalyst,
            "macro":        MacroAgent,
            "cross_market": CrossMarketAgent,
        }
        if agent_name not in AGENTS:
            raise HTTPException(404, detail=_err("AGENT_NOT_FOUND", f"Agent {agent_name} not found"))

        info = mkt.ASSETS.get(ticker, {"name": ticker, "market": "stocks"})
        pd_data = mkt.fetch_ohlcv(ticker, period="1y")
        df      = pd_data.get("df")
        ind     = ind_mod.compute_all(df, info["market"]) if df is not None else {}
        macro   = md.get_macro_snapshot()
        regime  = md.classify_regime(macro)
        news    = get_news_signal(info["name"])

        ctx = {"ticker": ticker, "asset": info["name"], "market": info["market"],
               "indicators": ind, "ohlcv_df": df, "macro": macro,
               "regime": regime, "news_signal": news,
               "kb_context": {}, "capital_usd": 0, "vix": macro.get("vix", 14)}

        sig = AGENTS[agent_name]().run(ctx)
        return {
            "agent":      agent_name,
            "ticker":     ticker,
            "score":      sig.signal,
            "direction":  sig.direction,
            "confidence": sig.confidence,
            "reasoning":  sig.reasoning,
            "raw_data":   sig.raw_data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # KNOWLEDGE BASE
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/kb/stats")
    async def kb_stats():
        from kairon.intelligence.knowledge_base import KnowledgeBase
        stats = KnowledgeBase().get_stats()

        # Accuracy trend (vs 30d ago)
        from kairon.db import database as db
        old = db.execute_one(
            """SELECT ROUND(AVG(prediction_correct)*100,1) as acc FROM predictions
               WHERE prediction_correct IS NOT NULL
               AND created_at < datetime('now','-30 days')"""
        )
        current_acc = stats.get("overall_accuracy", 0) * 100
        old_acc     = (old.get("acc") or 0) if old else 0
        trend_str   = f"+{current_acc-old_acc:.1f}% vs 30 days ago" if old_acc else "Insufficient history"

        # By regime
        by_regime = db.execute(
            """SELECT macro_regime as regime, COUNT(*) as n,
                      ROUND(AVG(prediction_correct)*100,1) as accuracy_pct
               FROM predictions WHERE prediction_correct IS NOT NULL AND macro_regime IS NOT NULL
               GROUP BY macro_regime ORDER BY n DESC"""
        )

        return {**stats, "accuracy_trend": trend_str, "by_regime": by_regime,
                "updated_at": datetime.now(timezone.utc).isoformat()}

    @app.get("/api/kb/lessons")
    async def kb_lessons():
        from kairon.intelligence.knowledge_base import KnowledgeBase
        return {"lessons": KnowledgeBase().get_lessons()}

    @app.get("/api/kb/predictions")
    async def kb_predictions(
        page:      int = Query(1, ge=1),
        per_page:  int = Query(20, ge=1, le=100),
        asset:     Optional[str] = None,
        outcome:   Optional[str] = None,
        from_date: Optional[str] = None,
        to_date:   Optional[str] = None,
    ):
        from kairon.db import database as db

        where, params = ["1=1"], []
        if asset:
            where.append("asset=?"); params.append(asset)
        if outcome == "correct":
            where.append("prediction_correct=1")
        elif outcome == "wrong":
            where.append("prediction_correct=0")
        elif outcome == "pending":
            where.append("prediction_correct IS NULL")
        if from_date:
            where.append("created_at >= ?"); params.append(from_date)
        if to_date:
            where.append("created_at <= ?"); params.append(to_date)

        where_str = " AND ".join(where)
        offset    = (page - 1) * per_page
        total     = db.execute_one(f"SELECT COUNT(*) as n FROM predictions WHERE {where_str}", tuple(params))
        rows      = db.execute(
            f"""SELECT id, created_at, asset, market, signal, confidence,
                        prediction_correct, actual_return, user_decision, macro_regime
                FROM predictions WHERE {where_str}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            tuple(params) + (per_page, offset),
        )
        return {"predictions": rows, "total": total["n"] if total else 0,
                "page": page, "per_page": per_page}

    @app.post("/api/kb/similar")
    async def kb_similar(req: SimilarRequest):
        from kairon.intelligence.knowledge_base import KnowledgeBase
        from kairon.data.market_data import ASSETS

        info = ASSETS.get(req.ticker, {"name": req.ticker, "market": "unknown"})
        kb   = KnowledgeBase()
        ctx  = kb.find_similar(
            asset=info["name"],
            market=info.get("market", "unknown"),
            rsi=req.rsi,
            macro_regime=req.macro_regime,
            vix=req.vix,
            gdelt_tone=req.gdelt_tone,
            n_results=req.n_results,
        )
        return ctx

    # ─────────────────────────────────────────────────────────────────────────
    # COSTS
    # ─────────────────────────────────────────────────────────────────────────
    @app.post("/api/costs/calculate")
    async def calculate_costs(req: CostRequest):
        from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit

        costs = calculate_all_costs(
            amount_usd=req.amount_usd,
            from_market=req.from_market,
            to_market=req.to_market,
            to_asset=req.to_asset,
            holding_days=req.holding_days,
            unrealized_gain_pct=req.unrealized_gain_pct,
            vix=req.vix,
            is_news_event=req.is_news_event,
            is_on_chain=req.is_on_chain_transfer,
            tax_region=req.tax_region,
            tax_loss_carryforward=req.tax_loss_carryforward,
        )
        _, msg = passes_minimum_profit(0.02, costs)  # assume 2% gross

        return {**costs.to_dict(), "verdict_message": msg}

    # ─────────────────────────────────────────────────────────────────────────
    # PORTFOLIO
    # ─────────────────────────────────────────────────────────────────────────
    @app.post("/api/portfolio/validate")
    async def validate_portfolio(req: PortfolioRequest):
        from kairon.data import market_data as mkt
        from kairon.config import cfg

        validated, errors_global = [], []
        total_value = 0.0
        total_gain  = 0.0

        for h in req.holdings:
            info = mkt.ASSETS.get(h.ticker, {"name": h.ticker, "market": "stocks"})
            current_price = mkt.get_current_price(h.ticker)
            errs = []

            if current_price is None:
                errs.append(f"Ticker {h.ticker} not found")
                current_price = h.avg_price

            current_val  = current_price * h.quantity
            unreal_gain  = current_val - h.avg_price * h.quantity
            unreal_pct   = unreal_gain / (h.avg_price * h.quantity) if h.avg_price > 0 else 0

            is_long   = h.days_held >= cfg.tax_year_days
            tax_rate  = cfg.long_term_tax_rate if is_long else cfg.short_term_tax_rate
            tax_type  = "Long-term" if is_long else "Short-term"

            total_value += current_val
            total_gain  += unreal_gain

            validated.append({
                "ticker":          h.ticker,
                "name":            info["name"],
                "market":          info["market"],
                "quantity":        h.quantity,
                "avg_price":       h.avg_price,
                "current_price":   round(current_price, 4),
                "current_value":   round(current_val, 2),
                "unrealized_gain": round(unreal_gain, 2),
                "unrealized_pct":  round(unreal_pct, 4),
                "days_held":       h.days_held,
                "tax_rate":        tax_rate,
                "tax_type":        tax_type,
                "valid":           len(errs) == 0,
                "errors":          errs,
            })

        return {
            "valid":       all(h["valid"] for h in validated),
            "holdings":    validated,
            "total_value": round(total_value, 2),
            "total_gain":  round(total_gain, 2),
            "errors":      errors_global,
        }

    @app.post("/api/portfolio/analyze")
    async def analyze_portfolio(req: PortfolioRequest):
        from kairon.engine.moves import get_move_recommendations
        # Derive capital from portfolio value
        total_val = sum(h.avg_price * h.quantity for h in req.holdings)
        return get_move_recommendations(
            capital_usd=total_val,
            holding_days=req.holdings[0].days_held if req.holdings else 0,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # WEBSOCKET — Live price streaming
    # ─────────────────────────────────────────────────────────────────────────
    class ConnectionManager:
        def __init__(self):
            self.active: dict[WebSocket, set] = {}

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.active[ws] = set()

        def subscribe(self, ws: WebSocket, tickers: list):
            if ws in self.active:
                self.active[ws].update(tickers)

        def disconnect(self, ws: WebSocket):
            self.active.pop(ws, None)

        async def broadcast_prices(self, prices: dict):
            dead = []
            for ws, subs in self.active.items():
                try:
                    relevant = {t: p for t, p in prices.items()
                                if not subs or t in subs}
                    if relevant:
                        await ws.send_text(json.dumps({
                            "type":      "price_update",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "prices":    relevant,
                        }))
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

        async def broadcast_regime(self, old: str, new: str, vix: float):
            msg = json.dumps({
                "type":           "regime_change",
                "old_regime":     old,
                "new_regime":     new,
                "vix":            vix,
                "trigger":        f"Regime shifted from {old} to {new}",
                "timestamp":      datetime.now(timezone.utc).isoformat(),
                "action_required":"Review all open recommendations",
            })
            dead = []
            for ws in self.active:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

    _manager = ConnectionManager()
    _last_regime = {"regime": "Risk-On"}

    @app.websocket("/ws/prices")
    async def websocket_prices(websocket: WebSocket):
        await _manager.connect(websocket)
        try:
            # Read subscribe message
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            msg = json.loads(raw)
            if msg.get("action") == "subscribe":
                _manager.subscribe(websocket, msg.get("tickers", []))

            # Stream price updates every 3 seconds
            from kairon.data import market_data as mkt
            from kairon.data import macro_data as md

            while True:
                prices = {}
                subs   = _manager.active.get(websocket, set())
                target_tickers = list(subs) if subs else ["GC=F","BTC-USD","^GSPC"]

                for ticker in target_tickers:
                    price = mkt.get_current_price(ticker)
                    if price:
                        prices[ticker] = {"price": round(price, 4), "change_1d": 0.0}

                await _manager.broadcast_prices(prices)

                # Check for regime change
                macro  = md.get_macro_snapshot()
                regime = md.classify_regime(macro)
                if regime["regime"] != _last_regime.get("regime"):
                    await _manager.broadcast_regime(
                        _last_regime.get("regime", "Risk-On"),
                        regime["regime"],
                        macro.get("vix", 14.2),
                    )
                    _last_regime["regime"] = regime["regime"]

                await asyncio.sleep(3)

        except (WebSocketDisconnect, asyncio.TimeoutError):
            _manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            _manager.disconnect(websocket)

    # ─────────────────────────────────────────────────────────────────────────
    # BACKTESTING
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/backtest/{ticker}")
    async def run_backtest(ticker: str,
                           market:       str = Query("stocks"),
                           horizon_days: int = Query(5),
                           n_folds:      int = Query(5)):
        from kairon.intelligence.backtester import walk_forward_backtest
        result = walk_forward_backtest(
            ticker=ticker, market=market,
            horizon_days=horizon_days, n_folds=n_folds,
        )
        return result.to_dict()

    @app.get("/api/backtest/suite")
    async def run_backtest_suite(horizon_days: int = Query(5)):
        from kairon.intelligence.backtester import run_backtest_suite
        return run_backtest_suite(horizon_days=horizon_days)

    # ─────────────────────────────────────────────────────────────────────────
    # EXPLAINABILITY
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/analyze/{prediction_id}/explain")
    async def get_explanation(prediction_id: str):
        from kairon.db import database as db
        row = db.execute_one("SELECT * FROM predictions WHERE id=?", (prediction_id,))
        if not row:
            raise HTTPException(404, detail=_err("NOT_FOUND", f"Prediction {prediction_id} not found"))

        # Rebuild explainability from stored data
        from kairon.intelligence.explainability import build_full_explanation
        import json
        agent_signals = {}
        for ag in ["technical","fundamental","news","macro","cross_market"]:
            score = row.get(f"{ag}_score")
            if score is not None:
                agent_signals[ag] = {"signal": score, "confidence": 0.6, "reasoning": ""}

        expl = build_full_explanation(
            asset=row.get("asset",""), market=row.get("market",""),
            ticker=row.get("ticker",""), decision=row.get("signal","HOLD"),
            composite=row.get("composite_score",0),
            confidence=row.get("confidence",0.5),
            indicators={"rsi": row.get("rsi"), "macd": row.get("macd"),
                        "trend": row.get("trend"), "close": row.get("price"),
                        "vol_ratio": row.get("volume_ratio"), "bb_pos": row.get("bb_position"),
                        "atr_pct": row.get("atr_pct"), "momentum_10": row.get("momentum_10"),
                        "z_score_20": row.get("z_score_20")},
            macro={"vix": row.get("vix"), "dxy": row.get("dxy"),
                   "fed_rate": row.get("fed_rate"), "real_yield_10y": row.get("real_yield_10y"),
                   "yield_curve": row.get("yield_curve")},
            news={"gdelt_tone_72h": row.get("gdelt_tone_72h"),
                  "gdelt_mentions": row.get("gdelt_mentions"),
                  "sentiment_label": row.get("sentiment_label"),
                  "signal": row.get("news_impact")},
            agent_signals=agent_signals,
            kb_context={"n_similar": 0, "n_correct": 0, "accuracy": 0.5,
                        "has_history": False, "avg_return": 0},
            costs={"total_cost_pct": row.get("total_cost_usd", 0) / max(1, row.get("capital_usd", 1) / 100)},
            horizon_days=row.get("horizon_days", 5),
        )
        return {"prediction_id": prediction_id, **expl}

    # ─────────────────────────────────────────────────────────────────────────
    # TIMING
    # ─────────────────────────────────────────────────────────────────────────
    @app.get("/api/timing/{ticker}")
    async def get_timing(ticker: str,
                          market:    str   = Query("stocks"),
                          composite: float = Query(0.5),
                          force:     str   = Query("technical_breakout"),
                          horizon:   int   = Query(5),
                          vix:       float = Query(14.2)):
        from kairon.engine.timing_engine import get_timing_recommendation
        timing = get_timing_recommendation(
            composite_score=composite, force_type=force,
            market=market, ticker=ticker,
            horizon_days=horizon, vix=vix,
        )
        return timing.to_dict()

    @app.get("/api/analyze/{prediction_id}/velocity")
    async def get_signal_velocity(prediction_id: str):
        """Return signal velocity data for the explainability panel."""
        from kairon.db import database as db
        from kairon.intelligence.signal_velocity import (
            get_signal_velocities_for_asset, get_overall_velocity_label,
        )
        row = db.execute_one("SELECT asset FROM predictions WHERE id=?", (prediction_id,))
        if not row:
            raise HTTPException(404, detail=_err("NOT_FOUND", f"Prediction {prediction_id} not found"))

        readings     = get_signal_velocities_for_asset(row["asset"])
        overall      = get_overall_velocity_label(readings)
        return {
            "prediction_id": prediction_id,
            "asset":         row["asset"],
            "readings":      [r.to_dict() for r in readings],
            "overall_label": overall,
        }


        from kairon.engine.timing_engine import get_upcoming_events
        events = get_upcoming_events(market, "", days_ahead)
        return {"market": market, "events": events, "count": len(events)}


    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "code": "INTERNAL_ERROR",
                     "detail": str(exc)},
        )

else:
    # Stub when FastAPI not installed
    app = None
    logger.warning("FastAPI not installed — API server unavailable. "
                   "Run: pip install fastapi uvicorn")


if __name__ == "__main__":
    if app is None:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
    else:
        import uvicorn
        uvicorn.run("kairon.api.main:app", host="0.0.0.0", port=8000, reload=True)
