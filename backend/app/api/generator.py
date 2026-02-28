"""
API routes for the video generator (test/preview functionality).
"""
import base64
import json
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Niche, Job, JobCreate, JobType, JobStatus
from app.services import topic_service, script_service, scraper_service, trend_service
from app.workers import run_job_now
from app.core.config import settings

router = APIRouter(prefix="/generator", tags=["generator"])


class GeneratePreviewRequest(BaseModel):
    niche_id: int
    topic: Optional[str] = None
    custom_script: Optional[str] = None
    video_name: Optional[str] = None  # Display name / title for the video (manual mode)
    topic_source: Optional[str] = "auto"  # auto, rss, list, llm, trending
    video_model: Optional[str] = None
    platform_format: Optional[str] = "9:16"  # 9:16 | 16:9 | 1:1
    character_description: Optional[str] = None
    start_frame_base64: Optional[str] = None
    start_frame_filename: Optional[str] = None
    end_frame_base64: Optional[str] = None
    end_frame_filename: Optional[str] = None
    scenes: Optional[List[str]] = None  # Optional scene order/prompts; if omitted, auto from script/LLM
    voice_id: Optional[str] = None  # XTTS speaker wav path or ElevenLabs voice id; overrides niche default
    voice_name: Optional[str] = None  # Display name (e.g. Daena)
    count: int = 1  # Number of videos to generate (1, 2, or 3) in one go
    target_duration_seconds: Optional[int] = None  # 20, 30, 60, 90, 120 etc.; overrides niche max


class ScriptPreviewRequest(BaseModel):
    niche_id: int
    topic: str
    character_description: Optional[str] = None


@router.post("/topic")
async def generate_topic(
    niche_id: int,
    source: str = "auto",
    session: Session = Depends(get_async_session)
):
    """Generate a topic for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    if source == "trending":
        # Get trending topics relevant to niche
        keywords = [niche.name]
        if niche.keywords:
            keywords.extend([k.strip() for k in niche.keywords.split(",") if k.strip()])
            
        trends = await trend_service.get_niche_trends(keywords)
        
        if trends:
            # Pick the top trend
            trend = trends[0]
            topic = trend.get("topic", "")
            return {"topic": topic, "source": "trending", "data": trend}
        else:
            # Fallback
            topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")
            return {"topic": topic, "source": "trending_fallback"}

    if source == "rss":
        # Get unused topic from scraper service
        # Use niche name as slug (or better, store slug in DB, but name usually works for directory lookup)
        niche_slug = niche.name  
        topic_data = scraper_service.get_unused_topic(niche_slug)
        
        if topic_data:
            topic = topic_data.get("title", "")
            # Mark as used immediately for generator preview? 
            # Maybe better to wait until video is generated, but for now let's just pick it.
            # We won't mark it used yet so user can regenerate if they don't like it.
            return {"topic": topic, "source": "rss", "data": topic_data}
        else:
            # Fallback to auto if no RSS topics found
            topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")
            return {"topic": topic, "source": "rss_fallback"}

    if source == "list":
        topic = topic_service.select_from_list(niche.name)
        if not topic:
            topic = await topic_service.generate_topic(niche.name, niche.description or "")
            source = "llm"
        return {"topic": topic, "source": source}
    if source == "llm":
        topic = await topic_service.generate_topic(niche.name, niche.description or "")
        return {"topic": topic, "source": "llm"}

    topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")
    return {"topic": topic, "source": "auto"}


@router.post("/script")
async def generate_script_preview(
    request: ScriptPreviewRequest,
    session: Session = Depends(get_async_session)
):
    """Generate a script preview without creating a full job."""
    niche = await session.get(Niche, request.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    script = await script_service.generate_with_niche_config(
        topic=request.topic,
        niche=niche,
        target_duration=niche.max_duration_seconds,
        character_description=request.character_description,
    )
    return {
        "topic": request.topic,
        "hook": script.hook,
        "body": script.body,
        "cta": script.cta,
        "full_script": script.full_script,
        "estimated_duration": script.estimated_duration,
        "visual_cues": script.visual_cues,
    }


def _create_one_job(session, request: GeneratePreviewRequest, niche: Niche, topic: str, index: int, total: int):
    """Create a single job from request; topic may be suffixed for batch (e.g. 'Title (2/3)')."""
    job_topic = topic if total <= 1 else f"{topic} ({index + 1}/{total})"
    job = Job(
        niche_id=request.niche_id,
        job_type=JobType.GENERATE_ONLY,
        topic=job_topic,
        topic_source="generator_preview",
        video_model=request.video_model,
        platform_format=request.platform_format or "9:16",
        character_description=request.character_description,
    )
    if request.custom_script and request.custom_script.strip():
        job.full_script = request.custom_script.strip()
    if request.scenes and len(request.scenes) > 0:
        job.visual_cues = json.dumps([s.strip() for s in request.scenes if s and s.strip()])
    if request.voice_id and request.voice_id.strip():
        job.voice_id = request.voice_id.strip()
    if request.voice_name and request.voice_name.strip():
        job.voice_name = request.voice_name.strip()
    if getattr(request, "target_duration_seconds", None) is not None and request.target_duration_seconds > 0:
        job.target_duration_seconds = min(600, max(15, request.target_duration_seconds))
    session.add(job)
    session.flush()
    return job


@router.post("/video")
async def generate_test_video(
    request: GeneratePreviewRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Generate one or more test videos (creates job(s) and runs them). Use count=2 or 3 for batch."""
    niche = await session.get(Niche, request.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    count = max(1, min(5, getattr(request, "count", 1)))
    
    # Topic (used as job/video title): video_name for manual, then topic, then fallback
    topic = request.video_name and request.video_name.strip() or request.topic
    if not topic and request.custom_script:
        topic = "Manual script"
    if not topic:
        topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")
    
    job_ids = []
    for i in range(count):
        job = _create_one_job(session, request, niche, topic, i, count)
        await session.commit()
        await session.refresh(job)
        job_ids.append(job.id)

        data_path = Path(settings.data_path)
        jobs_dir = data_path / "jobs"
        job_dir = jobs_dir / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = job_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        if request.start_frame_base64 and request.start_frame_filename:
            try:
                raw = base64.b64decode(request.start_frame_base64)
                ext = Path(request.start_frame_filename).suffix or ".png"
                start_path = assets_dir / f"start_frame{ext}"
                start_path.write_bytes(raw)
                job.start_frame_path = str(start_path.relative_to(data_path))
                session.add(job)
                await session.commit()
            except Exception:
                pass
        if request.end_frame_base64 and request.end_frame_filename:
            try:
                raw = base64.b64decode(request.end_frame_base64)
                ext = Path(request.end_frame_filename).suffix or ".png"
                end_path = assets_dir / f"end_frame{ext}"
                end_path.write_bytes(raw)
                job.end_frame_path = str(end_path.relative_to(data_path))
                session.add(job)
                await session.commit()
            except Exception:
                pass

        background_tasks.add_task(run_job_now, job.id)
    
    return {
        "job_id": job_ids[0],
        "job_ids": job_ids,
        "topic": topic,
        "count": len(job_ids),
        "message": f"{len(job_ids)} video(s) queued. Check Queue for progress." if len(job_ids) > 1 else "Video generation started. Check job status for progress."
    }


@router.get("/status/{job_id}")
async def get_generation_status(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Get the status of a generation job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress_percent,
        "topic": job.topic,
        "error": job.error_message
    }
    
    if job.status == JobStatus.READY_FOR_REVIEW and job.video_path:
        result["video_path"] = job.video_path
        result["preview_url"] = f"/api/generator/preview/{job.id}"
    
    if job.full_script:
        result["script"] = job.full_script
    
    return result


@router.get("/preview/{job_id}")
async def preview_video(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Stream the preview video for a completed job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.video_path:
        raise HTTPException(status_code=404, detail="Video not yet generated")
    
    video_path = settings.data_path / job.video_path
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"preview_{job_id}.mp4"
    )


@router.post("/approve/{job_id}")
async def approve_and_publish(
    job_id: int,
    platforms: list = ["youtube", "instagram", "tiktok"],
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Approve a preview video and publish to selected platforms."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.READY_FOR_REVIEW:
        raise HTTPException(status_code=400, detail="Job is not ready for approval")
    
    # Update job for publishing
    job.job_type = JobType.PUBLISH_EXISTING
    job.status = JobStatus.PENDING
    job.publish_youtube = "youtube" in platforms
    job.publish_instagram = "instagram" in platforms
    job.publish_tiktok = "tiktok" in platforms
    
    await session.commit()
    
    # Queue for publishing
    if background_tasks:
        background_tasks.add_task(run_job_now, job_id)
    
    return {
        "message": "Video approved and queued for publishing",
        "platforms": platforms
    }


@router.get("/assets/{niche_id}")
async def get_niche_assets(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Get available assets for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    from app.services import visual_service
    manifest = visual_service.create_asset_manifest(niche.name)
    
    return manifest
