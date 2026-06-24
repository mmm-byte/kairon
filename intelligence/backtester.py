"""
kairon/intelligence/backtester.py
Walk-forward backtesting from Document 12 Phase 6.
Strict no look-ahead bias: each fold only uses data available at that point in time.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger("kairon.backtest")


@dataclass
class BacktestResult:
    n_predictions:    int
    n_correct:        int
    accuracy:         float
    avg_return:       float
    sharpe_ratio:     float
    max_drawdown:     float
    win_rate:         float
    profit_factor:    float
    total_return_pct: float
    by_signal:        dict = field(default_factory=dict)
    by_market:        dict = field(default_factory=dict)
    folds:            list = field(default_factory=list)
    warnings:         list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_predictions":    self.n_predictions,
            "n_correct":        self.n_correct,
            "accuracy":         round(self.accuracy, 4),
            "avg_return":       round(self.avg_return, 4),
            "sharpe_ratio":     round(self.sharpe_ratio, 3),
            "max_drawdown":     round(self.max_drawdown, 4),
            "win_rate":         round(self.win_rate, 4),
            "profit_factor":    round(self.profit_factor, 3),
            "total_return_pct": round(self.total_return_pct, 2),
            "by_signal":        self.by_signal,
            "by_market":        self.by_market,
            "folds":            self.folds,
            "warnings":         self.warnings,
            "grade":            self._grade(),
        }

    def _grade(self) -> str:
        if self.accuracy >= 0.70 and self.sharpe_ratio >= 1.0:
            return "A"
        if self.accuracy >= 0.60 and self.sharpe_ratio >= 0.5:
            return "B"
        if self.accuracy >= 0.55:
            return "C"
        return "D"


def _rolling_technical_score(df_window: pd.DataFrame, market: str) -> float:
    """Quick technical score on a window of data — used inside backtest."""
    from kairon.data.indicators import compute_all, score_technical
    ind = compute_all(df_window, market)
    return score_technical(ind, market)


def _simulate_outcome(entry_price: float, signal: str,
                       future_prices: pd.Series, horizon_days: int) -> dict:
    """
    Given a signal and future prices, compute actual outcome.
    No look-ahead: future_prices only contains data AFTER entry.
    """
    if future_prices.empty or len(future_prices) < horizon_days:
        return {"outcome": "insufficient_data", "return": 0.0, "correct": None}

    exit_price   = float(future_prices.iloc[min(horizon_days - 1, len(future_prices) - 1)])
    actual_ret   = (exit_price - entry_price) / entry_price

    predicted_up = signal == "UP"
    actually_up  = actual_ret > 0
    correct      = predicted_up == actually_up

    return {
        "outcome":      "correct" if correct else "wrong",
        "return":       round(actual_ret, 5),
        "correct":      correct,
        "entry_price":  entry_price,
        "exit_price":   exit_price,
    }


def walk_forward_backtest(
    ticker:          str,
    market:          str,
    horizon_days:    int  = 5,
    n_folds:         int  = 6,
    min_train_days:  int  = 180,
    fold_size_days:  int  = 60,
    capital:         float = 10000.0,
) -> BacktestResult:
    """
    Walk-forward backtest with strict temporal ordering.
    
    Structure:
      Fold 1: train on days 0–179,   test on days 180–239
      Fold 2: train on days 0–239,   test on days 240–299
      Fold 3: train on days 0–299,   test on days 300–359
      ... etc.
    
    No data from the test window ever touches the train window.
    """
    from kairon.data.market_data import fetch_ohlcv

    logger.info(f"Starting walk-forward backtest: {ticker} / {market}")
    warnings = []

    # Fetch historical data
    price_data = fetch_ohlcv(ticker, period="5y")
    df         = price_data.get("df")
    if df is None or df.empty:
        return BacktestResult(
            n_predictions=0, n_correct=0, accuracy=0.0, avg_return=0.0,
            sharpe_ratio=0.0, max_drawdown=0.0, win_rate=0.0, profit_factor=0.0,
            total_return_pct=0.0,
            warnings=["No price data available for backtesting"],
        )

    total_days = len(df)
    required   = min_train_days + n_folds * fold_size_days + horizon_days
    if total_days < required:
        warnings.append(f"Only {total_days} days available; need {required}. "
                        f"Reducing folds from {n_folds} to {max(1,(total_days - min_train_days) // fold_size_days)}.")
        n_folds = max(1, (total_days - min_train_days - horizon_days) // fold_size_days)

    all_predictions = []
    fold_results    = []

    for fold in range(n_folds):
        train_end    = min_train_days + fold * fold_size_days
        test_start   = train_end
        test_end     = min(test_start + fold_size_days, total_days - horizon_days)

        if test_start >= total_days - horizon_days:
            break

        train_df = df.iloc[:train_end]
        test_df  = df.iloc[test_start:test_end]

        fold_preds = []
        for i in range(0, len(test_df), max(1, horizon_days)):
            if test_start + i + horizon_days >= total_days:
                break

            # Signal using only train + test data up to point i (NO FUTURE DATA)
            window    = pd.concat([train_df, test_df.iloc[:i + 1]])
            score     = _rolling_technical_score(window.tail(200), market)

            signal    = "UP" if score > 0.15 else ("DOWN" if score < -0.15 else "HOLD")
            if signal == "HOLD":
                continue   # skip HOLD predictions for cleaner metrics

            entry_price   = float(test_df["close"].iloc[i])
            future_prices = df["close"].iloc[test_start + i + 1: test_start + i + 1 + horizon_days]
            outcome       = _simulate_outcome(entry_price, signal, future_prices, horizon_days)

            if outcome["correct"] is None:
                continue

            pred = {
                "fold":         fold + 1,
                "date":         str(test_df.index[i])[:10],
                "signal":       signal,
                "score":        round(score, 4),
                "entry_price":  entry_price,
                "exit_price":   outcome["exit_price"],
                "return":       outcome["return"],
                "correct":      outcome["correct"],
                "market":       market,
            }
            fold_preds.append(pred)
            all_predictions.append(pred)

        if fold_preds:
            fold_acc  = sum(1 for p in fold_preds if p["correct"]) / len(fold_preds)
            fold_ret  = sum(p["return"] for p in fold_preds if p["correct"]) / max(1, len(fold_preds))
            fold_results.append({
                "fold":         fold + 1,
                "n_predictions": len(fold_preds),
                "accuracy":     round(fold_acc, 3),
                "avg_return":   round(fold_ret, 4),
                "train_days":   train_end,
                "test_days":    len(test_df),
                "date_start":   str(test_df.index[0])[:10],
                "date_end":     str(test_df.index[-1])[:10],
            })

    if not all_predictions:
        return BacktestResult(
            n_predictions=0, n_correct=0, accuracy=0.0, avg_return=0.0,
            sharpe_ratio=0.0, max_drawdown=0.0, win_rate=0.0, profit_factor=0.0,
            total_return_pct=0.0, folds=fold_results,
            warnings=warnings + ["No valid predictions generated"],
        )

    n_total   = len(all_predictions)
    n_correct = sum(1 for p in all_predictions if p["correct"])
    accuracy  = n_correct / n_total

    returns   = [p["return"] for p in all_predictions]
    avg_ret   = float(np.mean(returns))
    std_ret   = float(np.std(returns)) or 0.001
    sharpe    = (avg_ret / std_ret) * np.sqrt(252 / horizon_days)

    # Max drawdown on equity curve
    equity    = capital
    peak      = capital
    max_dd    = 0.0
    for r in returns:
        equity *= (1 + r)
        peak   = max(peak, equity)
        dd     = (peak - equity) / peak
        max_dd = max(max_dd, dd)

    wins      = [r for r in returns if r > 0]
    losses    = [r for r in returns if r <= 0]
    pf        = (sum(wins) / max(0.0001, abs(sum(losses)))) if losses else float("inf")
    total_ret = ((equity - capital) / capital) * 100

    # By signal
    by_signal = {}
    for sig in ("UP", "DOWN"):
        sp = [p for p in all_predictions if p["signal"] == sig]
        if sp:
            by_signal[sig] = {
                "n":        len(sp),
                "accuracy": round(sum(1 for p in sp if p["correct"]) / len(sp), 3),
                "avg_ret":  round(float(np.mean([p["return"] for p in sp])), 4),
            }

    if accuracy < 0.55:
        warnings.append(f"Overall accuracy {accuracy:.0%} is below 55% threshold. "
                        "Consider reviewing signal quality.")
    if sharpe < 0:
        warnings.append("Negative Sharpe ratio — strategy loses money on average.")
    if max_dd > 0.20:
        warnings.append(f"Max drawdown {max_dd:.0%} is high. Consider tighter risk controls.")

    return BacktestResult(
        n_predictions=n_total,
        n_correct=n_correct,
        accuracy=accuracy,
        avg_return=avg_ret,
        sharpe_ratio=float(sharpe),
        max_drawdown=max_dd,
        win_rate=len(wins) / n_total,
        profit_factor=pf,
        total_return_pct=total_ret,
        by_signal=by_signal,
        by_market={market: {"n": n_total, "accuracy": accuracy}},
        folds=fold_results,
        warnings=warnings,
    )


def run_backtest_suite(
    tickers_markets: list[tuple[str, str]] = None,
    horizon_days: int = 5,
) -> dict:
    """
    Run backtests across multiple assets and aggregate results.
    Used for Phase 6 validation (Document 12).
    """
    if tickers_markets is None:
        tickers_markets = [
            ("GC=F", "commodities"),
            ("BTC-USD", "crypto"),
            ("SPY", "stocks"),
            ("EURUSD=X", "forex"),
        ]

    suite_results = {}
    for ticker, market in tickers_markets:
        logger.info(f"Backtesting {ticker}...")
        try:
            result = walk_forward_backtest(
                ticker=ticker, market=market, horizon_days=horizon_days,
            )
            suite_results[ticker] = result.to_dict()
        except Exception as e:
            logger.error(f"Backtest failed for {ticker}: {e}")
            suite_results[ticker] = {"error": str(e)}

    # Aggregate
    valid = [v for v in suite_results.values() if "error" not in v and v["n_predictions"] > 0]
    if valid:
        avg_acc  = sum(v["accuracy"] for v in valid) / len(valid)
        avg_sr   = sum(v["sharpe_ratio"] for v in valid) / len(valid)
        passed   = sum(1 for v in valid if v["accuracy"] >= 0.60)
        suite_results["_summary"] = {
            "n_assets":      len(valid),
            "avg_accuracy":  round(avg_acc, 3),
            "avg_sharpe":    round(avg_sr, 3),
            "assets_passed": passed,
            "grade":         "PASS" if avg_acc >= 0.60 else "FAIL",
            "generated_at":  datetime.now(timezone.utc).isoformat(),
        }

    return suite_results
