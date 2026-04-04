"""
ContentOps Data Models — Multi-tenant, multi-niche, multi-platform.

Hierarchy:
  Tenant (customer) → Niches (content categories) → Platforms (social accounts)

Each platform connection has its own:
- Credentials (stored in credentials.env, gitignored)
- Posting schedule (auto-calculated from audience timezone)
- Hashtag strategy
- Content format preferences
- Analytics tracking
"""
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo

logger = logging.getLogger("contentops.models")


# === Platform posting intelligence ===

# Research-backed optimal posting times per platform (in audience local time)
PLATFORM_OPTIMAL_TIMES = {
    "tiktok": {
        "best_times": ["07:00", "12:00", "19:00", "21:00"],
        "best_days": ["tue", "thu", "fri", "sat"],
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "max_caption": 2200,
        "max_hashtags": 5,
        "content_tips": "First 3 seconds determine everything. Keywords in voiceover matter more than hashtags.",
    },
    "instagram": {
        "best_times": ["08:00", "11:00", "17:00", "21:00"],
        "best_days": ["mon", "wed", "fri"],
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "max_caption": 2200,
        "max_hashtags": 5,
        "content_tips": "Saves = strongest signal. Trending audio boosts distribution.",
    },
    "youtube": {
        "best_times": ["14:00", "16:00", "20:00"],
        "best_days": ["mon", "wed", "fri"],
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "max_caption": 5000,
        "max_hashtags": 15,
        "content_tips": "Rewatch rate is king. Loop structure beats linear for shorts.",
    },
    "linkedin": {
        "best_times": ["08:00", "10:00", "12:00"],
        "best_days": ["tue", "wed", "thu"],
        "max_duration": 180,
        "aspect_ratio": "16:9",
        "max_caption": 3000,
        "max_hashtags": 3,
        "content_tips": "Contrarian takes outperform agreement. Professional insight + personal story = highest engagement.",
    },
    "twitter": {
        "best_times": ["08:00", "12:00", "17:00", "21:00"],
        "best_days": ["mon", "tue", "wed", "thu", "fri"],
        "max_duration": 140,
        "aspect_ratio": "9:16",
        "max_caption": 280,
        "max_hashtags": 2,
        "content_tips": "Timing matters most. Threads outperform single tweets for educational content.",
    },
    "threads": {
        "best_times": ["09:00", "12:00", "18:00"],
        "best_days": ["mon", "wed", "fri", "sat"],
        "max_duration": 300,
        "aspect_ratio": "9:16",
        "max_caption": 500,
        "max_hashtags": 5,
        "content_tips": "Conversational tone. Reply engagement matters.",
    },
    "pinterest": {
        "best_times": ["14:00", "20:00", "22:00"],
        "best_days": ["sat", "sun"],
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "max_caption": 500,
        "max_hashtags": 20,
        "content_tips": "Evergreen content wins. SEO-driven descriptions.",
    },
    "snapchat": {
        "best_times": ["10:00", "13:00", "20:00"],
        "best_days": ["thu", "fri", "sat"],
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "max_caption": 250,
        "max_hashtags": 0,
        "content_tips": "Raw, authentic content outperforms polished.",
    },
}

# Common timezones by region for auto-detection
TIMEZONE_MAP = {
    "us_east": "America/New_York",
    "us_central": "America/Chicago",
    "us_west": "America/Los_Angeles",
    "canada_east": "America/Toronto",
    "canada_west": "America/Vancouver",
    "uk": "Europe/London",
    "eu_central": "Europe/Berlin",
    "eu_east": "Europe/Istanbul",
    "india": "Asia/Kolkata",
    "japan": "Asia/Tokyo",
    "australia": "Australia/Sydney",
    "dubai": "Asia/Dubai",
    "brazil": "America/Sao_Paulo",
    "singapore": "Asia/Singapore",
}


@dataclass
class PlatformConnection:
    """A social media account connected for a specific niche."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    platform: str = "tiktok"
    handle: str = ""  # @username
    display_name: str = ""
    connected: bool = False

    # Auto-calculated settings
    audience_timezone: str = "America/Toronto"
    audience_region: str = "canada_east"
    posting_times: list[str] = field(default_factory=list)  # Auto-set from timezone + platform
    posting_days: list[str] = field(default_factory=list)
    posts_per_week: int = 3

    # Content settings
    hashtag_strategy: list[str] = field(default_factory=list)  # Brand + niche tags
    caption_style: str = "engaging"  # engaging, professional, casual, educational
    cta_template: str = ""

    # Credentials (reference only — actual keys in credentials.env)
    has_api_key: bool = False
    auth_method: str = "manual"  # manual, api, browser_automation

    # Analytics
    follower_count: int = 0
    avg_views: int = 0
    last_posted: Optional[str] = None

    def auto_set_schedule(self):
        """Auto-calculate optimal posting schedule based on platform + timezone."""
        platform_data = PLATFORM_OPTIMAL_TIMES.get(self.platform, PLATFORM_OPTIMAL_TIMES["tiktok"])

        # Convert platform best times to the audience timezone
        self.posting_times = platform_data["best_times"][:self.posts_per_week]
        self.posting_days = platform_data["best_days"][:min(self.posts_per_week, len(platform_data["best_days"]))]

    def get_next_post_time(self) -> str:
        """Calculate next optimal posting time."""
        if not self.posting_times:
            self.auto_set_schedule()

        try:
            tz = ZoneInfo(self.audience_timezone)
        except Exception:
            tz = ZoneInfo("America/Toronto")

        now = datetime.now(tz)
        day_name = now.strftime("%a").lower()

        # Find next available slot
        for time_str in self.posting_times:
            h, m = map(int, time_str.split(":"))
            candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if candidate > now and day_name in self.posting_days:
                return candidate.isoformat()

        # Next day
        for days_ahead in range(1, 8):
            future = now + timedelta(days=days_ahead)
            future_day = future.strftime("%a").lower()
            if future_day in self.posting_days and self.posting_times:
                h, m = map(int, self.posting_times[0].split(":"))
                return future.replace(hour=h, minute=m, second=0, microsecond=0).isoformat()

        return (now + timedelta(hours=24)).isoformat()


@dataclass
class Niche:
    """A content category/niche for a tenant."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""  # e.g., "AI Tech", "Fitness", "Cooking"
    slug: str = ""  # e.g., "ai-tech"
    description: str = ""

    # Content strategy
    content_mix: dict = field(default_factory=lambda: {
        "educational": 0.40,
        "opinion": 0.25,
        "behind_scenes": 0.20,
        "news_commentary": 0.10,
        "community": 0.05,
    })
    target_audience: str = ""  # e.g., "AI founders, builders, tech professionals"
    tone: str = "expert_accessible"  # expert_accessible, casual, professional, edgy

    # Platforms connected for this niche
    platforms: list[PlatformConnection] = field(default_factory=list)

    # Influencer tracking for this niche
    tracked_influencers: list[dict] = field(default_factory=list)

    # Brand elements specific to this niche
    hashtags_always: list[str] = field(default_factory=list)
    hashtags_niche: list[str] = field(default_factory=list)

    # Status
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_platform(self, platform: str, handle: str = "", region: str = "canada_east",
                     posts_per_week: int = 3) -> PlatformConnection:
        """Add a platform connection to this niche."""
        tz = TIMEZONE_MAP.get(region, "America/Toronto")
        conn = PlatformConnection(
            platform=platform,
            handle=handle,
            audience_timezone=tz,
            audience_region=region,
            posts_per_week=posts_per_week,
        )
        conn.auto_set_schedule()

        # Set default hashtags
        conn.hashtag_strategy = self.hashtags_always + self.hashtags_niche

        self.platforms.append(conn)
        return conn

    def get_platform(self, platform: str) -> Optional[PlatformConnection]:
        """Get platform connection by name."""
        for p in self.platforms:
            if p.platform == platform:
                return p
        return None

    def get_all_posting_schedule(self) -> list[dict]:
        """Get combined posting schedule across all platforms."""
        schedule = []
        for p in self.platforms:
            for day in p.posting_days:
                for time in p.posting_times:
                    schedule.append({
                        "platform": p.platform,
                        "handle": p.handle,
                        "day": day,
                        "time": time,
                        "timezone": p.audience_timezone,
                    })
        return sorted(schedule, key=lambda s: (
            ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(s["day"]),
            s["time"]
        ))


@dataclass
class Tenant:
    """A customer/client of the ContentOps agency."""
    id: str = ""
    display_name: str = ""
    avatar_name: str = ""  # AI persona name

    # Brand identity
    brand_color: str = "#00c8ff"
    brand_accent: str = "#d4a853"
    tagline: str = ""
    logo_path: str = ""

    # Persona
    persona_name: str = ""
    persona_personality: str = ""
    persona_tone: str = ""

    # Voice
    voice_provider: str = "kokoro"  # kokoro, elevenlabs, f5tts
    voice_id: str = ""  # ElevenLabs voice ID or local model path
    voice_reference_audio: str = ""  # For voice cloning

    # Niches (content categories)
    niches: list[Niche] = field(default_factory=list)

    # Settings
    default_region: str = "canada_east"
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # CTA templates
    cta_templates: dict = field(default_factory=lambda: {
        "follow": "Follow {persona} for more.",
        "save": "Save this — you'll need it.",
        "share": "Share this with someone who needs it.",
        "comment": "Drop a comment if you've seen this.",
        "subscribe": "Subscribe — Part 2 is coming.",
    })

    def add_niche(self, name: str, target_audience: str = "",
                  hashtags: list[str] = None) -> Niche:
        """Add a new content niche."""
        slug = name.lower().replace(" ", "-").replace("&", "and")
        niche = Niche(
            name=name,
            slug=slug,
            target_audience=target_audience,
            hashtags_always=[f"#{self.avatar_name}"] if self.avatar_name else [],
            hashtags_niche=hashtags or [],
        )
        self.niches.append(niche)
        return niche

    def get_niche(self, slug: str) -> Optional[Niche]:
        """Get niche by slug."""
        for n in self.niches:
            if n.slug == slug:
                return n
        return None

    def get_all_platforms(self) -> list[dict]:
        """Get all platform connections across all niches."""
        platforms = []
        for niche in self.niches:
            for p in niche.platforms:
                platforms.append({
                    "niche": niche.name,
                    "niche_slug": niche.slug,
                    "platform": p.platform,
                    "handle": p.handle,
                    "connected": p.connected,
                    "posts_per_week": p.posts_per_week,
                    "timezone": p.audience_timezone,
                })
        return platforms

    def get_weekly_content_plan(self) -> list[dict]:
        """Generate a weekly content plan across all niches and platforms."""
        plan = []
        for niche in self.niches:
            if not niche.active:
                continue
            schedule = niche.get_all_posting_schedule()
            for slot in schedule:
                # Determine content type based on mix
                plan.append({
                    "niche": niche.name,
                    "platform": slot["platform"],
                    "handle": slot.get("handle", ""),
                    "day": slot["day"],
                    "time": slot["time"],
                    "timezone": slot["timezone"],
                    "content_type": "educational",  # Would be randomized by content_mix weights
                })
        return plan


class TenantStore:
    """Manages tenant data on disk."""

    def __init__(self, tenants_dir: str = "tenants"):
        self.tenants_dir = Path(tenants_dir)
        self.tenants_dir.mkdir(parents=True, exist_ok=True)

    def save(self, tenant: Tenant):
        """Save tenant to disk."""
        tenant_dir = self.tenants_dir / tenant.id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        (tenant_dir / "avatars").mkdir(exist_ok=True)
        (tenant_dir / "posts").mkdir(exist_ok=True)

        # Convert to dict (handle nested dataclasses)
        data = self._tenant_to_dict(tenant)

        with open(tenant_dir / "config.json", "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Tenant saved: {tenant.id}")

    def load(self, tenant_id: str) -> Optional[Tenant]:
        """Load tenant from disk."""
        config_path = self.tenants_dir / tenant_id / "config.json"
        if not config_path.exists():
            return None

        with open(config_path) as f:
            data = json.load(f)

        return self._dict_to_tenant(data)

    def list_all(self) -> list[Tenant]:
        """List all tenants."""
        tenants = []
        for d in self.tenants_dir.iterdir():
            if d.is_dir() and (d / "config.json").exists():
                tenant = self.load(d.name)
                if tenant:
                    tenants.append(tenant)
        return tenants

    def delete(self, tenant_id: str):
        """Delete a tenant."""
        import shutil
        tenant_dir = self.tenants_dir / tenant_id
        if tenant_dir.exists():
            shutil.rmtree(tenant_dir)

    def _tenant_to_dict(self, tenant: Tenant) -> dict:
        """Convert Tenant (with nested dataclasses) to dict."""
        d = {
            "id": tenant.id,
            "display_name": tenant.display_name,
            "avatar_name": tenant.avatar_name,
            "brand_color": tenant.brand_color,
            "brand_accent": tenant.brand_accent,
            "tagline": tenant.tagline,
            "logo_path": tenant.logo_path,
            "persona_name": tenant.persona_name,
            "persona_personality": tenant.persona_personality,
            "persona_tone": tenant.persona_tone,
            "voice_provider": tenant.voice_provider,
            "voice_id": tenant.voice_id,
            "voice_reference_audio": tenant.voice_reference_audio,
            "default_region": tenant.default_region,
            "active": tenant.active,
            "created_at": tenant.created_at,
            "cta_templates": tenant.cta_templates,
            "niches": [],
        }

        for niche in tenant.niches:
            niche_dict = {
                "id": niche.id,
                "name": niche.name,
                "slug": niche.slug,
                "description": niche.description,
                "content_mix": niche.content_mix,
                "target_audience": niche.target_audience,
                "tone": niche.tone,
                "hashtags_always": niche.hashtags_always,
                "hashtags_niche": niche.hashtags_niche,
                "tracked_influencers": niche.tracked_influencers,
                "active": niche.active,
                "created_at": niche.created_at,
                "platforms": [],
            }

            for p in niche.platforms:
                niche_dict["platforms"].append({
                    "id": p.id,
                    "platform": p.platform,
                    "handle": p.handle,
                    "display_name": p.display_name,
                    "connected": p.connected,
                    "audience_timezone": p.audience_timezone,
                    "audience_region": p.audience_region,
                    "posting_times": p.posting_times,
                    "posting_days": p.posting_days,
                    "posts_per_week": p.posts_per_week,
                    "hashtag_strategy": p.hashtag_strategy,
                    "caption_style": p.caption_style,
                    "cta_template": p.cta_template,
                    "has_api_key": p.has_api_key,
                    "auth_method": p.auth_method,
                    "follower_count": p.follower_count,
                    "avg_views": p.avg_views,
                    "last_posted": p.last_posted,
                })

            d["niches"].append(niche_dict)

        return d

    def _dict_to_tenant(self, data: dict) -> Tenant:
        """Convert dict back to Tenant."""
        tenant = Tenant(
            id=data.get("id", ""),
            display_name=data.get("display_name", ""),
            avatar_name=data.get("avatar_name", ""),
            brand_color=data.get("brand_color", "#00c8ff"),
            brand_accent=data.get("brand_accent", "#d4a853"),
            tagline=data.get("tagline", ""),
            logo_path=data.get("logo_path", ""),
            persona_name=data.get("persona_name", ""),
            persona_personality=data.get("persona_personality", ""),
            persona_tone=data.get("persona_tone", ""),
            voice_provider=data.get("voice_provider", "kokoro"),
            voice_id=data.get("voice_id", ""),
            voice_reference_audio=data.get("voice_reference_audio", ""),
            default_region=data.get("default_region", "canada_east"),
            active=data.get("active", True),
            created_at=data.get("created_at", ""),
            cta_templates=data.get("cta_templates", {}),
        )

        for niche_data in data.get("niches", []):
            niche = Niche(
                id=niche_data.get("id", str(uuid.uuid4())[:8]),
                name=niche_data.get("name", ""),
                slug=niche_data.get("slug", ""),
                description=niche_data.get("description", ""),
                content_mix=niche_data.get("content_mix", {}),
                target_audience=niche_data.get("target_audience", ""),
                tone=niche_data.get("tone", "expert_accessible"),
                hashtags_always=niche_data.get("hashtags_always", []),
                hashtags_niche=niche_data.get("hashtags_niche", []),
                tracked_influencers=niche_data.get("tracked_influencers", []),
                active=niche_data.get("active", True),
                created_at=niche_data.get("created_at", ""),
            )

            for p_data in niche_data.get("platforms", []):
                conn = PlatformConnection(
                    id=p_data.get("id", str(uuid.uuid4())[:8]),
                    platform=p_data.get("platform", "tiktok"),
                    handle=p_data.get("handle", ""),
                    display_name=p_data.get("display_name", ""),
                    connected=p_data.get("connected", False),
                    audience_timezone=p_data.get("audience_timezone", "America/Toronto"),
                    audience_region=p_data.get("audience_region", "canada_east"),
                    posting_times=p_data.get("posting_times", []),
                    posting_days=p_data.get("posting_days", []),
                    posts_per_week=p_data.get("posts_per_week", 3),
                    hashtag_strategy=p_data.get("hashtag_strategy", []),
                    caption_style=p_data.get("caption_style", "engaging"),
                    cta_template=p_data.get("cta_template", ""),
                    has_api_key=p_data.get("has_api_key", False),
                    auth_method=p_data.get("auth_method", "manual"),
                    follower_count=p_data.get("follower_count", 0),
                    avg_views=p_data.get("avg_views", 0),
                    last_posted=p_data.get("last_posted"),
                )
                niche.platforms.append(conn)

            tenant.niches.append(niche)

        return tenant


def create_masai_tenant() -> Tenant:
    """Create the default MAS-AI / Daena tenant with proper niche structure."""
    tenant = Tenant(
        id="mas-ai",
        display_name="MAS-AI Technologies",
        avatar_name="Daena",
        brand_color="#00c8ff",
        brand_accent="#d4a853",
        tagline="Governed AI That Gets Things Done",
        persona_name="Daena",
        persona_personality="Confident, intellectually sharp, slightly witty, data-driven",
        persona_tone="Expert but accessible, founder energy, not corporate",
        voice_provider="kokoro",
        voice_id="XrExE9yKIg1WjnnlVkGX",
        default_region="canada_east",
    )

    # Niche 1: AI Tech
    ai_niche = tenant.add_niche(
        "AI Tech",
        target_audience="AI founders, builders, tech professionals",
        hashtags=["#AIGovernance", "#AIAgents", "#TechStartup", "#AITools"],
    )
    ai_niche.add_platform("tiktok", "@daena_ai", "canada_east", posts_per_week=4)
    ai_niche.add_platform("instagram", "@daena.ai", "canada_east", posts_per_week=3)
    ai_niche.add_platform("youtube", "@DaenaAI", "canada_east", posts_per_week=3)
    ai_niche.add_platform("linkedin", "@mas-ai-technologies", "canada_east", posts_per_week=3)
    ai_niche.add_platform("twitter", "@daena_ai", "canada_east", posts_per_week=5)
    ai_niche.tracked_influencers = [
        {"handle": "@aiexplained", "platform": "youtube", "priority": 1},
        {"handle": "@gregisenberg", "platform": "tiktok", "priority": 1},
        {"handle": "@alexhormozi", "platform": "youtube", "priority": 2},
        {"handle": "@levelsio", "platform": "twitter", "priority": 2},
    ]

    # Niche 2: Startup / Founder
    startup_niche = tenant.add_niche(
        "Startup Insights",
        target_audience="Startup founders, indie hackers, bootstrappers",
        hashtags=["#StartupLife", "#FounderTips", "#BuildInPublic", "#IndieHacker"],
    )
    startup_niche.add_platform("tiktok", "@daena_ai", "canada_east", posts_per_week=2)
    startup_niche.add_platform("linkedin", "@mas-ai-technologies", "canada_east", posts_per_week=2)
    startup_niche.add_platform("twitter", "@daena_ai", "canada_east", posts_per_week=3)

    return tenant


if __name__ == "__main__":
    # Create and save MAS-AI tenant
    store = TenantStore()
    tenant = create_masai_tenant()
    store.save(tenant)

    print(f"Tenant: {tenant.display_name}")
    print(f"Niches: {len(tenant.niches)}")
    for niche in tenant.niches:
        print(f"  {niche.name}: {len(niche.platforms)} platforms")
        for p in niche.platforms:
            print(f"    - {p.platform} {p.handle} ({p.posts_per_week}/week, {p.audience_timezone})")

    print(f"\nWeekly content plan: {len(tenant.get_weekly_content_plan())} slots")
    print(f"All platforms: {len(tenant.get_all_platforms())}")
