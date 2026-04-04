"""
Distribution Engine — Multi-Platform Publishing.

Handles platform-specific formatting, optimal timing, and publishing.
Supports: TikTok, Instagram, YouTube, LinkedIn, X/Twitter.
Uses platform APIs where available, with Playwright browser automation as fallback.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("contentops.distributor")


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
            "api_env": "INSTAGRAM_ACCESS_TOKEN",
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

    def __init__(self):
        self.published_dir = Path("data/published")
        self.published_dir.mkdir(parents=True, exist_ok=True)

    def get_platform_status(self) -> dict:
        """Check which platforms have API credentials configured."""
        import os
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
        # Always include brand hashtags
        always = brand.get("hashtags", {}).get("always", ["#DaenaAI"])
        niche_tags = brand.get("hashtags", {}).get("niche", ["#AI", "#TechStartup"])

        if platform == "linkedin":
            return always[:1] + niche_tags[:2]  # Max 3 for LinkedIn
        elif platform == "twitter":
            return always[:1] + niche_tags[:1]  # Max 2 for Twitter
        else:
            return always + niche_tags[:3]  # Max 5 for TikTok/IG

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

    async def publish(self, post: PostMetadata) -> PostResult:
        """
        Publish to platform. Currently saves as draft for manual upload.
        API integration for each platform will be added when credentials are configured.
        """
        # For now, save as a ready-to-post package
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

        # Save post package
        post_path = self.published_dir / f"{post_id}.json"
        with open(post_path, "w", encoding="utf-8") as f:
            json.dump(post_package, f, indent=2, ensure_ascii=False)

        logger.info(f"Post package ready: {post_path}")

        # Try API publishing if credentials are available
        api_result = await self._try_api_publish(post)
        if api_result:
            return api_result

        return PostResult(
            platform=post.platform,
            status="draft",
            post_id=post_id,
        )

    async def _try_api_publish(self, post: PostMetadata) -> Optional[PostResult]:
        """Attempt to publish via platform API. Returns None if no credentials."""
        import os

        if post.platform == "youtube" and os.environ.get("YOUTUBE_API_KEY"):
            return await self._publish_youtube(post)
        elif post.platform == "tiktok" and os.environ.get("TIKTOK_ACCESS_TOKEN"):
            return await self._publish_tiktok(post)
        elif post.platform == "instagram" and os.environ.get("INSTAGRAM_ACCESS_TOKEN"):
            return await self._publish_instagram(post)

        return None

    async def _publish_youtube(self, post: PostMetadata) -> PostResult:
        """Publish to YouTube using Data API v3."""
        # Placeholder — requires OAuth2 flow setup
        logger.info(f"YouTube API publish not yet implemented. Draft saved.")
        return PostResult(platform="youtube", status="draft", post_id="yt_pending")

    async def _publish_tiktok(self, post: PostMetadata) -> PostResult:
        """Publish to TikTok using Content Posting API."""
        logger.info(f"TikTok API publish not yet implemented. Draft saved.")
        return PostResult(platform="tiktok", status="draft", post_id="tt_pending")

    async def _publish_instagram(self, post: PostMetadata) -> PostResult:
        """Publish to Instagram using Graph API."""
        logger.info(f"Instagram API publish not yet implemented. Draft saved.")
        return PostResult(platform="instagram", status="draft", post_id="ig_pending")

    def _get_manual_instructions(self, post: PostMetadata) -> dict:
        """Generate manual upload instructions per platform."""
        instructions = {
            "tiktok": {
                "steps": [
                    f"1. Open TikTok app",
                    f"2. Tap + to create",
                    f"3. Upload video: {post.video_path}",
                    f"4. Add caption (copied below)",
                    f"5. Post at: {post.scheduled_time or 'now'}",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "instagram": {
                "steps": [
                    f"1. Open Instagram",
                    f"2. Create new Reel",
                    f"3. Upload video: {post.video_path}",
                    f"4. Add caption and hashtags",
                    f"5. Share",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "youtube": {
                "steps": [
                    f"1. Go to studio.youtube.com",
                    f"2. Upload Short",
                    f"3. Title: {post.title}",
                    f"4. Description below",
                ],
                "caption_to_copy": post.caption,
            },
            "linkedin": {
                "steps": [
                    f"1. Go to linkedin.com",
                    f"2. Start a post",
                    f"3. Upload video",
                    f"4. Add text below",
                ],
                "caption_to_copy": f"{post.caption}\n\n{' '.join(post.hashtags)}",
            },
            "twitter": {
                "steps": [
                    f"1. Go to x.com",
                    f"2. Compose tweet",
                    f"3. Attach video",
                    f"4. Add text",
                ],
                "caption_to_copy": f"{post.caption} {' '.join(post.hashtags)}",
            },
        }
        return instructions.get(post.platform, instructions["tiktok"])

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

    asyncio.run(test())
