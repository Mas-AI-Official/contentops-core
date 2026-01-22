"""
API routes for job management.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Job, JobCreate, JobUpdate, JobRead, JobLog, JobStatus, JobType
from app.workers import run_job_now

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[JobStatus] = None,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """List all jobs with optional filters."""
    query = select(Job)
    
    if status:
        query = query.where(Job.status == status)
    if niche_id:
        query = query.where(Job.niche_id == niche_id)
    
    query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/today")
async def get_todays_jobs(
    session: Session = Depends(get_async_session)
):
    """Get summary of today's jobs."""
    today = datetime.utcnow().date()
    
    result = await session.execute(select(Job))
    jobs = result.scalars().all()
    
    # Filter to today's jobs
    today_jobs = [j for j in jobs if j.created_at.date() == today]
    
    return {
        "total": len(today_jobs),
        "pending": len([j for j in today_jobs if j.status == JobStatus.PENDING]),
        "completed": len([j for j in today_jobs if j.status in [JobStatus.READY_FOR_REVIEW, JobStatus.PUBLISHED]]),
        "failed": len([j for j in today_jobs if j.status == JobStatus.FAILED]),
        "in_progress": len([j for j in today_jobs if j.status not in [JobStatus.PENDING, JobStatus.READY_FOR_REVIEW, JobStatus.PUBLISHED, JobStatus.FAILED, JobStatus.CANCELLED]]),
    }


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Get a specific job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/", response_model=JobRead, status_code=201)
async def create_job(
    job: JobCreate,
    run_immediately: bool = False,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Create a new job."""
    db_job = Job.model_validate(job)
    session.add(db_job)
    await session.commit()
    await session.refresh(db_job)
    
    if run_immediately and background_tasks:
        background_tasks.add_task(run_job_now, db_job.id)
    
    return db_job


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    session: Session = Depends(get_async_session)
):
    """Update a job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    
    job.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(job)
    return job


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Delete a job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await session.delete(job)
    await session.commit()
    return {"message": "Job deleted"}


@router.post("/{job_id}/run")
async def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Run a specific job immediately."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.PENDING, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Job is not in a runnable state")
    
    # Reset status if failed
    if job.status == JobStatus.FAILED:
        job.status = JobStatus.PENDING
        job.error_message = None
        await session.commit()
    
    background_tasks.add_task(run_job_now, job_id)
    return {"message": "Job queued for execution"}


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Retry a failed job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
    
    job.status = JobStatus.PENDING
    job.error_message = None
    job.progress_percent = 0
    await session.commit()
    
    background_tasks.add_task(run_job_now, job_id)
    return {"message": "Job queued for retry"}


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Cancel a pending job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled in current state")
    
    job.status = JobStatus.CANCELLED
    await session.commit()
    return {"message": "Job cancelled"}


@router.post("/{job_id}/approve")
async def approve_job(
    job_id: int,
    publish: bool = True,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Approve a generated video and optionally publish."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.READY_FOR_REVIEW:
        raise HTTPException(status_code=400, detail="Job is not ready for approval")
    
    job.status = JobStatus.APPROVED
    await session.commit()
    
    if publish and background_tasks:
        # Create a publish job
        job.job_type = JobType.PUBLISH_EXISTING
        job.status = JobStatus.PENDING
        await session.commit()
        background_tasks.add_task(run_job_now, job_id)
    
    return {"message": "Job approved" + (" and queued for publishing" if publish else "")}


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Get logs for a specific job."""
    result = await session.execute(
        select(JobLog)
        .where(JobLog.job_id == job_id)
        .order_by(JobLog.timestamp)
    )
    logs = result.scalars().all()
    
    return [
        {
            "timestamp": log.timestamp.isoformat(),
            "level": log.level,
            "message": log.message,
            "details": log.details
        }
        for log in logs
    ]
