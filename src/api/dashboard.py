"""
ContentOps Dashboard API — The single view the operator opens.
FastAPI backend providing full system visibility and control.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("contentops.dashboard")

app = FastAPI(title="ContentOps Dashboard", version="1.0.0", description="Autonomous AI Media Agency Control Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IdeaRequest(BaseModel):
    topic: str
    platform: str = "tiktok"
    tenant: str = "mas-ai"
    priority: str = "normal"


class PipelineRequest(BaseModel):
    tenant: str = "mas-ai"
    source_material: str
    platform: str = "tiktok"
    mode: str = "test"  # test or production


class TenantCreate(BaseModel):
    tenant_id: str
    display_name: str
    avatar_name: str
    niche: str
    platforms: list[str] = ["tiktok", "instagram"]
    brand_color: str = "#00c8ff"


# --- Status ---
@app.get("/api/status")
async def get_status():
    """Full system status."""
    from src.agents.tool_manager import tool_manager
    return {
        "status": "operational",
        "build_phase": "Phase 1 - Foundation",
        "tools": tool_manager.status(),
        "timestamp": datetime.now().isoformat(),
    }


# --- Queue ---
@app.get("/api/queue")
async def get_queue():
    """Current content production queue."""
    scripts_dir = Path("data/scripts")
    queue = []
    if scripts_dir.exists():
        for f in sorted(scripts_dir.glob("*.json"), reverse=True):
            with open(f) as fh:
                data = json.load(fh)
                queue.append({
                    "script_id": data.get("script_id"),
                    "platform": data.get("platform"),
                    "status": data.get("production_status"),
                    "quality_score": data.get("quality_score"),
                    "created_at": data.get("created_at"),
                })
    return {"queue": queue, "total": len(queue)}


# --- Analytics ---
@app.get("/api/analytics")
async def get_analytics():
    """Performance metrics summary."""
    return {
        "total_scripts_generated": len(list(Path("data/scripts").glob("*.json"))) if Path("data/scripts").exists() else 0,
        "total_audio_generated": len(list(Path("data/audio").glob("*.wav"))) + len(list(Path("data/audio").glob("*.mp3"))) if Path("data/audio").exists() else 0,
        "total_videos_rendered": len(list(Path("data/videos").glob("*.mp4"))) if Path("data/videos").exists() else 0,
        "total_published": len(list(Path("data/published").glob("*.json"))) if Path("data/published").exists() else 0,
    }


# --- Hooks ---
@app.get("/api/hooks")
async def get_hooks():
    """Hook Vault contents."""
    vault_path = Path("src/intelligence/hook_vault.json")
    if vault_path.exists():
        with open(vault_path) as f:
            return json.load(f)
    return {"hooks": [], "patterns": []}


# --- Idea Drop ---
@app.post("/api/idea")
async def drop_idea(idea: IdeaRequest):
    """Operator drops a content idea into the queue."""
    ideas_dir = Path("data/ideas")
    ideas_dir.mkdir(parents=True, exist_ok=True)

    idea_data = {
        "topic": idea.topic,
        "platform": idea.platform,
        "tenant": idea.tenant,
        "priority": idea.priority,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    }

    filepath = ideas_dir / f"idea_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, "w") as f:
        json.dump(idea_data, f, indent=2)

    return {"message": "Idea queued", "id": filepath.stem}


# --- Pipeline Trigger ---
@app.post("/api/pipeline/run")
async def run_pipeline(req: PipelineRequest):
    """Trigger a full pipeline run for a topic."""
    from src.agents.script_maestro import ScriptMaestro
    from src.agents.avatar_engine import AvatarEngine

    sm = ScriptMaestro()
    script = await sm.create_script(req.source_material, req.platform, req.tenant)
    sm.save_script(script)

    result = {"script_id": script.script_id, "status": script.production_status, "quality_score": script.quality_score}

    if script.production_status == "approved":
        ae = AvatarEngine()
        audio_path = await ae.generate_voice(script.full_voiceover_text, script.script_id, req.mode)
        result["audio_path"] = audio_path

    return result


# --- Tenants ---
@app.get("/api/tenants")
async def list_tenants():
    """List all tenants."""
    tenants_dir = Path("tenants")
    tenants = []
    if tenants_dir.exists():
        for d in tenants_dir.iterdir():
            if d.is_dir():
                config_path = d / "config.json"
                if config_path.exists():
                    with open(config_path) as f:
                        tenants.append(json.load(f))
    return {"tenants": tenants}


@app.get("/api/tenant/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant details."""
    config_path = Path(f"tenants/{tenant_id}/config.json")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")
    with open(config_path) as f:
        config = json.load(f)

    brand_path = Path(f"tenants/{tenant_id}/brand.json")
    brand = {}
    if brand_path.exists():
        with open(brand_path) as f:
            brand = json.load(f)

    return {"config": config, "brand": brand}


@app.post("/api/tenant/create")
async def create_tenant(tenant: TenantCreate):
    """Create a new tenant (new agency client)."""
    tenant_dir = Path(f"tenants/{tenant.tenant_id}")
    if tenant_dir.exists():
        raise HTTPException(status_code=409, detail=f"Tenant '{tenant.tenant_id}' already exists")

    tenant_dir.mkdir(parents=True)
    (tenant_dir / "avatars").mkdir()
    (tenant_dir / "posts").mkdir()

    config = {
        "tenant_id": tenant.tenant_id,
        "display_name": tenant.display_name,
        "avatar_name": tenant.avatar_name,
        "niche": tenant.niche,
        "platforms": tenant.platforms,
        "content_mix": {"educational": 0.40, "opinion": 0.25, "behind_scenes": 0.20, "news_commentary": 0.10, "community": 0.05},
        "posting_schedule": {},
        "brand_color": tenant.brand_color,
        "default_avatar": "avatar.png",
        "cta_style": "follow_and_save",
        "active": True,
    }
    with open(tenant_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    brand = {"name": tenant.display_name, "colors": {"primary": tenant.brand_color}, "hashtags": {"always": [], "niche": []}}
    with open(tenant_dir / "brand.json", "w") as f:
        json.dump(brand, f, indent=2)

    calendar = {"tenant_id": tenant.tenant_id, "weekly_slots": [], "upcoming": []}
    with open(tenant_dir / "calendar.json", "w") as f:
        json.dump(calendar, f, indent=2)

    influencers = {"niche": tenant.niche, "influencers": [], "refresh_schedule": "weekly"}
    with open(tenant_dir / "influencers.json", "w") as f:
        json.dump(influencers, f, indent=2)

    return {"message": f"Tenant '{tenant.tenant_id}' created", "tenant_id": tenant.tenant_id}


# --- Health ---
@app.get("/health")
async def health():
    return {"status": "ok", "service": "contentops-dashboard", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
