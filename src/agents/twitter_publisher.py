"""
X/Twitter Publisher — Post videos using tweepy (API v1.1 media + v2 tweet).

Uses Twitter API v1.1 for chunked media upload (videos) and v2 for tweet creation.
Requires a Twitter Developer App with OAuth 1.0a credentials.

Env vars required:
  TWITTER_API_KEY          — Consumer key
  TWITTER_API_SECRET       — Consumer secret
  TWITTER_ACCESS_TOKEN     — User access token
  TWITTER_ACCESS_SECRET    — User access token secret

Note: X/Twitter videos should be 16:9 or 1:1 (not 9:16 portrait).
Max duration: 2:20 (140 seconds). Max file size: 512MB.
"""
import json
import logging
import os
import random
import time
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.twitter")

# Lazy import
_tweepy = None


def _get_tweepy():
    global _tweepy
    if _tweepy is None:
        import tweepy
        _tweepy = tweepy
    return _tweepy


class TwitterPublisher:
    """Publish videos and tweets to X/Twitter via API."""

    MAX_DAILY_POSTS = 10
    MAX_VIDEO_SIZE_MB = 512
    MAX_VIDEO_DURATION_S = 140
    DELAY_RANGE = (5, 15)

    def __init__(self):
        self.api_key = os.environ.get("TWITTER_API_KEY", "")
        self.api_secret = os.environ.get("TWITTER_API_SECRET", "")
        self.access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")
        self.daily_log_file = Path("config/twitter_daily_posts.json")
        self.daily_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._api_v1 = None
        self._client_v2 = None

    def is_configured(self) -> bool:
        return all([self.api_key, self.api_secret, self.access_token, self.access_secret])

    def _get_api_v1(self):
        """Get tweepy v1.1 API (needed for media upload)."""
        if self._api_v1 is None:
            tweepy = _get_tweepy()
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret,
            )
            self._api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        return self._api_v1

    def _get_client_v2(self):
        """Get tweepy v2 Client (for tweet creation)."""
        if self._client_v2 is None:
            tweepy = _get_tweepy()
            self._client_v2 = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret,
            )
        return self._client_v2

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

    # ── Publishing ──────────────────────────────────────────────────

    def publish_video(
        self,
        video_path: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> dict:
        """
        Upload video to X/Twitter and create a tweet.

        Args:
            video_path: Path to MP4 (16:9 or 1:1 recommended, max 140s)
            caption: Tweet text (max 280 chars)
            hashtags: Optional hashtags appended to caption

        Returns:
            dict with status, tweet_id, url
        """
        if not self.is_configured():
            return {
                "status": "failed",
                "error": "Twitter credentials not configured. Set TWITTER_API_KEY, "
                         "TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET in .env",
            }

        if not Path(video_path).exists():
            return {"status": "failed", "error": f"Video not found: {video_path}"}

        if not self._check_daily_limit():
            return {"status": "rate_limited", "error": f"Daily limit reached ({self.MAX_DAILY_POSTS})"}

        # Build tweet text (max 280 chars)
        text = caption
        if hashtags:
            tags = " ".join(f"#{t.lstrip('#')}" for t in hashtags[:2])
            text = f"{caption}\n\n{tags}"
        text = text[:280]

        try:
            api = self._get_api_v1()
            client = self._get_client_v2()

            # Step 1: Chunked media upload via v1.1
            time.sleep(random.uniform(*self.DELAY_RANGE))
            media = api.chunked_upload(
                video_path,
                media_category="tweet_video",
                wait_for_async_finalize=True,
            )
            logger.info("Twitter media uploaded: media_id=%s", media.media_id)

            # Step 2: Create tweet with media via v2
            time.sleep(random.uniform(2, 5))
            response = client.create_tweet(
                text=text,
                media_ids=[media.media_id],
            )
            tweet_id = response.data["id"]

            self._increment_daily_count()

            # Construct tweet URL (need username)
            try:
                me = client.get_me()
                username = me.data.username
                url = f"https://x.com/{username}/status/{tweet_id}"
            except Exception:
                url = f"https://x.com/i/status/{tweet_id}"

            logger.info("Tweet published: %s", url)

            return {
                "status": "published",
                "platform": "twitter",
                "tweet_id": tweet_id,
                "media_id": str(media.media_id),
                "url": url,
            }

        except Exception as e:
            logger.error("Twitter publish failed: %s", e)
            return {"status": "failed", "error": str(e)}
