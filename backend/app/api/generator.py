"""
API routes for the video generator (test/preview functionality).
"""
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Niche, Job, JobCreate, JobType, JobStatus
from app.services import topic_service, script_service
from app.workers import run_job_now
from app.core.config import settings

router = APIRouter(prefix="/generator", tags=["generator"])


class GeneratePreviewRequest(BaseModel):
    niche_id: int
    topic: Optional[str] = None
    custom_script: Optional[str] = None


class ScriptPreviewRequest(BaseModel):
    niche_id: int
    topic: str


@router.post("/topic")
async def generate_topic(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Generate a topic for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    topic = await topic_service.generate_topic(niche.name, niche.description or "")
    return {"topic": topic}


@router.post("/script")
async def generate_script_preview(
    request: ScriptPreviewRequest,
    session: Session = Depends(get_async_session)
):
    """Generate a script preview without creating a full job."""
    niche = await session.get(Niche, request.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    script = await script_service.generate_script(
        topic=request.topic,
        prompt_hook=niche.prompt_hook,
        prompt_body=niche.prompt_body,
        prompt_cta=niche.prompt_cta,
        target_duration=niche.max_duration_seconds,
        style=niche.style.value
    )
    
    return {
        "topic": request.topic,
        "hook": script.hook,
        "body": script.body,
        "cta": script.cta,
        "full_script": script.full_script,
        "estimated_duration": script.estimated_duration
    }


@router.post("/video")
async def generate_test_video(
    request: GeneratePreviewRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Generate a test video (creates a job and runs it)."""
    niche = await session.get(Niche, request.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    # Generate topic if not provided
    topic = request.topic
    if not topic:
        topic = await topic_service.generate_topic(niche.name, niche.description or "")
    
    # Create job
    job = Job(
        niche_id=request.niche_id,
        job_type=JobType.GENERATE_ONLY,
        topic=topic,
        topic_source="generator_preview"
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    
    # Run the job
    background_tasks.add_task(run_job_now, job.id)
    
    return {
        "job_id": job.id,
        "topic": topic,
        "message": "Video generation started. Check job status for progress."
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
