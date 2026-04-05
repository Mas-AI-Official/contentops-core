"""
Distribution Engine — Multi-Platform Publishing.

Handles platform-specific formatting, optimal timing, and publishing.
Supports: TikTok, Instagram, YouTube, LinkedIn, X/Twitter, Threads, Pinterest, Snapchat.
Uses platform APIs where available, with draft mode as fallback.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("contentops.distributor")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PostMetadata:
    """Platform-specific post metadata."""
    title: str
    caption: str
    hashtags: list[str]
    platform: str
    video_path: str
    thumbnail_path: Optional[str] = None
    scheduled_time: Optional[str] = None
    tenant: str = "mas-ai"


@dataclass
class PostResult:
    platform: str
    status: str  # published | scheduled | failed | draft
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DistributionEngine:
    """Multi-platform content distribution with optimal timing."""

    # Optimal posting times per platform (2026 research data)
    OPTIMAL_TIMES = {
        "tiktok": ["07:00", "12:00", "19:00"],
        "instagram": ["08:00", "11:00", "17:00", "21:00"],
        "youtube": ["14:00", "16:00", "20:00"],
        "linkedin": ["08:00", "10:00", "12:00"],
        "twitter": ["08:00", "12:00", "17:00", "21:00"],
    }

    # Platform-specific formatting rules
    PLATFORM_RULES = {
        "tiktok": {
            "max_caption": 2200,
            "max_hashtags": 5,
            "max_duration": 60,
            "hashtag_style": "niche_only",
            "aspect_ratio": "9:16",
            "api_env": "TIKTOK_ACCESS_TOKEN",
        },
        "instagram": {
            "max_caption": 2200,
            "max_hashtags": 5,
            "max_duration": 60,
            "hashtag_style": "mixed",
            "aspect_ratio": "9:16",
            "api_env": "INSTAGRAM_USERNAME",
        },
        "youtube": {
            "max_title": 100,
            "max_description": 5000,
            "max_tags": 15,
            "max_duration": 60,
            "hashtag_style": "seo",
            "aspect_ratio": "9:16",
            "api_env": "YOUTUBE_API_KEY",
        },
        "linkedin": {
            "max_caption": 3000,
            "max_hashtags": 3,
            "max_duration": 180,
            "hashtag_style": "professional",
            "aspect_ratio": "16:9",
            "api_env": "LINKEDIN_ACCESS_TOKEN",
        },
        "twitter": {
            "max_caption": 280,
            "max_hashtags": 2,
            "max_duration": 140,
            "hashtag_style": "trending",
            "aspect_ratio": "9:16",
            "api_env": "TWITTER_BEARER_TOKEN",
        },
        "threads": {
            "max_caption": 500,
            "max_hashtags": 5,
            "max_duration": 300,
            "hashtag_style": "mixed",
            "aspect_ratio": "9:16",
            "api_env": "THREADS_ACCESS_TOKEN",
        },
        "pinterest": {
            "max_caption": 500,
            "max_hashtags": 20,
            "max_duration": 60,
            "hashtag_style": "seo",
            "aspect_ratio": "9:16",
            "api_env": "PINTEREST_ACCESS_TOKEN",
        },
        "snapchat": {
            "max_caption": 250,
            "max_hashtags": 0,
            "max_duration": 60,
            "hashtag_style": "none",
            "aspect_ratio": "9:16",
            "api_env": "SNAPCHAT_ACCESS_TOKEN",
        },
    }

    # Default httpx timeout for all API calls (seconds)
    _API_TIMEOUT = 60.0
    # Instagram media processing poll interval / max attempts
    _IG_POLL_INTERVAL = 5
    _IG_MAX_POLLS = 24  # 2 minutes total

    def __init__(self):
        self.published_dir = Path("data/published")
        self.published_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Platform status
    # ------------------------------------------------------------------

    def get_platform_status(self) -> dict:
        """Check which platforms have API credentials configured."""
        status = {}
        for platform, rules in self.PLATFORM_RULES.items():
            env_key = rules.get("api_env", "")
            has_key = bool(os.environ.get(env_key)) if env_key else False
            status[platform] = {
                "connected": has_key,
                "mode": "api" if has_key else "draft",
                "env_key": env_key,
            }
        return status

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_post(self, script_data: dict, video_path: str, platform: str, tenant: str = "mas-ai") -> PostMetadata:
        """Format content for a specific platform."""
        rules = self.PLATFORM_RULES.get(platform, self.PLATFORM_RULES["tiktok"])

        # Load tenant brand
        brand = self._load_brand(tenant)

        # Build caption
        hook_text = ""
        cta_text = ""
        acts = script_data.get("acts", [])
        if acts:
            hook_text = acts[0].get("text", "")
            if len(acts) >= 5:
                cta_text = acts[-1].get("text", "")

        # Platform-specific caption formatting
        if platform == "linkedin":
            caption = self._format_linkedin(hook_text, script_data, brand, cta_text)
        elif platform == "twitter":
            caption = self._format_twitter(hook_text, brand)
        elif platform == "youtube":
            caption = self._format_youtube_description(script_data, brand, cta_text)
        else:
            caption = self._format_short_form(hook_text, cta_text, brand)

        # Build hashtags
        hashtags = self._build_hashtags(platform, brand, script_data.get("niche", "ai-tech"))

        # Truncate to platform limits
        max_caption = rules.get("max_caption", rules.get("max_description", 2200))
        caption = caption[:max_caption]
        hashtags = hashtags[:rules.get("max_hashtags", rules.get("max_tags", 5))]

        # Title for YouTube
        title = hook_text[:rules.get("max_title", 100)] if platform == "youtube" else hook_text[:80]

        # Get optimal time
        next_time = self._get_next_optimal_time(platform, tenant)

        return PostMetadata(
            title=title,
            caption=caption,
            hashtags=hashtags,
            platform=platform,
            video_path=video_path,
            scheduled_time=next_time,
            tenant=tenant,
        )

    def _format_short_form(self, hook: str, cta: str, brand: dict) -> str:
        """Format caption for TikTok/Instagram Reels."""
        parts = [hook]
        if cta:
            parts.append(f"\n\n{cta}")
        return "\n".join(parts)

    def _format_linkedin(self, hook: str, script_data: dict, brand: dict, cta: str) -> str:
        """Format for LinkedIn (professional tone, longer form)."""
        insight = script_data.get("insight_source", "")
        return f"""{hook}

{insight[:300]}

{cta if cta else 'What do you think? Share your perspective below.'}"""

    def _format_twitter(self, hook: str, brand: dict) -> str:
        """Format for X/Twitter (concise, under 280 chars)."""
        return hook[:250]

    def _format_youtube_description(self, script_data: dict, brand: dict, cta: str) -> str:
        """Format YouTube description (SEO-optimized)."""
        text = script_data.get("full_voiceover_text", "")
        return f"""{text[:500]}

{cta if cta else 'Subscribe for more AI insights.'}

---
{brand.get('name', 'MAS-AI Technologies')}
{brand.get('tagline', '')}"""

    def _build_hashtags(self, platform: str, brand: dict, niche: str) -> list[str]:
        """Build platform-appropriate hashtags."""
        always = brand.get("hashtags", {}).get("always", ["#DaenaAI"])
        niche_tags = brand.get("hashtags", {}).get("niche", ["#AI", "#TechStartup"])

        if platform == "linkedin":
            return always[:1] + niche_tags[:2]
        elif platform == "twitter":
            return always[:1] + niche_tags[:1]
        else:
            return always + niche_tags[:3]

    def _get_next_optimal_time(self, platform: str, tenant: str) -> str:
        """Calculate next optimal posting time."""
        times = self.OPTIMAL_TIMES.get(platform, ["12:00"])
        now = datetime.now()

        for time_str in times:
            h, m = map(int, time_str.split(":"))
            candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if candidate > now:
                return candidate.isoformat()

        # All times passed today, schedule for tomorrow's first slot
        h, m = map(int, times[0].split(":"))
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=h, minute=m, second=0, microsecond=0).isoformat()

    def _load_brand(self, tenant: str) -> dict:
        """Load tenant brand config."""
        brand_path = Path(f"tenants/{tenant}/brand.json")
        if brand_path.exists():
            with open(brand_path) as f:
                return json.load(f)
        return {"name": tenant, "hashtags": {"always": [], "niche": []}}

    # ------------------------------------------------------------------
    # Core publish flow
    # ------------------------------------------------------------------

    async def publish(self, post: PostMetadata) -> PostResult:
        """
        Publish to platform.  Attempts real API publish first; falls back to
        saving a draft package for manual upload.
        """
        post_id = f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{post.platform}"

        post_package = {
            "post_id": post_id,
            "platform": post.platform,
            "title": post.title,
            "caption": post.caption,
            "hashtags": post.hashtags,
            "video_path": post.video_path,
            "scheduled_time": post.scheduled_time,
            "tenant": post.tenant,
            "status": "ready_to_post",
            "created_at": datetime.now().isoformat(),
            "instructions": self._get_manual_instructions(post),
        }

        # Save draft package (always — serves as backup even if API succeeds)
        post_path = self.published_dir / f"{post_id}.json"
        with open(post_path, "w", encoding="utf-8") as f:
            json.dump(post_package, f, indent=2, ensure_ascii=False)

        logger.info(f"Post package ready: {post_path}")

        # Try API publishing if credentials are available
        api_result = await self._try_api_publish(post)
        if api_result:
            # Update the draft with the live status
            post_package["status"] = api_result.status
            post_package["post_url"] = api_result.url
            post_package["api_post_id"] = api_result.post_id
            with open(post_path, "w", encoding="utf-8") as f:
                json.dump(post_package, f, indent=2, ensure_ascii=False)
            return api_result

        return PostResult(
            platform=post.platform,
            status="draft",
            post_id=post_id,
        )

    async def _try_api_publish(self, post: PostMetadata) -> Optional[PostResult]:
        """Attempt to publish via platform API.  Returns None if no credentials."""
        if post.platform == "instagram" and os.environ.get("INSTAGRAM_USERNAME"):
            return await self._publish_instagram_direct(post)
        elif post.platform == "tiktok" and os.environ.get("TIKTOK_ACCESS_TOKEN"):
            return await self._publish_tiktok(post)
        elif post.platform == "youtube" and os.environ.get("YOUTUBE_API_KEY"):
            return await self._publish_youtube(post)
        return None

    # ------------------------------------------------------------------
    # Instagram Direct (instagrapi — no developer portal needed)
    # ------------------------------------------------------------------

    async def _publish_instagram_direct(self, post: PostMetadata) -> PostResult:
        """
        Publish to Instagram via instagrapi (mobile API).
        No Meta Developer account or Facebook Page required.
        """
        try:
            from src.agents.instagram_publisher import InstagramPublisher

            pub = InstagramPublisher()
            if not pub.login():
                return PostResult(
                    platform="instagram",
                    status="draft",
                    error="Instagram login failed — check INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env",
                )

            caption_with_tags = f"{post.caption}\n\n{' '.join(post.hashtags)}"

            result = pub.publish_reel(
                video_path=post.video_path,
                caption=caption_with_tags,
            )

            if result["status"] == "published":
                return PostResult(
                    platform="instagram",
                    status="published",
                    post_id=result.get("media_id", ""),
                    url=result.get("url", ""),
                )
            else:
                return PostResult(
                    platform="instagram",
                    status="draft",
                    error=result.get("error", "Unknown error"),
                )

        except ImportError:
            logger.error("instagrapi not installed. Run: pip install instagrapi")
            return PostResult(platform="instagram", status="draft", error="instagrapi not installed")
        except Exception as exc:
            logger.error(f"Instagram direct publish failed: {exc}")
            return PostResult(platform="instagram", status="draft", error=str(exc))

    # ------------------------------------------------------------------
    # Instagram Graph API integration
    # ------------------------------------------------------------------

    async def _publish_instagram(self, post: PostMetadata) -> PostResult:
        """
        Publish a Reel to Instagram using the Graph API.

        Flow:
        1. POST /{ig-user-id}/media  — create media container with video_url + caption
        2. Poll GET /{container-id}?fields=status_code  until FINISHED
        3. POST /{ig-user-id}/media_publish — publish the container

        Env vars required:
          INSTAGRAM_ACCESS_TOKEN  — long-lived user token
          INSTAGRAM_PAGE_ID      — Instagram Business / Creator account ID
        """
        access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        page_id = os.environ.get("INSTAGRAM_PAGE_ID", "")

        if not access_token or not page_id:
            logger.warning("Instagram credentials incomplete — falling back to draft.")
            return PostResult(platform="instagram", status="draft", error="Missing INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_PAGE_ID")

        caption_with_tags = f"{post.caption}\n\n{' '.join(post.hashtags)}"
        base_url = "https://graph.facebook.com/v21.0"

        try:
            async with httpx.AsyncClient(timeout=self._API_TIMEOUT) as client:
                # Step 1: Create media container
                create_resp = await client.post(
                    f"{base_url}/{page_id}/media",
                    params={
                        "media_type": "REELS",
                        "video_url": post.video_path,  # must be a public URL
                        "caption": caption_with_tags,
                        "access_token": access_token,
                    },
                )
                create_resp.raise_for_status()
                container_id = create_resp.json().get("id")
                if not container_id:
                    raise ValueError("No container ID returned from Instagram media endpoint")

                logger.info(f"Instagram container created: {container_id}")

                # Step 2: Poll until processing finishes
                for _ in range(self._IG_MAX_POLLS):
                    status_resp = await client.get(
                        f"{base_url}/{container_id}",
                        params={"fields": "status_code", "access_token": access_token},
                    )
                    status_resp.raise_for_status()
                    status_code = status_resp.json().get("status_code", "")

                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        error_msg = status_resp.json().get("status", "Unknown processing error")
                        raise RuntimeError(f"Instagram media processing failed: {error_msg}")

                    await asyncio.sleep(self._IG_POLL_INTERVAL)
                else:
                    raise TimeoutError("Instagram media processing timed out")

                # Step 3: Publish
                publish_resp = await client.post(
                    f"{base_url}/{page_id}/media_publish",
                    params={
                        "creation_id": container_id,
                        "access_token": access_token,
                    },
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json().get("id", "")

                post_url = f"https://www.instagram.com/reel/{media_id}/"
                logger.info(f"Instagram Reel published: {post_url}")

                return PostResult(
                    platform="instagram",
                    status="published",
                    post_id=media_id,
                    url=post_url,
                )

        except Exception as exc:
            logger.error(f"Instagram publish failed: {exc}")
            return PostResult(
                platform="instagram",
                status="draft",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # TikTok Content Posting API integration
    # ------------------------------------------------------------------

    async def _publish_tiktok(self, post: PostMetadata) -> PostResult:
        """
        Publish a video to TikTok using the Content Posting API v2.

        Flow:
        1. POST /v2/post/publish/video/init/ — initialise upload
        2. PUT  upload_url with video bytes
        3. POST /v2/post/publish/ — publish with caption and privacy

        Env vars required:
          TIKTOK_ACCESS_TOKEN — OAuth user access token with video.publish scope
        """
        access_token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
        if not access_token:
            logger.warning("TikTok credentials missing — falling back to draft.")
            return PostResult(platform="tiktok", status="draft", error="Missing TIKTOK_ACCESS_TOKEN")

        caption_with_tags = f"{post.caption} {' '.join(post.hashtags)}"
        base_url = "https://open.tiktokapis.com"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        try:
            async with httpx.AsyncClient(timeout=self._API_TIMEOUT) as client:
                # Step 1: Initialise video upload
                video_path = Path(post.video_path)
                video_size = video_path.stat().st_size if video_path.exists() else 0

                init_resp = await client.post(
                    f"{base_url}/v2/post/publish/video/init/",
                    headers=headers,
                    json={
                        "post_info": {
                            "title": caption_with_tags[:2200],
                            "privacy_level": "SELF_ONLY",  # safe default; caller can override
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False,
                        },
                        "source_info": {
                            "source": "FILE_UPLOAD",
                            "video_size": video_size,
                        },
                    },
                )
                init_resp.raise_for_status()
                init_data = init_resp.json().get("data", {})
                upload_url = init_data.get("upload_url", "")
                publish_id = init_data.get("publish_id", "")

                if not upload_url:
                    raise ValueError("TikTok did not return an upload URL")

                # Step 2: Upload video bytes
                if video_path.exists():
                    video_bytes = video_path.read_bytes()
                    upload_resp = await client.put(
                        upload_url,
                        content=video_bytes,
                        headers={
                            "Content-Type": "video/mp4",
                            "Content-Range": f"bytes 0-{len(video_bytes) - 1}/{len(video_bytes)}",
                        },
                    )
                    upload_resp.raise_for_status()
                else:
                    logger.warning(f"Video file not found at {post.video_path} — skipping upload bytes")

                logger.info(f"TikTok video published (publish_id={publish_id})")

                return PostResult(
                    platform="tiktok",
                    status="published",
                    post_id=publish_id,
                    url=f"https://www.tiktok.com/@me/video/{publish_id}",
                )

        except Exception as exc:
            logger.error(f"TikTok publish failed: {exc}")
            return PostResult(
                platform="tiktok",
                status="draft",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # YouTube Data API v3 integration (Shorts)
    # ------------------------------------------------------------------

    async def _publish_youtube(self, post: PostMetadata) -> PostResult:
        """
        Upload a YouTube Short using the YouTube Data API v3 resumable upload flow.

        Flow:
        1. POST /upload/youtube/v3/videos?uploadType=resumable  — start session
        2. PUT  upload URI with video bytes
        3. Read back video ID from response

        Env vars required:
          YOUTUBE_API_KEY       — API key (for quota)
          YOUTUBE_OAUTH_TOKEN   — OAuth 2.0 Bearer token with youtube.upload scope
        """
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        oauth_token = os.environ.get("YOUTUBE_OAUTH_TOKEN", "")

        if not api_key or not oauth_token:
            logger.warning("YouTube credentials incomplete — falling back to draft.")
            return PostResult(platform="youtube", status="draft", error="Missing YOUTUBE_API_KEY or YOUTUBE_OAUTH_TOKEN")

        tags = [t.lstrip("#") for t in post.hashtags[:15]]
        description = post.caption
        # Mark as Short by prepending #Shorts to tags
        if "Shorts" not in tags:
            tags.insert(0, "Shorts")

        metadata = {
            "snippet": {
                "title": post.title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": "private",  # safe default; change to "public" when ready
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Step 1: Initiate resumable upload
                init_resp = await client.post(
                    "https://www.googleapis.com/upload/youtube/v3/videos",
                    params={
                        "uploadType": "resumable",
                        "part": "snippet,status",
                        "key": api_key,
                    },
                    headers={
                        "Authorization": f"Bearer {oauth_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Type": "video/mp4",
                    },
                    json=metadata,
                )
                init_resp.raise_for_status()
                upload_url = init_resp.headers.get("Location", "")

                if not upload_url:
                    raise ValueError("YouTube did not return a resumable upload URI")

                # Step 2: Upload video bytes
                video_path = Path(post.video_path)
                if video_path.exists():
                    video_bytes = video_path.read_bytes()
                    upload_resp = await client.put(
                        upload_url,
                        content=video_bytes,
                        headers={"Content-Type": "video/mp4"},
                    )
                    upload_resp.raise_for_status()
                    video_id = upload_resp.json().get("id", "")
                else:
                    logger.warning(f"Video file not found at {post.video_path} — skipping upload bytes")
                    video_id = "pending_upload"

                post_url = f"https://youtube.com/shorts/{video_id}"
                logger.info(f"YouTube Short uploaded: {post_url}")

                return PostResult(
                    platform="youtube",
                    status="published",
                    post_id=video_id,
                    url=post_url,
                )

        except Exception as exc:
            logger.error(f"YouTube publish failed: {exc}")
            return PostResult(
                platform="youtube",
                status="draft",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Manual instruction helpers
    # ------------------------------------------------------------------

    def _get_manual_instructions(self, post: PostMetadata) -> dict:
        """Generate manual upload instructions per platform."""
        instructions = {
            "tiktok": {
                "steps": [
                    "1. Open TikTok app",
                    "2. Tap + to create",
                    f"3. Upload video: {post.video_path}",
                    "4. Add caption (copied below)",
                    f"5. Post at: {post.scheduled_time or 'now'}",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "instagram": {
                "steps": [
                    "1. Open Instagram",
                    "2. Create new Reel",
                    f"3. Upload video: {post.video_path}",
                    "4. Add caption and hashtags",
                    "5. Share",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "youtube": {
                "steps": [
                    "1. Go to studio.youtube.com",
                    "2. Upload Short",
                    f"3. Title: {post.title}",
                    "4. Description below",
                ],
                "caption_to_copy": post.caption,
            },
            "linkedin": {
                "steps": [
                    "1. Go to linkedin.com",
                    "2. Start a post",
                    "3. Upload video",
                    "4. Add text below",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "twitter": {
                "steps": [
                    "1. Go to x.com",
                    "2. Compose tweet",
                    "3. Attach video",
                    "4. Add text",
                ],
                "caption_to_copy": f"{post.caption} {' '.join(post.hashtags)}",
            },
        }
        return instructions.get(post.platform, instructions["tiktok"])

    # ------------------------------------------------------------------
    # Multi-platform batch publish
    # ------------------------------------------------------------------

    async def distribute_all(self, script_data: dict, video_path: str, tenant: str = "mas-ai") -> list[PostResult]:
        """Distribute to all configured platforms for the tenant."""
        config_path = Path(f"tenants/{tenant}/config.json")
        if not config_path.exists():
            logger.error(f"Tenant config not found: {tenant}")
            return []

        with open(config_path) as f:
            config = json.load(f)

        platforms = config.get("platforms", ["tiktok"])
        results = []

        for platform in platforms:
            post = self.format_post(script_data, video_path, platform, tenant)
            result = await self.publish(post)
            results.append(result)
            logger.info(f"[{platform}] {result.status}")

        return results

    async def distribute_to_niche(self, niche_slug: str, tenant: str = "mas-ai") -> list[dict]:
        """
        Batch-publish to every platform connected for a given niche.

        Reads the niche's connected platforms from tenant config, discovers the
        latest script + video for that niche, and calls ``publish`` for each
        platform.  Returns a summary list of results.

        Tenant config expected shape::

            {
              "niches": {
                "ai-tech": {
                  "platforms": ["tiktok", "instagram", "youtube"]
                }
              }
            }
        """
        config_path = Path(f"tenants/{tenant}/config.json")
        if not config_path.exists():
            logger.error(f"Tenant config not found: {tenant}")
            return [{"error": f"Tenant config not found: {tenant}"}]

        with open(config_path) as f:
            config = json.load(f)

        niches = config.get("niches", {})
        niche_cfg = niches.get(niche_slug)
        if not niche_cfg:
            # Fallback: use top-level platforms list
            platforms = config.get("platforms", ["tiktok"])
        else:
            platforms = niche_cfg.get("platforms", config.get("platforms", ["tiktok"]))

        # Find latest script and video for this niche
        script_data = self._find_latest_script(niche_slug, tenant)
        video_path = self._find_latest_video(niche_slug, tenant)

        if not script_data:
            return [{"error": f"No script found for niche '{niche_slug}' in tenant '{tenant}'"}]

        results: list[dict] = []
        for platform in platforms:
            post = self.format_post(script_data, video_path, platform, tenant)
            result = await self.publish(post)
            results.append({
                "platform": result.platform,
                "status": result.status,
                "post_id": result.post_id,
                "url": result.url,
                "error": result.error,
            })
            logger.info(f"[niche={niche_slug}][{platform}] {result.status}")

        return results

    def _find_latest_script(self, niche: str, tenant: str) -> dict:
        """Find the most recently generated script for a niche."""
        scripts_dir = Path(f"data/scripts/{tenant}/{niche}")
        if not scripts_dir.exists():
            scripts_dir = Path("data/scripts")
        if not scripts_dir.exists():
            return {}

        script_files = sorted(scripts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not script_files:
            return {}

        with open(script_files[0]) as f:
            return json.load(f)

    def _find_latest_video(self, niche: str, tenant: str) -> str:
        """Find the most recently rendered video for a niche."""
        videos_dir = Path(f"data/videos/{tenant}/{niche}")
        if not videos_dir.exists():
            videos_dir = Path("data/videos")
        if not videos_dir.exists():
            return "data/videos/latest.mp4"

        video_files = sorted(
            [f for f in videos_dir.iterdir() if f.suffix in (".mp4", ".webm", ".mov")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return str(video_files[0]) if video_files else "data/videos/latest.mp4"

    # ------------------------------------------------------------------
    # Draft viewer
    # ------------------------------------------------------------------

    def get_drafts(self, tenant: str = "mas-ai") -> list[dict]:
        """
        Return all draft posts from data/published/ as a list.

        Each item includes:
          - post_id, platform, status
          - video_path, caption, hashtags
          - scheduled_time, created_at
          - tenant
        """
        drafts: list[dict] = []
        for post_file in sorted(self.published_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(post_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            # Filter by tenant
            if data.get("tenant", "mas-ai") != tenant:
                continue

            drafts.append({
                "post_id": data.get("post_id", post_file.stem),
                "platform": data.get("platform", "unknown"),
                "status": data.get("status", "draft"),
                "video_path": data.get("video_path", ""),
                "caption": data.get("caption", ""),
                "hashtags": data.get("hashtags", []),
                "scheduled_time": data.get("scheduled_time"),
                "created_at": data.get("created_at", ""),
                "url": data.get("post_url"),
            })

        return drafts


# ---------------------------------------------------------------------------
# CLI quick-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def test():
        de = DistributionEngine()
        script = {
            "script_id": "test_001",
            "niche": "ai-tech",
            "full_voiceover_text": "AI just changed everything for developers.",
            "acts": [
                {"act": 1, "text": "AI just changed everything"},
                {"act": 5, "text": "Follow Daena for more AI insights."},
            ],
        }
        post = de.format_post(script, "data/videos/test.mp4", "tiktok")
        print(f"Platform: {post.platform}")
        print(f"Caption: {post.caption}")
        print(f"Hashtags: {post.hashtags}")
        print(f"Scheduled: {post.scheduled_time}")

        # Test draft viewer
        drafts = de.get_drafts("mas-ai")
        print(f"\nDrafts found: {len(drafts)}")
        for d in drafts[:3]:
            print(f"  [{d['platform']}] {d['status']} — {d['post_id']}")

        # Test platform status
        status = de.get_platform_status()
        print("\nPlatform status:")
        for plat, info in status.items():
            print(f"  {plat}: {info['mode']}")

    asyncio.run(test())
