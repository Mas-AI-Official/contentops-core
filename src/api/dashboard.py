"""
ContentOps Dashboard API — Multi-tenant, Multi-niche, Multi-platform.

Hierarchy: Tenant → Niches → Platform Connections
Each platform auto-calculates optimal posting schedule from audience timezone.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("contentops.dashboard")

app = FastAPI(
    title="ContentOps Dashboard",
    version="2.0.0",
    description="Autonomous AI Media Agency — Multi-tenant Content Operations",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Pydantic Request Models ===

class TenantCreate(BaseModel):
    tenant_id: str
    display_name: str
    avatar_name: str = ""
    brand_color: str = "#00c8ff"
    tagline: str = ""
    persona_tone: str = "expert_accessible"
    voice_provider: str = "kokoro"
    default_region: str = "canada_east"

class TenantUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_name: Optional[str] = None
    brand_color: Optional[str] = None
    brand_accent: Optional[str] = None
    tagline: Optional[str] = None
    persona_name: Optional[str] = None
    persona_personality: Optional[str] = None
    persona_tone: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None

class NicheCreate(BaseModel):
    name: str
    target_audience: str = ""
    hashtags: list[str] = []
    tone: str = "expert_accessible"
    description: str = ""

class NicheUpdate(BaseModel):
    name: Optional[str] = None
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    description: Optional[str] = None
    content_mix: Optional[dict] = None
    hashtags_niche: Optional[list[str]] = None
    active: Optional[bool] = None

class PlatformConnect(BaseModel):
    platform: str
    handle: str = ""
    region: str = "canada_east"
    posts_per_week: int = 3
    caption_style: str = "engaging"

class PlatformUpdate(BaseModel):
    handle: Optional[str] = None
    region: Optional[str] = None
    posts_per_week: Optional[int] = None
    caption_style: Optional[str] = None
    audience_timezone: Optional[str] = None
    connected: Optional[bool] = None
    has_api_key: Optional[bool] = None
    auth_method: Optional[str] = None

class PipelineRequest(BaseModel):
    source_material: str
    platform: str = "tiktok"
    niche_slug: str = ""
    mode: str = "test"

class IdeaRequest(BaseModel):
    topic: str
    niche_slug: str = ""
    platform: str = "tiktok"
    priority: str = "normal"


# === Helper: get TenantStore ===

def _get_store():
    import sys
    sys.path.insert(0, ".")
    from src.models import TenantStore
    return TenantStore()


# === System Status ===

@app.get("/health")
async def health():
    return {"status": "ok", "service": "contentops-dashboard", "version": "2.0.0"}


@app.get("/api/status")
async def get_status():
    from src.agents.tool_manager import tool_manager
    store = _get_store()
    tenants = store.list_all()

    total_niches = sum(len(t.niches) for t in tenants)
    total_platforms = sum(len(t.get_all_platforms()) for t in tenants)

    return {
        "status": "operational",
        "version": "2.0.0",
        "tenants": len(tenants),
        "niches": total_niches,
        "platform_connections": total_platforms,
        "tools": tool_manager.status(),
        "timestamp": datetime.now().isoformat(),
    }


# === Available Options ===

@app.get("/api/platforms")
async def list_available_platforms():
    """List all supported platforms with their specs and tips."""
    from src.models import PLATFORM_OPTIMAL_TIMES
    return {"platforms": PLATFORM_OPTIMAL_TIMES}


@app.get("/api/regions")
async def list_available_regions():
    """List all supported audience regions/timezones."""
    from src.models import TIMEZONE_MAP
    return {"regions": {k: {"timezone": v, "label": k.replace("_", " ").title()} for k, v in TIMEZONE_MAP.items()}}


# === Tenant CRUD ===

@app.get("/api/tenants")
async def list_tenants():
    store = _get_store()
    tenants = store.list_all()
    return {
        "tenants": [
            {
                "id": t.id,
                "display_name": t.display_name,
                "avatar_name": t.avatar_name,
                "niches": len(t.niches),
                "platforms": len(t.get_all_platforms()),
                "active": t.active,
                "brand_color": t.brand_color,
            }
            for t in tenants
        ]
    }


@app.get("/api/tenant/{tenant_id}")
async def get_tenant(tenant_id: str):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    from src.models import TenantStore
    return store._tenant_to_dict(tenant)


@app.post("/api/tenant")
async def create_tenant(req: TenantCreate):
    store = _get_store()
    if store.load(req.tenant_id):
        raise HTTPException(409, f"Tenant '{req.tenant_id}' already exists")

    from src.models import Tenant
    tenant = Tenant(
        id=req.tenant_id,
        display_name=req.display_name,
        avatar_name=req.avatar_name,
        brand_color=req.brand_color,
        tagline=req.tagline,
        persona_name=req.avatar_name,
        persona_tone=req.persona_tone,
        voice_provider=req.voice_provider,
        default_region=req.default_region,
    )
    store.save(tenant)
    return {"message": f"Tenant '{req.tenant_id}' created", "tenant_id": req.tenant_id}


@app.put("/api/tenant/{tenant_id}")
async def update_tenant(tenant_id: str, req: TenantUpdate):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)

    store.save(tenant)
    return {"message": f"Tenant '{tenant_id}' updated"}


@app.delete("/api/tenant/{tenant_id}")
async def delete_tenant(tenant_id: str):
    store = _get_store()
    if not store.load(tenant_id):
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")
    store.delete(tenant_id)
    return {"message": f"Tenant '{tenant_id}' deleted"}


# === Niche CRUD ===

@app.get("/api/tenant/{tenant_id}/niches")
async def list_niches(tenant_id: str):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    return {
        "niches": [
            {
                "id": n.id,
                "name": n.name,
                "slug": n.slug,
                "target_audience": n.target_audience,
                "tone": n.tone,
                "platforms": len(n.platforms),
                "active": n.active,
            }
            for n in tenant.niches
        ]
    }


@app.post("/api/tenant/{tenant_id}/niche")
async def create_niche(tenant_id: str, req: NicheCreate):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    niche = tenant.add_niche(req.name, req.target_audience, req.hashtags)
    niche.tone = req.tone
    niche.description = req.description
    store.save(tenant)

    return {"message": f"Niche '{req.name}' created", "niche_slug": niche.slug, "niche_id": niche.id}


@app.put("/api/tenant/{tenant_id}/niche/{niche_slug}")
async def update_niche(tenant_id: str, niche_slug: str, req: NicheUpdate):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    niche = tenant.get_niche(niche_slug)
    if not niche:
        raise HTTPException(404, f"Niche '{niche_slug}' not found")

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(niche, field, value)

    store.save(tenant)
    return {"message": f"Niche '{niche_slug}' updated"}


@app.delete("/api/tenant/{tenant_id}/niche/{niche_slug}")
async def delete_niche(tenant_id: str, niche_slug: str):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")

    tenant.niches = [n for n in tenant.niches if n.slug != niche_slug]
    store.save(tenant)
    return {"message": f"Niche '{niche_slug}' deleted"}


# === Platform Connection CRUD ===

@app.get("/api/tenant/{tenant_id}/niche/{niche_slug}/platforms")
async def list_niche_platforms(tenant_id: str, niche_slug: str):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404)

    niche = tenant.get_niche(niche_slug)
    if not niche:
        raise HTTPException(404, f"Niche '{niche_slug}' not found")

    return {
        "platforms": [
            {
                "id": p.id,
                "platform": p.platform,
                "handle": p.handle,
                "connected": p.connected,
                "audience_timezone": p.audience_timezone,
                "audience_region": p.audience_region,
                "posting_times": p.posting_times,
                "posting_days": p.posting_days,
                "posts_per_week": p.posts_per_week,
                "caption_style": p.caption_style,
                "auth_method": p.auth_method,
                "has_api_key": p.has_api_key,
                "next_post": p.get_next_post_time(),
            }
            for p in niche.platforms
        ]
    }


@app.post("/api/tenant/{tenant_id}/niche/{niche_slug}/platform")
async def connect_platform(tenant_id: str, niche_slug: str, req: PlatformConnect):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404)

    niche = tenant.get_niche(niche_slug)
    if not niche:
        raise HTTPException(404, f"Niche '{niche_slug}' not found")

    conn = niche.add_platform(req.platform, req.handle, req.region, req.posts_per_week)
    conn.caption_style = req.caption_style
    store.save(tenant)

    return {
        "message": f"{req.platform} connected to niche '{niche_slug}'",
        "platform_id": conn.id,
        "posting_schedule": {"times": conn.posting_times, "days": conn.posting_days},
        "timezone": conn.audience_timezone,
    }


@app.put("/api/tenant/{tenant_id}/niche/{niche_slug}/platform/{platform_id}")
async def update_platform(tenant_id: str, niche_slug: str, platform_id: str, req: PlatformUpdate):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404)

    niche = tenant.get_niche(niche_slug)
    if not niche:
        raise HTTPException(404)

    platform = None
    for p in niche.platforms:
        if p.id == platform_id:
            platform = p
            break

    if not platform:
        raise HTTPException(404, f"Platform '{platform_id}' not found")

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(platform, field, value)

    # Recalculate schedule if region changed
    if req.region:
        from src.models import TIMEZONE_MAP
        platform.audience_timezone = TIMEZONE_MAP.get(req.region, platform.audience_timezone)
        platform.auto_set_schedule()

    store.save(tenant)
    return {"message": "Platform updated", "posting_schedule": {"times": platform.posting_times, "days": platform.posting_days}}


@app.delete("/api/tenant/{tenant_id}/niche/{niche_slug}/platform/{platform_id}")
async def disconnect_platform(tenant_id: str, niche_slug: str, platform_id: str):
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404)

    niche = tenant.get_niche(niche_slug)
    if not niche:
        raise HTTPException(404)

    niche.platforms = [p for p in niche.platforms if p.id != platform_id]
    store.save(tenant)
    return {"message": "Platform disconnected"}


# === Schedule ===

@app.get("/api/tenant/{tenant_id}/schedule")
async def get_schedule(tenant_id: str):
    """Get weekly content schedule across all niches and platforms."""
    store = _get_store()
    tenant = store.load(tenant_id)
    if not tenant:
        raise HTTPException(404)

    return {"schedule": tenant.get_weekly_content_plan(), "total_slots": len(tenant.get_weekly_content_plan())}


# === Content Queue ===

@app.get("/api/queue")
async def get_queue():
    scripts_dir = Path("data/scripts")
    queue = []
    if scripts_dir.exists():
        for f in sorted(scripts_dir.glob("*.json"), reverse=True)[:20]:
            with open(f) as fh:
                data = json.load(fh)
                queue.append({
                    "script_id": data.get("script_id"),
                    "platform": data.get("platform"),
                    "tenant": data.get("tenant"),
                    "status": data.get("production_status"),
                    "quality_score": data.get("quality_score"),
                    "hook_type": data.get("hook_type"),
                    "created_at": data.get("created_at"),
                })
    return {"queue": queue, "total": len(queue)}


# === Analytics ===

@app.get("/api/analytics")
async def get_analytics():
    return {
        "scripts": len(list(Path("data/scripts").glob("*.json"))) if Path("data/scripts").exists() else 0,
        "audio": len(list(Path("data/audio").glob("*"))) if Path("data/audio").exists() else 0,
        "videos": len(list(Path("data/videos").glob("*/*.mp4"))) if Path("data/videos").exists() else 0,
        "published": len(list(Path("data/published").glob("*.json"))) if Path("data/published").exists() else 0,
        "trends_cached": len(json.load(open("src/intelligence/trend_cache.json")).get("trends", [])) if Path("src/intelligence/trend_cache.json").exists() else 0,
    }


# === Hooks ===

@app.get("/api/hooks")
async def get_hooks():
    vault_path = Path("src/intelligence/hook_vault.json")
    if vault_path.exists():
        with open(vault_path) as f:
            return json.load(f)
    return {"hooks": [], "patterns": []}


# === Ideas ===

@app.post("/api/idea")
async def drop_idea(idea: IdeaRequest):
    ideas_dir = Path("data/ideas")
    ideas_dir.mkdir(parents=True, exist_ok=True)

    idea_data = {
        "topic": idea.topic,
        "niche_slug": idea.niche_slug,
        "platform": idea.platform,
        "priority": idea.priority,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    }

    filepath = ideas_dir / f"idea_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, "w") as f:
        json.dump(idea_data, f, indent=2)

    return {"message": "Idea queued", "id": filepath.stem}


# === Pipeline ===

@app.post("/api/pipeline/run")
async def run_pipeline(req: PipelineRequest):
    from src.agents.pipeline import ContentOpsPipeline

    pipeline = ContentOpsPipeline()
    result = await pipeline.run_full(
        req.source_material,
        req.platform,
        tenant="mas-ai",  # TODO: get from auth
        mode=req.mode,
        skip_video=False,
    )

    return result.to_dict()


# === Trends ===

@app.get("/api/trends")
async def get_trends():
    """Get cached trending topics."""
    cache_path = Path("src/intelligence/trend_cache.json")
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {"trends": [], "scanned_at": None}


@app.post("/api/trends/scan")
async def scan_trends():
    """Trigger a new trend scan."""
    from src.agents.virai_scout import VirAIScout
    scout = VirAIScout()
    result = await scout.run(mode="trends")
    return result


# === Dashboard Frontend ===

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard frontend."""
    from fastapi.responses import FileResponse
    dashboard_path = Path("src/dashboard/index.html")
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Dashboard frontend not found. Visit /docs for API."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
