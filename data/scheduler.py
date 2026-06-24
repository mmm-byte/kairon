"""
kairon/data/scheduler.py
APScheduler background jobs from Document 02:
  - Every 15 min: prices, GDELT, indicators, sentiment
  - Every 1 hour:  FRED macro, correlation matrix, regime check
  - Daily 06:00 UTC: outcome recording, lesson extraction, KB stats
Designed to run as a standalone process or alongside the API server.
"""
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("kairon.scheduler")


def job_refresh_prices():
    """Fetch latest prices and indicators for all watchlist assets."""
    from kairon.data import market_data as mkt, indicators as ind_mod
    from kairon.data import cache as cache_mod

    logger.info("Scheduler: refreshing prices")
    from kairon.engine.moves import WATCHLIST
    refreshed = 0
    for ticker, (name, market) in WATCHLIST.items():
        try:
            result = mkt.fetch_ohlcv(ticker, period="1y")
            df = result.get("df")
            if df is not None and not df.empty:
                cache_mod.set_price(ticker, result)
                ind = ind_mod.compute_all(df, market)
                cache_mod.set_indicators(ticker, ind)
                refreshed += 1
        except Exception as e:
            logger.warning(f"Price refresh failed for {ticker}: {e}")
    logger.info(f"Prices refreshed: {refreshed}/{len(WATCHLIST)} tickers")


def job_refresh_news():
    """Refresh news signals for all key assets."""
    from kairon.data import news_fetcher, cache as cache_mod

    ASSETS_TO_WATCH = [
        "Gold", "Bitcoin", "Crude Oil", "EUR/USD", "US 10Y", "S&P 500", "Copper"
    ]
    logger.info("Scheduler: refreshing news")
    for asset in ASSETS_TO_WATCH:
        try:
            sig = news_fetcher.get_news_signal(asset)
            cache_mod.set_news(asset, [sig])
            logger.debug(f"News signal for {asset}: {sig.get('signal',0):+.3f}")
        except Exception as e:
            logger.warning(f"News refresh failed for {asset}: {e}")


def job_refresh_macro():
    """Refresh FRED macro data, update regime, and take correlation snapshot."""
    from kairon.data import macro_data as md, cache as cache_mod
    from kairon.db import database as db
    import uuid

    logger.info("Scheduler: refreshing macro data")
    try:
        macro  = md.get_macro_snapshot()
        regime = md.classify_regime(macro)

        # Save regime change to history if changed
        current = cache_mod.get_regime()
        if not current or current.get("regime") != regime["regime"]:
            prev = current.get("regime") if current else None
            db.insert("regime_history", {
                "id":              str(uuid.uuid4()),
                "regime":          regime["regime"],
                "previous_regime": prev,
                "vix":             macro.get("vix"),
                "dxy":             macro.get("dxy"),
                "trigger":         regime.get("reasoning", "")[:200],
                "confidence":      regime.get("confidence"),
            })
            logger.info(f"Regime changed: {prev} → {regime['regime']}")

        cache_mod.set_regime({**macro, **regime})
        logger.info(f"Macro refreshed: regime={regime['regime']}, VIX={macro.get('vix'):.1f}")

        # Update correlation snapshot
        try:
            from kairon.intelligence.correlation_tracker import snapshot_and_save
            snapshot_and_save(regime["regime"])
        except Exception as ce:
            logger.warning(f"Correlation snapshot failed: {ce}")

    except Exception as e:
        logger.error(f"Macro refresh failed: {e}")


def job_record_outcomes():
    """
    Daily job: find all predictions whose horizon has passed,
    fetch actual prices, record outcomes, trigger lesson extraction.
    """
    from kairon.db import database as db
    from kairon.intelligence.knowledge_base import KnowledgeBase
    from kairon.data import market_data as mkt

    logger.info("Scheduler: recording outcomes")
    kb = KnowledgeBase()

    # Find predictions due for outcome recording
    due = db.execute("""
        SELECT id, ticker, price, signal, horizon_days, created_at
        FROM predictions
        WHERE prediction_correct IS NULL
          AND outcome_date IS NULL
          AND datetime(created_at, '+' || horizon_days || ' days') < datetime('now')
        ORDER BY created_at ASC
        LIMIT 100
    """)

    recorded = 0
    for row in due:
        try:
            actual_price = mkt.get_current_price(row["ticker"])
            if actual_price is None:
                continue
            ok = kb.record_outcome(row["id"], actual_price)
            if ok:
                recorded += 1
        except Exception as e:
            logger.warning(f"Outcome recording failed for {row['id']}: {e}")

    logger.info(f"Outcomes recorded: {recorded}/{len(due)}")


def job_extract_lessons():
    """Scan prediction history for high-confidence patterns worth extracting."""
    from kairon.db import database as db
    import uuid, json

    logger.info("Scheduler: checking for new lessons")
    # Find asset+regime combos with enough data
    combos = db.execute("""
        SELECT asset, macro_regime, COUNT(*) as n,
               ROUND(AVG(prediction_correct)*100,1) as acc,
               ROUND(AVG(actual_return)*100,2) as avg_ret
        FROM predictions
        WHERE prediction_correct IS NOT NULL AND macro_regime IS NOT NULL
        GROUP BY asset, macro_regime
        HAVING COUNT(*) >= 10
    """)

    for c in combos:
        acc = (c.get("acc") or 0) / 100
        if acc < 0.65:
            continue

        # Check if this lesson already exists
        existing = db.execute_one(
            "SELECT id FROM lessons WHERE asset=? AND macro_regime=? AND active=1",
            (c["asset"], c["macro_regime"]),
        )

        level = "high" if c["n"] >= 20 else "medium"
        desc  = f"{c['asset']} in {c['macro_regime']} regime"

        if existing:
            db.execute(
                """UPDATE lessons SET n_observations=?, n_correct=?, accuracy=?,
                   avg_return=?, confidence_level=?, updated_at=datetime('now')
                   WHERE id=?""",
                (c["n"], int(acc * c["n"]), acc,
                 (c.get("avg_ret") or 0) / 100, level, existing["id"]),
            )
        else:
            lesson_id = str(uuid.uuid4())
            db.insert("lessons", {
                "id":             lesson_id,
                "asset":          c["asset"],
                "macro_regime":   c["macro_regime"],
                "pattern_type":   "macro",
                "pattern_code":   f"{c['asset']}_{c['macro_regime']}".lower().replace(" ","_"),
                "description":    desc,
                "conditions":     json.dumps({"asset": c["asset"], "macro_regime": c["macro_regime"]}),
                "n_observations": c["n"],
                "n_correct":      int(acc * c["n"]),
                "accuracy":       acc,
                "avg_return":     (c.get("avg_ret") or 0) / 100,
                "confidence_level": level,
                "is_negative":    0 if acc >= 0.65 else 1,
                "active":         1,
            })
            logger.info(f"New lesson extracted: {desc} ({acc:.0%} accuracy, {c['n']} obs)")


def start_scheduler():
    """Start APScheduler with all background jobs."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("APScheduler not installed — background jobs disabled. "
                       "Run: pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    # Every 15 minutes during market hours (+ always for crypto)
    scheduler.add_job(job_refresh_prices, IntervalTrigger(minutes=15),
                      id="refresh_prices", max_instances=1, coalesce=True)

    # Every 15 minutes
    scheduler.add_job(job_refresh_news, IntervalTrigger(minutes=15),
                      id="refresh_news", max_instances=1, coalesce=True)

    # Every 1 hour
    scheduler.add_job(job_refresh_macro, IntervalTrigger(hours=1),
                      id="refresh_macro", max_instances=1, coalesce=True)

    # Daily at 06:00 UTC
    scheduler.add_job(job_record_outcomes, CronTrigger(hour=6, minute=0),
                      id="record_outcomes", max_instances=1)

    # Daily at 07:00 UTC (after outcomes are in)
    scheduler.add_job(job_extract_lessons, CronTrigger(hour=7, minute=0),
                      id="extract_lessons", max_instances=1)

    scheduler.start()
    logger.info("Background scheduler started (prices/news: 15min, macro: 1h, outcomes: daily)")
    return scheduler


if __name__ == "__main__":
    # Run scheduler standalone for testing
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    from kairon.db.database import init_db
    init_db()

    sched = start_scheduler()
    if sched:
        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            sched.shutdown()
            print("Scheduler stopped.")
