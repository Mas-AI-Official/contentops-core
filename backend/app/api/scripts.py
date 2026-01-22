"""
API routes for script management and browsing.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

from app.services.script_storage import script_storage
from app.core.config import settings

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("/")
async def list_scripts(
    niche: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """List stored scripts with optional filters."""
    if date:
        scripts = script_storage.get_scripts_by_date(niche_name=niche, date_str=date)
    else:
        scripts = script_storage.get_recent_scripts(limit=limit, niche_name=niche)
    
    return {"scripts": scripts[:limit], "total": len(scripts)}


@router.get("/stats")
async def get_scripts_stats():
    """Get statistics about stored scripts."""
    return script_storage.get_scripts_stats()


@router.get("/by-path")
async def get_script_by_path(path: str):
    """Get a specific script by its storage path."""
    script = script_storage.get_script(path)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.get("/download/{job_id}")
async def download_script(job_id: int, format: str = "txt"):
    """Download a script file."""
    # Find script by job_id
    all_scripts = script_storage.get_scripts_by_date()
    script_info = next((s for s in all_scripts if s.get("job_id") == job_id), None)
    
    if not script_info:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_path = Path(script_info["path"])
    
    if format == "json":
        file_path = script_path / "script.json"
    else:
        file_path = script_path / "script.txt"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Script file not found")
    
    return FileResponse(
        path=file_path,
        filename=f"script_{job_id}.{format}",
        media_type="application/json" if format == "json" else "text/plain"
    )


@router.get("/dates")
async def get_available_dates(niche: Optional[str] = None):
    """Get list of dates that have scripts."""
    stats = script_storage.get_scripts_stats()
    dates = sorted(stats.get("by_date", {}).keys(), reverse=True)
    
    return {"dates": dates}


@router.get("/niches")
async def get_script_niches():
    """Get list of niches that have scripts."""
    stats = script_storage.get_scripts_stats()
    return {"niches": list(stats.get("by_niche", {}).keys())}
