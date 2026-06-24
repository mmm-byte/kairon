"""
kairon/intelligence/knowledge_base.py
Prediction storage, similarity search, lesson extraction.
Uses pure numpy cosine similarity (ChromaDB optional upgrade).
Document 05 implementation.
"""
import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from kairon.db import database as db

logger = logging.getLogger("kairon.kb")


def _norm(v: Optional[float], lo: float, hi: float) -> float:
    if v is None:
        return 0.5  # neutral when unknown
    return max(0.0, min(1.0, (v - lo) / (hi - lo + 1e-9)))


def embed_prediction(rsi: float, vix: float, gdelt_tone: float,
                      macro_regime: str, z_score: float = 0.0,
                      vol_ratio: float = 1.0, macd: float = 0.0) -> np.ndarray:
    """
    32-dimensional market fingerprint vector from Document 05.
    All values normalised to [0, 1] for consistent cosine distance.
    """
    regime_one_hot = [
        1.0 if macro_regime == "Risk-On"       else 0.0,
        1.0 if macro_regime == "Risk-Off"      else 0.0,
        1.0 if macro_regime == "Inflationary"  else 0.0,
        1.0 if macro_regime == "Deflationary"  else 0.0,
        1.0 if macro_regime == "Stagflationary" else 0.0,
        1.0 if macro_regime == "Crisis"         else 0.0,
    ]
    vec = [
        _norm(rsi,        0,   100),
        _norm(macd,      -20,   20),
        _norm(z_score,   -3,     3),
        _norm(vol_ratio,  0,     3),
        _norm(vix,       10,    80),
        _norm(gdelt_tone,-5,     5),
        *regime_one_hot,
        # Pad to 32 dims with zeros (for future features)
        *([0.0] * (32 - 6 - len(regime_one_hot))),
    ]
    arr = np.array(vec[:32], dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    na  = np.linalg.norm(a)
    nb  = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))


class KnowledgeBase:
    """In-process knowledge base with numpy similarity search."""

    def find_similar(
        self,
        asset: str,
        market: str,
        rsi: Optional[float],
        macro_regime: str,
        vix: float,
        gdelt_tone: float,
        n_results: int = 10,
        min_similarity: float = 0.75,
    ) -> dict:
        """
        Find similar historical situations and return KB context.
        Only uses resolved predictions (outcome known).
        """
        query_vec = embed_prediction(
            rsi=rsi or 50.0,
            vix=vix,
            gdelt_tone=gdelt_tone,
            macro_regime=macro_regime,
        )

        # Fetch resolved predictions for this asset
        rows = db.execute(
            """SELECT id, rsi, vix, gdelt_tone_72h, macro_regime, z_score_20,
                      volume_ratio as vol_ratio, macd, prediction_correct, actual_return,
                      signal, confidence, created_at, outcome_notes
               FROM predictions
               WHERE asset=? AND prediction_correct IS NOT NULL
               ORDER BY created_at DESC LIMIT 200""",
            (asset,),
        )

        if not rows:
            return self._empty_context(asset)

        # Score similarity
        scored = []
        for row in rows:
            rv = embed_prediction(
                rsi=row.get("rsi") or 50.0,
                vix=row.get("vix") or 14.2,
                gdelt_tone=row.get("gdelt_tone_72h") or 0.0,
                macro_regime=row.get("macro_regime") or "Risk-On",
                z_score=row.get("z_score_20") or 0.0,
                vol_ratio=row.get("vol_ratio") or 1.0,
                macd=row.get("macd") or 0.0,
            )
            sim = _cosine_similarity(query_vec, rv)
            if sim >= min_similarity:
                scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]

        if not top:
            return self._empty_context(asset)

        n_total   = len(top)
        n_correct = sum(1 for _, r in top if r.get("prediction_correct") == 1)
        accuracy  = n_correct / n_total
        avg_ret   = sum(r.get("actual_return") or 0.0 for _, r in top) / n_total

        matches = []
        for sim, r in top[:5]:
            correct = r.get("prediction_correct")
            matches.append({
                "date":      r["created_at"][:10],
                "signal":    r.get("signal"),
                "outcome":   "CORRECT" if correct == 1 else ("WRONG" if correct == 0 else "PENDING"),
                "return":    round((r.get("actual_return") or 0.0) * 100, 2),
                "similarity": round(sim, 3),
                "notes":     r.get("outcome_notes") or "",
            })

        precedent = (f"KB: {n_correct}/{n_total} similar setups correct "
                     f"(avg return +{avg_ret*100:.1f}%)")

        return {
            "n_similar":      n_total,
            "n_correct":      n_correct,
            "accuracy":       round(accuracy, 3),
            "avg_return":     round(avg_ret, 4),
            "top_matches":    matches,
            "precedent_text": precedent,
            "has_history":    True,
        }

    def _empty_context(self, asset: str) -> dict:
        return {
            "n_similar":      0,
            "n_correct":      0,
            "accuracy":       0.5,
            "avg_return":     0.0,
            "top_matches":    [],
            "precedent_text": f"No similar history yet for {asset} — building KB",
            "has_history":    False,
        }

    def record_outcome(self, prediction_id: str, actual_price: float) -> bool:
        """Called by the daily background job to record outcomes."""
        try:
            row = db.execute_one(
                "SELECT price, signal, horizon_days FROM predictions WHERE id=?",
                (prediction_id,),
            )
            if not row:
                return False
            entry_price  = row["price"]
            actual_return = (actual_price - entry_price) / entry_price
            predicted_up  = row["signal"] == "UP"
            actually_up   = actual_return > 0
            correct       = 1 if predicted_up == actually_up else 0

            db.execute(
                """UPDATE predictions SET
                   actual_price=?, actual_return=?, prediction_correct=?, outcome_date=?
                   WHERE id=?""",
                (actual_price, actual_return, correct,
                 datetime.now(timezone.utc).isoformat(), prediction_id),
            )
            logger.info(f"Recorded outcome {prediction_id}: {'CORRECT' if correct else 'WRONG'} "
                        f"({actual_return:+.2%})")
            return True
        except Exception as e:
            logger.error(f"Outcome recording failed: {e}")
            return False

    def get_stats(self) -> dict:
        """Overall KB statistics for Screen 4."""
        total = db.execute_one("SELECT COUNT(*) as n FROM predictions")
        resolved = db.execute_one(
            "SELECT COUNT(*) as n, AVG(prediction_correct) as acc, AVG(actual_return) as ret "
            "FROM predictions WHERE prediction_correct IS NOT NULL"
        )
        lessons = db.execute_one("SELECT COUNT(*) as n FROM lessons WHERE active=1")
        by_asset = db.execute(
            """SELECT asset, COUNT(*) as n,
                      ROUND(AVG(prediction_correct)*100,1) as accuracy_pct,
                      ROUND(AVG(actual_return)*100,2) as avg_return_pct
               FROM predictions
               WHERE prediction_correct IS NOT NULL
               GROUP BY asset HAVING COUNT(*)>=3
               ORDER BY accuracy_pct DESC LIMIT 10"""
        )
        return {
            "total_predictions": total["n"] if total else 0,
            "with_outcomes":     resolved["n"] if resolved else 0,
            "overall_accuracy":  round((resolved.get("acc") or 0.0), 3) if resolved else 0.0,
            "avg_return":        round((resolved.get("ret") or 0.0) * 100, 2) if resolved else 0.0,
            "total_lessons":     lessons["n"] if lessons else 0,
            "by_asset":          by_asset,
        }

    def get_recent_predictions(self, limit: int = 50) -> list:
        return db.execute(
            """SELECT id, created_at, asset, market, signal, confidence,
                      prediction_correct, actual_return, user_decision
               FROM predictions ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )

    def get_lessons(self) -> list:
        return db.execute(
            "SELECT * FROM lessons WHERE active=1 ORDER BY accuracy DESC LIMIT 20"
        )
