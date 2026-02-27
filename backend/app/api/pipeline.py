from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/status")
async def get_pipeline_status():
    from app.api.diagnostics import check_pipeline_health

    health = await check_pipeline_health()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "autopilot_enabled": settings.autopilot_enabled,
        "worker_enabled": settings.worker_enabled,
        "worker_interval_seconds": settings.worker_interval_seconds,
        "pipeline": health,
    }
