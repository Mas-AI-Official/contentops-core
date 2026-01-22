"""
Compatibility endpoints for external tools expecting /api/v1 routes.
"""
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["compat"])


@router.get("/brain/status")
async def brain_status():
    return {
        "status": "ok",
        "app": settings.app_name,
        "time": datetime.utcnow().isoformat()
    }


@router.get("/agents/")
async def list_agents():
    return {"agents": []}


@router.get("/voice/status")
async def voice_status():
    return {
        "tts_provider": settings.tts_provider,
        "xtts_enabled": settings.xtts_enabled
    }


@router.get("/tasks/stats/overview")
async def tasks_overview():
    return {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0
    }


@router.get("/system/status")
async def system_status():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "time": datetime.utcnow().isoformat()
    }


@router.get("/projects/")
async def projects_list():
    return {"projects": []}


@router.get("/council/list")
async def council_list():
    return {"council": []}


@router.post("/chat-history/sessions")
async def create_chat_session():
    return {
        "session_id": str(uuid4()),
        "created_at": datetime.utcnow().isoformat()
    }
