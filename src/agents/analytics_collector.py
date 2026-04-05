"""
Analytics Collector — Scrapes post engagement metrics from platforms.

Currently supports Instagram via instagrapi. Stores metrics in the
existing `post_metrics` table for dashboard display and viral detection.

Designed to run periodically (every 6 hours) for 7 days after posting.
"""
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.analytics_collector")


class AnalyticsCollector:
    """Collect engagement metrics from social platforms and store in DB."""

    # How long to track a post after publishing (days)
    TRACKING_WINDOW_DAYS = 7
    # Viral threshold: if a metric is Nx above the platform average, flag it
    VIRAL_MULTIPLIER = 3.0

    def __init__(self, db_path: str = "data/contentops.db"):
        self.db_path = Path(db_path)
        self._ensure_tables()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _ensure_tables(self):
        """Ensure post_metrics table exists with all needed columns."""
        conn = self._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS post_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
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
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_post_id
                ON post_metrics (post_id)
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Instagram collection via instagrapi
    # ------------------------------------------------------------------

    async def collect_instagram(self, tenant_id: str = "mas-ai") -> list[dict]:
        """Scrape metrics for all Instagram posts within the tracking window."""
        import os

        if not os.environ.get("INSTAGRAM_USERNAME"):
            logger.warning("No Instagram credentials — skipping collection")
            return []

        # Get posts to check (published on Instagram within tracking window)
        conn = self._conn()
        try:
            cutoff = (datetime.now() - timedelta(days=self.TRACKING_WINDOW_DAYS)).isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, external_post_id, published_at
                FROM posts
                WHERE platform = 'instagram'
                  AND tenant_id = ?
                  AND published_at > ?
                  AND external_post_id IS NOT NULL
                  AND external_post_id != ''
                ORDER BY published_at DESC
            """, (tenant_id, cutoff))
            posts_to_check = cursor.fetchall()
        finally:
            conn.close()

        if not posts_to_check:
            logger.info("No recent Instagram posts to collect metrics for")
            return []

        # Login to Instagram
        try:
            from src.agents.instagram_publisher import InstagramPublisher
            pub = InstagramPublisher()
            if not pub.login():
                logger.error("Instagram login failed — cannot collect metrics")
                return []
        except ImportError:
            logger.error("instagrapi not installed")
            return []

        results = []
        for post_id, media_id, published_at in posts_to_check:
            try:
                # instagrapi media_info returns full engagement data
                media_info = pub._client.media_info(media_id)
                metrics = {
                    "post_id": post_id,
                    "views": getattr(media_info, "view_count", 0) or 0,
                    "likes": getattr(media_info, "like_count", 0) or 0,
                    "comments": getattr(media_info, "comment_count", 0) or 0,
                    # Play count for reels
                    "plays": getattr(media_info, "play_count", 0) or 0,
                }

                # Detect viral signals
                viral = self._detect_viral(metrics)
                self._store_metrics(post_id, metrics, viral)
                metrics["viral_signal"] = viral
                results.append(metrics)

                logger.info(
                    "Collected IG metrics for %s: %d views, %d likes, %d comments",
                    post_id, metrics["views"], metrics["likes"], metrics["comments"],
                )

                # Human-like delay between API calls
                import time, random
                time.sleep(random.uniform(1.5, 3.0))

            except Exception as e:
                logger.error("Failed to collect metrics for %s: %s", post_id, e)
                results.append({"post_id": post_id, "error": str(e)})

        return results

    # ------------------------------------------------------------------
    # Metric storage
    # ------------------------------------------------------------------

    def _store_metrics(self, post_id: str, metrics: dict, viral_signal: Optional[str]):
        """Store a metrics snapshot in post_metrics table."""
        conn = self._conn()
        try:
            conn.execute("""
                INSERT INTO post_metrics (
                    post_id, collected_at, views, likes, comments,
                    shares, saves, viral_signal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                datetime.now().isoformat(),
                metrics.get("views", 0),
                metrics.get("likes", 0),
                metrics.get("comments", 0),
                metrics.get("shares", 0),
                metrics.get("saves", 0),
                viral_signal,
            ))
            conn.commit()
        finally:
            conn.close()

    def _detect_viral(self, metrics: dict) -> Optional[str]:
        """Check if metrics indicate viral performance."""
        # Get platform averages
        averages = self._get_platform_averages("instagram")
        if not averages or averages.get("avg_views", 0) == 0:
            return None

        signals = []
        if metrics.get("views", 0) > averages["avg_views"] * self.VIRAL_MULTIPLIER:
            signals.append("view_spike")
        if metrics.get("likes", 0) > averages["avg_likes"] * self.VIRAL_MULTIPLIER:
            signals.append("like_spike")
        if metrics.get("comments", 0) > averages["avg_comments"] * self.VIRAL_MULTIPLIER:
            signals.append("comment_spike")

        return ",".join(signals) if signals else None

    def _get_platform_averages(self, platform: str) -> dict:
        """Get average metrics across all posts on a platform."""
        conn = self._conn()
        try:
            cursor = conn.cursor()
            # Get latest metrics snapshot per post, then average
            cursor.execute("""
                SELECT
                    AVG(m.views) as avg_views,
                    AVG(m.likes) as avg_likes,
                    AVG(m.comments) as avg_comments
                FROM post_metrics m
                INNER JOIN (
                    SELECT post_id, MAX(collected_at) as latest
                    FROM post_metrics
                    GROUP BY post_id
                ) latest_m ON m.post_id = latest_m.post_id AND m.collected_at = latest_m.latest
                INNER JOIN posts p ON m.post_id = p.id
                WHERE p.platform = ?
            """, (platform,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return {
                    "avg_views": row[0],
                    "avg_likes": row[1],
                    "avg_comments": row[2],
                }
            return {}
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Collection orchestration
    # ------------------------------------------------------------------

    async def collect_all(self, tenant_id: str = "mas-ai") -> dict:
        """Collect metrics from all connected platforms."""
        results = {"instagram": [], "timestamp": datetime.now().isoformat()}

        ig_results = await self.collect_instagram(tenant_id)
        results["instagram"] = ig_results
        results["total_collected"] = len(ig_results)

        return results

    # ------------------------------------------------------------------
    # Dashboard queries
    # ------------------------------------------------------------------

    def get_posts_with_metrics(
        self,
        limit: int = 20,
        platform: Optional[str] = None,
    ) -> dict:
        """Get posts joined with their latest metrics for dashboard display."""
        conn = self._conn()
        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    p.id, p.platform, p.published_at, p.caption, p.url,
                    p.thumbnail_path, p.method_tag, p.hook_type, p.status,
                    COALESCE(m.views, 0) as views,
                    COALESCE(m.likes, 0) as likes,
                    COALESCE(m.comments, 0) as comments,
                    COALESCE(m.shares, 0) as shares,
                    COALESCE(m.saves, 0) as saves,
                    m.viral_signal,
                    m.collected_at as metrics_updated
                FROM posts p
                LEFT JOIN (
                    SELECT post_id, views, likes, comments, shares, saves,
                           viral_signal, collected_at,
                           ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY collected_at DESC) as rn
                    FROM post_metrics
                ) m ON p.id = m.post_id AND m.rn = 1
                WHERE 1=1
            """
            params = []
            if platform:
                query += " AND p.platform = ?"
                params.append(platform)
            query += " ORDER BY p.published_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            columns = [
                "id", "platform", "published_at", "caption", "url",
                "thumbnail_path", "method_tag", "hook_type", "status",
                "views", "likes", "comments", "shares", "saves",
                "viral_signal", "metrics_updated",
            ]
            posts = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Calculate summary
            total_views = sum(p.get("views", 0) or 0 for p in posts)
            total_likes = sum(p.get("likes", 0) or 0 for p in posts)
            viral_count = sum(1 for p in posts if p.get("viral_signal"))

            return {
                "posts": posts,
                "summary": {
                    "total_posts": len(posts),
                    "total_views": total_views,
                    "total_likes": total_likes,
                    "viral_posts": viral_count,
                    "avg_views": round(total_views / len(posts), 1) if posts else 0,
                    "avg_likes": round(total_likes / len(posts), 1) if posts else 0,
                },
            }
        finally:
            conn.close()
