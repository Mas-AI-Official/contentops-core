"""
API routes for the Content Factory.
"""
from fastapi import APIRouter

from .niches import router as niches_router
from .accounts import router as accounts_router
from .jobs import router as jobs_router
from .videos import router as videos_router
from .analytics import router as analytics_router
from .generator import router as generator_router
from .settings import router as settings_router
from .models import router as models_router
from .scripts import router as scripts_router
from .export import router as export_router
from .mcp import router as mcp_router

api_router = APIRouter(prefix="/api")

api_router.include_router(niches_router)
api_router.include_router(accounts_router)
api_router.include_router(jobs_router)
api_router.include_router(videos_router)
api_router.include_router(analytics_router)
api_router.include_router(generator_router)
api_router.include_router(settings_router)
api_router.include_router(models_router)
api_router.include_router(scripts_router)
api_router.include_router(export_router)
api_router.include_router(mcp_router)

__all__ = ["api_router"]
