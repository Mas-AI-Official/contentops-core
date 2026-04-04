"""
Method Optimizer — Self-Tuning Performance Loop.

Scores all content methods, promotes winners, retires losers,
and generates new test hypotheses.

Runs daily at 02:00 to process accumulated metrics.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger("contentops.method_optimizer")


class MethodOptimizer:
    """Self-improvement brain. Scores methods, promotes/retires, generates hypotheses."""

    # Promotion thresholds
    PROMOTED_THRESHOLD = 8.5
    ACTIVE_THRESHOLD = 6.0
    TESTING_THRESHOLD = 4.0
    MIN_SAMPLES = 5  # Minimum data points before scoring

    def __init__(self, db_path: str = "data/contentops.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")

    def run_daily_optimization(self) -> dict:
        """Main daily optimization loop."""
        logger.info("Running daily method optimization...")

        # Step 1: Score all methods
        scores = self._score_all_methods()

        # Step 2: Promote/retire
        promotions = self._apply_promotions(scores)

        # Step 3: Update method_scores table
        self._persist_scores(scores)

        # Step 4: Generate report
        report = self._generate_report(scores, promotions)

        # Save report
        reports_dir = Path("data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"optimization_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Optimization complete. Report: {report_path}")
        return report

    def _score_all_methods(self) -> list[dict]:
        """Score all methods with enough data."""
        with self.engine.connect() as conn:
            # Get unique methods with their latest metrics
            rows = conn.execute(text("""
                SELECT p.method_tag, p.hook_type,
                    COUNT(DISTINCT p.id) as sample_count,
                    AVG(pm.completion_rate) as avg_completion,
                    AVG(CASE WHEN pm.views > 0 THEN CAST(pm.shares AS REAL) / pm.views ELSE 0 END) as avg_share_rate,
                    AVG(CASE WHEN pm.views > 0 THEN CAST(pm.saves AS REAL) / pm.views ELSE 0 END) as avg_save_rate,
                    AVG(CASE WHEN pm.views > 0 THEN CAST(pm.comments AS REAL) / pm.views ELSE 0 END) as avg_comment_rate,
                    SUM(pm.views) as total_views
                FROM posts p
                LEFT JOIN post_metrics pm ON p.id = pm.post_id
                WHERE p.method_tag IS NOT NULL
                GROUP BY p.method_tag
                HAVING COUNT(DISTINCT p.id) >= :min_samples
            """), {"min_samples": self.MIN_SAMPLES}).fetchall()

        scores = []
        for row in rows:
            composite = (
                min((row[3] or 0) * 10, 10) * 0.30 +
                min((row[4] or 0) * 200, 10) * 0.25 +
                min((row[5] or 0) * 200, 10) * 0.20 +
                min((row[6] or 0) * 100, 10) * 0.15 +
                2.0 * 0.10  # Base engagement
            )

            scores.append({
                "method_tag": row[0],
                "hook_type": row[1],
                "sample_count": row[2],
                "avg_completion_rate": round(row[3] or 0, 3),
                "avg_share_rate": round(row[4] or 0, 4),
                "avg_save_rate": round(row[5] or 0, 4),
                "composite_score": round(composite, 2),
                "total_views": row[7] or 0,
            })

        return sorted(scores, key=lambda s: s["composite_score"], reverse=True)

    def _apply_promotions(self, scores: list[dict]) -> dict:
        """Apply promotion/retirement logic."""
        promotions = {"promoted": [], "active": [], "testing": [], "retired": []}

        for score in scores:
            cs = score["composite_score"]
            if cs >= self.PROMOTED_THRESHOLD:
                score["status"] = "promoted"
                promotions["promoted"].append(score["method_tag"])
            elif cs >= self.ACTIVE_THRESHOLD:
                score["status"] = "active"
                promotions["active"].append(score["method_tag"])
            elif cs >= self.TESTING_THRESHOLD:
                score["status"] = "testing"
                promotions["testing"].append(score["method_tag"])
            else:
                score["status"] = "retired"
                promotions["retired"].append(score["method_tag"])

        return promotions

    def _persist_scores(self, scores: list[dict]):
        """Update method_scores table."""
        with self.engine.connect() as conn:
            for score in scores:
                conn.execute(text("""
                    INSERT OR REPLACE INTO method_scores
                    (method_tag, sample_count, avg_completion_rate, avg_share_rate, avg_save_rate,
                     composite_score, status, last_updated)
                    VALUES (:method_tag, :sample_count, :avg_completion, :avg_share, :avg_save,
                            :composite, :status, :updated)
                """), {
                    "method_tag": score["method_tag"],
                    "sample_count": score["sample_count"],
                    "avg_completion": score["avg_completion_rate"],
                    "avg_share": score["avg_share_rate"],
                    "avg_save": score["avg_save_rate"],
                    "composite": score["composite_score"],
                    "status": score.get("status", "testing"),
                    "updated": datetime.now().isoformat(),
                })
            conn.commit()

    def _generate_report(self, scores: list[dict], promotions: dict) -> dict:
        """Generate daily optimization report."""
        return {
            "date": datetime.now().isoformat(),
            "total_methods_scored": len(scores),
            "promotions": promotions,
            "top_3_methods": scores[:3] if scores else [],
            "recommendations": self._generate_recommendations(scores, promotions),
        }

    def _generate_recommendations(self, scores: list[dict], promotions: dict) -> list[str]:
        """Generate actionable recommendations."""
        recs = []
        if promotions["promoted"]:
            recs.append(f"Use {promotions['promoted'][0]} for 70% of next week's content")
        if promotions["retired"]:
            recs.append(f"Stop using: {', '.join(promotions['retired'][:3])}")
        if not scores:
            recs.append("Not enough data yet. Need at least 5 posts per method to score.")
        return recs

    def get_best_method(self) -> Optional[str]:
        """Get the current best-performing method tag."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT method_tag FROM method_scores
                WHERE status IN ('promoted', 'active')
                ORDER BY composite_score DESC LIMIT 1
            """)).fetchone()
        return result[0] if result else None


if __name__ == "__main__":
    optimizer = MethodOptimizer()
    report = optimizer.run_daily_optimization()
    print(json.dumps(report, indent=2))
