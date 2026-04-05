"""
LinkedIn Publisher — Post text, images, and video via linkedin-api.

Supports both personal profiles and company pages.
Uses username/password auth with session persistence.

Env vars:
  LINKEDIN_MASOUD_EMAIL / LINKEDIN_MASOUD_PASSWORD — personal profile
  LINKEDIN_MASAI_EMAIL / LINKEDIN_MASAI_PASSWORD   — company admin account
"""
import json
import logging
import os
import random
import time
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.linkedin")

_Linkedin = None

def _get_linkedin_class():
    global _Linkedin
    if _Linkedin is None:
        from linkedin_api import Linkedin
        _Linkedin = Linkedin
    return _Linkedin


class LinkedInPublisher:
    """Publish posts to LinkedIn personal profiles and company pages."""

    MAX_DAILY_POSTS = 5
    DELAY_RANGE = (5, 15)

    def __init__(self, account_id: str = "masoud"):
        """
        Args:
            account_id: "masoud" for personal, "masai" for company
        """
        self.account_id = account_id
        prefix = f"LINKEDIN_{account_id.upper()}"
        self.email = os.environ.get(f"{prefix}_EMAIL", "")
        self.password = os.environ.get(f"{prefix}_PASSWORD", "")
        self.daily_log_file = Path(f"config/linkedin_{account_id}_daily.json")
        self.daily_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.email and self.password)

    def _get_client(self):
        if self._client is None:
            if not self.is_configured():
                raise ValueError(f"LinkedIn credentials not configured for {self.account_id}")
            LinkedinClass = _get_linkedin_class()
            self._client = LinkedinClass(self.email, self.password)
            logger.info("LinkedIn login successful for %s", self.email)
        return self._client

    def _check_daily_limit(self) -> bool:
        today = date.today().isoformat()
        log = self._load_daily_log()
        return log.get(today, 0) < self.MAX_DAILY_POSTS

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

    def publish_text_post(
        self,
        text: str,
        visibility: str = "PUBLIC",
    ) -> dict:
        """Post a text update to LinkedIn."""
        if not self.is_configured():
            return {"status": "failed", "error": f"LinkedIn {self.account_id} credentials not set"}

        if not self._check_daily_limit():
            return {"status": "rate_limited", "error": "Daily limit reached"}

        try:
            client = self._get_client()
            self._human_delay()

            result = client.post(text)
            self._increment_daily_count()

            logger.info("LinkedIn text post published for %s", self.account_id)
            return {
                "status": "published",
                "platform": "linkedin",
                "account": self.account_id,
                "post_type": "text",
            }
        except Exception as e:
            logger.error("LinkedIn post failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def publish_image_post(
        self,
        text: str,
        image_path: str,
        title: str = "",
    ) -> dict:
        """Post with an image attachment."""
        if not self.is_configured():
            return {"status": "failed", "error": f"LinkedIn {self.account_id} credentials not set"}

        if not Path(image_path).exists():
            return {"status": "failed", "error": f"Image not found: {image_path}"}

        if not self._check_daily_limit():
            return {"status": "rate_limited", "error": "Daily limit reached"}

        try:
            client = self._get_client()
            self._human_delay()

            result = client.post(text, media=image_path, title=title)
            self._increment_daily_count()

            logger.info("LinkedIn image post published for %s", self.account_id)
            return {
                "status": "published",
                "platform": "linkedin",
                "account": self.account_id,
                "post_type": "image",
            }
        except Exception as e:
            logger.error("LinkedIn image post failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def publish_video_post(
        self,
        text: str,
        video_path: str,
        title: str = "",
    ) -> dict:
        """Post with a video attachment (16:9 recommended for LinkedIn)."""
        if not self.is_configured():
            return {"status": "failed", "error": f"LinkedIn {self.account_id} credentials not set"}

        if not Path(video_path).exists():
            return {"status": "failed", "error": f"Video not found: {video_path}"}

        if not self._check_daily_limit():
            return {"status": "rate_limited", "error": "Daily limit reached"}

        try:
            client = self._get_client()
            self._human_delay()

            # linkedin-api supports video upload via post()
            result = client.post(text, media=video_path, title=title)
            self._increment_daily_count()

            logger.info("LinkedIn video post published for %s", self.account_id)
            return {
                "status": "published",
                "platform": "linkedin",
                "account": self.account_id,
                "post_type": "video",
            }
        except Exception as e:
            logger.error("LinkedIn video post failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_profile(self) -> dict:
        """Get the logged-in user's profile info."""
        try:
            client = self._get_client()
            profile = client.get_profile(public_id="me")
            return {
                "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}",
                "headline": profile.get("headline", ""),
                "url": f"https://www.linkedin.com/in/{profile.get('public_id', '')}",
            }
        except Exception as e:
            return {"error": str(e)}
