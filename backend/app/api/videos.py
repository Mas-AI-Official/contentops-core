"""
API routes for video library management.
"""
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Video, VideoRead, VideoPublish
from app.core.config import settings

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/", response_model=List[VideoRead])
async def list_videos(
    skip: int = 0,
    limit: int = 50,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """List all videos with optional filters."""
    query = select(Video)
    
    if niche_id:
        query = query.where(Video.niche_id == niche_id)
    
    query = query.order_by(Video.created_at.desc()).offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get a specific video."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Stream a video file."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_path = settings.data_path / video.file_path
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=video_path.name
    )


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get video thumbnail."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    thumbnail_path = settings.data_path / video.thumbnail_path
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    
    return FileResponse(
        path=thumbnail_path,
        media_type="image/jpeg"
    )


@router.get("/{video_id}/publishes")
async def get_video_publishes(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get publish records for a video."""
    result = await session.execute(
        select(VideoPublish).where(VideoPublish.video_id == video_id)
    )
    publishes = result.scalars().all()
    
    return [
        {
            "platform": p.platform,
            "status": p.status,
            "video_id": p.platform_video_id,
            "url": p.platform_url,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "error": p.error_message
        }
        for p in publishes
    ]


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    delete_files: bool = False,
    session: Session = Depends(get_async_session)
):
    """Delete a video record (optionally delete files)."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if delete_files:
        # Delete video file
        video_path = settings.data_path / video.file_path
        if video_path.exists():
            video_path.unlink()
        
        # Delete thumbnail
        if video.thumbnail_path:
            thumb_path = settings.data_path / video.thumbnail_path
            if thumb_path.exists():
                thumb_path.unlink()
    
    await session.delete(video)
    await session.commit()
    return {"message": "Video deleted"}


@router.get("/{video_id}/metadata")
async def get_video_metadata(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get full metadata for a video (for export/manual upload)."""
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {
        "title": video.title,
        "description": video.description,
        "topic": video.topic,
        "duration": video.duration_seconds,
        "tags": video.tags,
        "hashtags": video.hashtags,
        "file_path": str(settings.data_path / video.file_path),
        "thumbnail_path": str(settings.data_path / video.thumbnail_path) if video.thumbnail_path else None,
        "created_at": video.created_at.isoformat()
    }
