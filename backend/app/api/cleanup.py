"""
API routes for cleanup/retention management.
"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.cleanup_service import cleanup_service

router = APIRouter(prefix="/cleanup", tags=["cleanup"])


class RetentionUpdate(BaseModel):
    category: str
    sub_category: Optional[str] = None
    days: float


@router.get("/stats")
async def get_storage_stats():
    """Get current storage usage statistics."""
    return cleanup_service.get_storage_stats()


@router.post("/run")
async def run_cleanup(dry_run: bool = True):
    """
    Run cleanup on all categories.
    
    Args:
        dry_run: If True (default), only report what would be deleted without actually deleting.
    """
    result = cleanup_service.run_full_cleanup(dry_run=dry_run)
    return result


@router.post("/outputs")
async def cleanup_outputs(dry_run: bool = True):
    """Clean up old output files."""
    result = cleanup_service.cleanup_outputs(dry_run=dry_run)
    return result


@router.post("/uploads")
async def cleanup_uploads(dry_run: bool = True):
    """Clean up old uploaded files."""
    result = cleanup_service.cleanup_uploads(dry_run=dry_run)
    return result


@router.post("/logs")
async def cleanup_logs(dry_run: bool = True):
    """Clean up old log files."""
    result = cleanup_service.cleanup_logs(dry_run=dry_run)
    return result


@router.get("/config")
async def get_retention_config():
    """Get current retention configuration."""
    return cleanup_service.retention_config


@router.put("/config")
async def update_retention_config(update: RetentionUpdate):
    """Update retention configuration."""
    if update.sub_category:
        cleanup_service.update_retention_sub(
            update.category, 
            update.sub_category, 
            update.days
        )
    else:
        cleanup_service.update_retention(update.category, update.days)
    
    return {
        "status": "updated",
        "config": cleanup_service.retention_config
    }
