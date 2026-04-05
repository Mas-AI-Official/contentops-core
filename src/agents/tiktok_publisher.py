"""
TikTok Publisher — Direct posting via tiktok-uploader (Playwright).

Bypasses TikTok Developer Portal entirely. Uses exported browser cookies
to authenticate through TikTok's web interface via Playwright automation.

Setup:
  1. Login to TikTok in Chrome
  2. Install "Get cookies.txt" browser extension
  3. Export cookies to config/tiktok_cookies.txt
  4. Set TIKTOK_COOKIES_PATH in .env (default: config/tiktok_cookies.txt)

Anti-block safety measures:
  - Cookie-based auth (no repeated logins)
  - Human-like delays between uploads (30-60s)
  - Max 5 posts per day enforced
  - Headless mode configurable
"""
import json
import logging
import os
import random
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.tiktok")

# Lazy import — only load when publishing
_TikTokUploader = None


def _get_uploader_class():
    global _TikTokUploader
    if _TikTokUploader is None:
        from tiktok_uploader.upload import TikTokUploader
        _TikTokUploader = TikTokUploader
    return _TikTokUploader


class TikTokPublisher:
    """Publish videos to TikTok via browser cookie authentication."""

    MAX_DAILY_POSTS = 5
    DELAY_RANGE = (30, 60)  # TikTok is stricter than Instagram

    def __init__(self, cookies_path: str = ""):
        self.cookies_path = Path(
            cookies_path
            or os.environ.get("TIKTOK_COOKIES_PATH", "config/tiktok_cookies.txt")
        )
        self.daily_log_file = Path("config/tiktok_daily_posts.json")
        self.daily_log_file.parent.mkdir(parents=True, exist_ok=True)

    # ── Validation ──────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """Check if TikTok cookies are available."""
        return self.cookies_path.exists()

    def _check_daily_limit(self) -> bool:
        """Enforce daily post limit. Returns True if under limit."""
        today = date.today().isoformat()
        log = self._load_daily_log()
        count = log.get(today, 0)
        if count >= self.MAX_DAILY_POSTS:
            logger.warning("TikTok daily limit reached: %d/%d", count, self.MAX_DAILY_POSTS)
            return False
        return True

    def _increment_daily_count(self):
        today = date.today().isoformat()
        log = self._load_daily_log()
        log[today] = log.get(today, 0) + 1
        self.daily_log_file.write_text(json.dumps(log, indent=2))

    def _load_daily_log(self) -> dict:
        if self.daily_log_file.exists():
            try:
                return json.loads(self.daily_log_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _human_delay(self):
        delay = random.uniform(*self.DELAY_RANGE)
        logger.info("Human-like delay: %.1fs", delay)
        time.sleep(delay)

    # ── Publishing ──────────────────────────────────────────────────

    def publish_video(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
        schedule: Optional[datetime] = None,
        cover_path: Optional[str] = None,
        headless: bool = True,
    ) -> dict:
        """
        Upload a video to TikTok.

        Args:
            video_path: Path to MP4 file (9:16 aspect, max 10min)
            caption: Video description
            hashtags: List of hashtags (will be appended to caption)
            schedule: Optional future datetime (min 20min, max 10 days)
            cover_path: Optional thumbnail image path
            headless: Run browser in headless mode

        Returns:
            dict with status, error (if any)
        """
        if not self.is_configured():
            return {
                "status": "failed",
                "error": f"TikTok cookies not found at {self.cookies_path}. "
                         "Export cookies from Chrome using 'Get cookies.txt' extension.",
            }

        if not Path(video_path).exists():
            return {"status": "failed", "error": f"Video file not found: {video_path}"}

        if not self._check_daily_limit():
            return {
                "status": "rate_limited",
                "error": f"Daily TikTok post limit reached ({self.MAX_DAILY_POSTS}/day)",
            }

        # Build description with hashtags
        full_caption = caption
        if hashtags:
            tags = " ".join(f"#{t.lstrip('#')}" for t in hashtags[:5])
            full_caption = f"{caption}\n\n{tags}"

        # Validate schedule if provided
        if schedule:
            min_schedule = datetime.now() + timedelta(minutes=20)
            max_schedule = datetime.now() + timedelta(days=10)
            if schedule < min_schedule:
                logger.warning("Schedule too soon, posting immediately instead")
                schedule = None
            elif schedule > max_schedule:
                logger.warning("Schedule too far out (max 10 days), clamping")
                schedule = max_schedule

        try:
            UploaderClass = _get_uploader_class()
            uploader = UploaderClass(
                cookies=str(self.cookies_path),
                headless=headless,
            )

            self._human_delay()

            uploader.upload_video(
                str(video_path),
                description=full_caption,
                schedule=schedule,
                cover=cover_path,
                comment=True,
                stitch=True,
                duet=True,
            )

            self._increment_daily_count()

            status = "scheduled" if schedule else "published"
            logger.info(
                "TikTok upload %s: %s (caption: %s...)",
                status, video_path, caption[:50],
            )

            return {
                "status": status,
                "platform": "tiktok",
                "video_path": video_path,
                "caption": caption,
                "scheduled_time": schedule.isoformat() if schedule else None,
            }

        except Exception as e:
            logger.error("TikTok upload failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def publish_videos(
        self,
        videos: list[dict],
        headless: bool = True,
    ) -> list[dict]:
        """
        Batch upload multiple videos.

        Args:
            videos: List of dicts with keys: path, caption, hashtags (optional), schedule (optional)
            headless: Run browser in headless mode

        Returns:
            List of result dicts
        """
        results = []
        for video in videos:
            if not self._check_daily_limit():
                results.append({
                    "status": "rate_limited",
                    "video_path": video.get("path", ""),
                    "error": "Daily limit reached",
                })
                break

            result = self.publish_video(
                video_path=video["path"],
                caption=video.get("caption", ""),
                hashtags=video.get("hashtags"),
                schedule=video.get("schedule"),
                headless=headless,
            )
            results.append(result)

            # Extra delay between batch uploads
            if len(videos) > 1:
                time.sleep(random.uniform(60, 120))

        return results
