"""
Content Tracker — Deduplication, Post History, and Render Cleanup.

Tracks all published content with media/caption hashes to prevent
duplicate posts. Provides history queries for the dashboard and
auto-cleans old rendered files to free disk space.

Uses the existing contentops.db — extends the `posts` table with
hash columns added via migration on first run.
"""
import hashlib
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.content_tracker")


class ContentTracker:
    """Track published content, detect duplicates, manage render lifecycle."""

    def __init__(self, db_path: str = "data/contentops.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    # ------------------------------------------------------------------
    # Schema migration
    # ------------------------------------------------------------------

    def _migrate(self):
        """Add tracking columns to existing posts table if missing."""
        conn = self._conn()
        try:
            cursor = conn.cursor()
            # Check which columns already exist
            cursor.execute("PRAGMA table_info(posts)")
            existing = {row[1] for row in cursor.fetchall()}

            migrations = {
                "content_hash": "TEXT",
                "caption_hash": "TEXT",
                "caption": "TEXT",
                "video_path": "TEXT",
                "url": "TEXT",
                "thumbnail_path": "TEXT",
            }

            for col, dtype in migrations.items():
                if col not in existing:
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {col} {dtype}")
                    logger.info("Migrated posts table: added column %s", col)

            # Index for fast dedup lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_content_hash
                ON posts (content_hash, platform)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_caption_hash
                ON posts (caption_hash, platform)
            """)
            conn.commit()
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_file(file_path: str) -> str:
        """SHA-256 hash of a file's contents. Fast enough for video files."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        """SHA-256 hash of text (caption, script, etc.)."""
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def has_been_posted(self, video_path: str, platform: str) -> bool:
        """Check if this exact video file has already been posted to a platform."""
        content_hash = self.hash_file(video_path)
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM posts WHERE content_hash = ? AND platform = ? LIMIT 1",
                (content_hash, platform),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def caption_already_used(self, caption: str, platform: str) -> bool:
        """Check if this exact caption has been used on a platform."""
        caption_hash = self.hash_text(caption)
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM posts WHERE caption_hash = ? AND platform = ? LIMIT 1",
                (caption_hash, platform),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_post(
        self,
        post_id: str,
        video_path: str,
        caption: str,
        platform: str,
        url: Optional[str] = None,
        tenant_id: str = "mas-ai",
        script_id: Optional[str] = None,
        method_tag: Optional[str] = None,
        hook_type: Optional[str] = None,
        external_post_id: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
    ) -> dict:
        """Record a published post with content hashes for dedup."""
        content_hash = self.hash_file(video_path) if os.path.exists(video_path) else None
        caption_hash = self.hash_text(caption) if caption else None

        conn = self._conn()
        try:
            cursor = conn.cursor()
            # Upsert — update if post_id already exists (re-publish scenario)
            cursor.execute("""
                INSERT INTO posts (
                    id, tenant_id, platform, external_post_id, script_id,
                    method_tag, hook_type, published_at, status,
                    content_hash, caption_hash, caption, video_path, url, thumbnail_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    caption_hash = excluded.caption_hash,
                    caption = excluded.caption,
                    video_path = excluded.video_path,
                    url = excluded.url,
                    thumbnail_path = excluded.thumbnail_path,
                    status = 'published'
            """, (
                post_id, tenant_id, platform, external_post_id, script_id,
                method_tag, hook_type, datetime.now().isoformat(),
                content_hash, caption_hash, caption, str(video_path), url, thumbnail_path,
            ))
            conn.commit()
            logger.info("Recorded post %s on %s (hash=%s)", post_id, platform, content_hash[:12] if content_hash else "none")
            return {
                "post_id": post_id,
                "platform": platform,
                "content_hash": content_hash,
                "url": url,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # History queries
    # ------------------------------------------------------------------

    def get_post_history(
        self,
        limit: int = 50,
        platform: Optional[str] = None,
        tenant_id: str = "mas-ai",
    ) -> list[dict]:
        """Get recent post history for dashboard display."""
        conn = self._conn()
        try:
            cursor = conn.cursor()
            query = """
                SELECT id, platform, published_at, caption, video_path, url,
                       thumbnail_path, method_tag, hook_type, status, external_post_id
                FROM posts
                WHERE tenant_id = ?
            """
            params: list = [tenant_id]
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            query += " ORDER BY published_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            columns = [
                "id", "platform", "published_at", "caption", "video_path",
                "url", "thumbnail_path", "method_tag", "hook_type", "status",
                "external_post_id",
            ]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_post_count(self, platform: Optional[str] = None) -> int:
        """Total post count, optionally filtered by platform."""
        conn = self._conn()
        try:
            cursor = conn.cursor()
            if platform:
                cursor.execute("SELECT COUNT(*) FROM posts WHERE platform = ?", (platform,))
            else:
                cursor.execute("SELECT COUNT(*) FROM posts")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Render cleanup
    # ------------------------------------------------------------------

    def cleanup_old_renders(self, days: int = 3, render_dirs: Optional[list[str]] = None) -> dict:
        """Delete rendered video files older than `days` days.

        Returns summary of what was cleaned.
        """
        if render_dirs is None:
            render_dirs = ["out", "data/videos", "data/outputs"]

        cutoff = time.time() - (days * 86400)
        cleaned = {"files_deleted": 0, "bytes_freed": 0, "errors": []}

        for dir_path in render_dirs:
            p = Path(dir_path)
            if not p.exists():
                continue
            for f in p.rglob("*"):
                if not f.is_file():
                    continue
                # Only clean video/image renders
                if f.suffix.lower() not in (".mp4", ".webm", ".mov", ".png", ".jpg", ".jpeg", ".gif"):
                    continue
                try:
                    if f.stat().st_mtime < cutoff:
                        size = f.stat().st_size
                        f.unlink()
                        cleaned["files_deleted"] += 1
                        cleaned["bytes_freed"] += size
                        logger.info("Cleaned old render: %s (%d bytes)", f, size)
                except OSError as e:
                    cleaned["errors"].append(f"{f}: {e}")

        cleaned["bytes_freed_mb"] = round(cleaned["bytes_freed"] / (1024 * 1024), 2)
        logger.info(
            "Cleanup complete: %d files, %.2f MB freed",
            cleaned["files_deleted"],
            cleaned["bytes_freed_mb"],
        )
        return cleaned
