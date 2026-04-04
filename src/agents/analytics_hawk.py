"""
Analytics Hawk — Performance Data Collection & Viral Signal Detection.

Monitors published post performance, detects viral signals,
and feeds data to the Method Optimizer for self-tuning.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger("contentops.analytics_hawk")


@dataclass
class PostMetrics:
    post_id: str
    platform: str
    views: int = 0
    watch_time_pct: float = 0.0
    completion_rate: float = 0.0
    shares: int = 0
    saves: int = 0
    comments: int = 0
    likes: int = 0
    follows_gained: int = 0
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AnalyticsHawk:
    """Collects performance metrics and detects viral signals."""

    VIRAL_THRESHOLDS = {
        "rapid_growth": {"views": 10000, "hours": 6},
        "share_spike": {"share_rate": 0.05},
        "save_spike": {"save_rate": 0.03},
    }

    def __init__(self, db_path: str = "data/contentops.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self._ensure_tables()

    def _ensure_tables(self):
        """Create analytics tables if they don't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    external_post_id TEXT,
                    script_id TEXT,
                    method_tag TEXT,
                    hook_type TEXT,
                    published_at TEXT,
                    status TEXT DEFAULT 'published'
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS post_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT REFERENCES posts(id),
                    collected_at TEXT,
                    views INTEGER DEFAULT 0,
                    watch_time_pct REAL DEFAULT 0,
                    completion_rate REAL DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    saves INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    follows_gained INTEGER DEFAULT 0,
                    viral_signal TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS method_scores (
                    method_tag TEXT PRIMARY KEY,
                    sample_count INTEGER DEFAULT 0,
                    avg_completion_rate REAL DEFAULT 0,
                    avg_share_rate REAL DEFAULT 0,
                    avg_save_rate REAL DEFAULT 0,
                    composite_score REAL DEFAULT 0,
                    status TEXT DEFAULT 'testing',
                    last_updated TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS viral_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    signal_type TEXT,
                    detected_at TEXT,
                    views_at_detection INTEGER,
                    action_taken TEXT
                )
            """))
            conn.commit()

    def record_post(self, post_id: str, tenant: str, platform: str, script_id: str,
                    method_tag: str, hook_type: str):
        """Record a new published post for tracking."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO posts (id, tenant_id, platform, script_id, method_tag, hook_type, published_at, status)
                VALUES (:id, :tenant, :platform, :script_id, :method_tag, :hook_type, :published_at, 'published')
            """), {
                "id": post_id, "tenant": tenant, "platform": platform,
                "script_id": script_id, "method_tag": method_tag,
                "hook_type": hook_type, "published_at": datetime.now().isoformat()
            })
            conn.commit()
        logger.info(f"Recorded post: {post_id} ({platform}, {method_tag})")

    def record_metrics(self, metrics: PostMetrics):
        """Record metrics snapshot for a post."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO post_metrics (post_id, collected_at, views, watch_time_pct, completion_rate,
                    shares, saves, comments, likes, follows_gained, viral_signal)
                VALUES (:post_id, :collected_at, :views, :watch_time_pct, :completion_rate,
                    :shares, :saves, :comments, :likes, :follows_gained, :viral_signal)
            """), {
                "post_id": metrics.post_id, "collected_at": metrics.collected_at,
                "views": metrics.views, "watch_time_pct": metrics.watch_time_pct,
                "completion_rate": metrics.completion_rate, "shares": metrics.shares,
                "saves": metrics.saves, "comments": metrics.comments,
                "likes": metrics.likes, "follows_gained": metrics.follows_gained,
                "viral_signal": self._check_viral(metrics),
            })
            conn.commit()

    def _check_viral(self, metrics: PostMetrics) -> Optional[str]:
        """Check if metrics indicate a viral signal."""
        if metrics.views > 0:
            share_rate = metrics.shares / metrics.views
            save_rate = metrics.saves / metrics.views

            if metrics.views >= self.VIRAL_THRESHOLDS["rapid_growth"]["views"]:
                return "rapid_growth"
            if share_rate >= self.VIRAL_THRESHOLDS["share_spike"]["share_rate"]:
                return "share_spike"
            if save_rate >= self.VIRAL_THRESHOLDS["save_spike"]["save_rate"]:
                return "save_spike"
        return None

    def calculate_virality_score(self, metrics: PostMetrics) -> float:
        """Weighted composite virality score (0-10)."""
        if metrics.views == 0:
            return 0.0

        share_rate = metrics.shares / metrics.views
        save_rate = metrics.saves / metrics.views
        comment_rate = metrics.comments / metrics.views
        like_rate = metrics.likes / metrics.views

        score = (
            min(metrics.completion_rate * 10, 10) * 0.30 +
            min(share_rate * 200, 10) * 0.25 +
            min(save_rate * 200, 10) * 0.20 +
            min(comment_rate * 100, 10) * 0.15 +
            min(like_rate * 20, 10) * 0.10
        )
        return round(score, 2)

    def get_analytics_summary(self, tenant: str = None) -> dict:
        """Get analytics summary."""
        with self.engine.connect() as conn:
            total_posts = conn.execute(text("SELECT COUNT(*) FROM posts")).scalar() or 0
            total_metrics = conn.execute(text("SELECT COUNT(*) FROM post_metrics")).scalar() or 0
            viral_count = conn.execute(text("SELECT COUNT(*) FROM viral_signals")).scalar() or 0

            # Top methods
            top_methods = conn.execute(text("""
                SELECT method_tag, composite_score, sample_count, status
                FROM method_scores ORDER BY composite_score DESC LIMIT 5
            """)).fetchall()

        return {
            "total_posts": total_posts,
            "total_metric_snapshots": total_metrics,
            "viral_signals": viral_count,
            "top_methods": [{"method": r[0], "score": r[1], "samples": r[2], "status": r[3]} for r in top_methods],
        }


if __name__ == "__main__":
    hawk = AnalyticsHawk()
    print("Analytics Hawk initialized. Database ready.")
    print(json.dumps(hawk.get_analytics_summary(), indent=2))
