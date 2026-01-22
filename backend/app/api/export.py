"""
API routes for platform-specific video export.
"""
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Video, Job
from app.core.platforms import (
    PlatformType, get_platform_config, validate_video_for_platform,
    get_ffmpeg_args_for_platform, PLATFORM_CONFIGS
)
from app.core.config import settings
from app.services.render_service import render_service

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    video_id: int
    platforms: List[str]  # ["youtube_shorts", "instagram_reels", "tiktok"]


class PlatformValidation(BaseModel):
    platform: str
    valid: bool
    issues: List[str]
    warnings: List[str]


@router.get("/platforms")
async def get_platform_configs():
    """Get configuration for all supported platforms."""
    return {
        platform.value: {
            "name": config.name,
            "resolution": f"{config.width}x{config.height}",
            "aspect_ratio": config.aspect_ratio,
            "max_duration": config.max_duration_seconds,
            "recommended_duration": config.recommended_duration_seconds,
            "max_file_size_mb": config.max_file_size_mb,
            "max_title_length": config.max_title_length,
            "max_description_length": config.max_description_length,
            "max_hashtags": config.max_hashtags,
        }
        for platform, config in PLATFORM_CONFIGS.items()
    }


@router.get("/validate/{video_id}")
async def validate_video(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Validate a video against all platform requirements."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    file_size_mb = video.file_size_bytes / (1024 * 1024)
    
    validations = {}
    for platform in [PlatformType.YOUTUBE_SHORTS, PlatformType.INSTAGRAM_REELS, PlatformType.TIKTOK]:
        result = validate_video_for_platform(
            duration_seconds=video.duration_seconds,
            file_size_mb=file_size_mb,
            platform=platform
        )
        validations[platform.value] = result
    
    # Overall validation
    all_valid = all(v["valid"] for v in validations.values())
    
    return {
        "video_id": video_id,
        "duration_seconds": video.duration_seconds,
        "file_size_mb": round(file_size_mb, 2),
        "all_platforms_valid": all_valid,
        "validations": validations
    }


@router.post("/optimize/{video_id}")
async def optimize_for_platform(
    video_id: int,
    platform: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Re-encode video optimized for a specific platform."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        platform_type = PlatformType(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
    
    config = get_platform_config(platform_type)
    
    # Queue the optimization
    background_tasks.add_task(
        optimize_video_task,
        video_id=video_id,
        platform=platform_type,
        session=session
    )
    
    return {
        "message": f"Video optimization for {config.name} started",
        "video_id": video_id,
        "platform": platform
    }


async def optimize_video_task(video_id: int, platform: PlatformType, session: Session):
    """Background task to optimize video for platform."""
    from app.db import get_sync_session
    
    with get_sync_session() as sync_session:
        video = sync_session.get(Video, video_id)
        if not video:
            return
        
        config = get_platform_config(platform)
        input_path = settings.data_path / video.file_path
        
        # Create output path
        output_dir = input_path.parent / "exports"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_{platform.value}.mp4"
        
        # Build FFmpeg command
        import subprocess
        
        ffmpeg_args = get_ffmpeg_args_for_platform(platform)
        
        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-i", str(input_path),
            "-vf", f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease,pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2",
            *ffmpeg_args,
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            from loguru import logger
            logger.error(f"Platform export failed: {result.stderr}")


@router.get("/downloads/{video_id}")
async def get_export_downloads(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get available export downloads for a video."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    input_path = settings.data_path / video.file_path
    export_dir = input_path.parent / "exports"
    
    downloads = {
        "original": {
            "available": input_path.exists(),
            "path": f"/api/videos/{video_id}/stream",
            "filename": input_path.name
        }
    }
    
    if export_dir.exists():
        for platform in [PlatformType.YOUTUBE_SHORTS, PlatformType.INSTAGRAM_REELS, PlatformType.TIKTOK]:
            export_file = export_dir / f"{input_path.stem}_{platform.value}.mp4"
            downloads[platform.value] = {
                "available": export_file.exists(),
                "path": f"/outputs/{video_id}/exports/{export_file.name}" if export_file.exists() else None,
                "filename": export_file.name if export_file.exists() else None
            }
    
    return downloads
