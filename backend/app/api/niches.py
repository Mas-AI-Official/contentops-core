"""
API routes for niche management.
"""
import json
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Niche, NicheCreate, NicheUpdate, NicheRead, Job
from app.services import topic_service, niche_sync_service
from app.services.scheduler_service import content_scheduler
from app.core.config import settings

router = APIRouter(prefix="/niches", tags=["niches"])


@router.get("/", response_model=List[NicheRead])
async def list_niches(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    session: Session = Depends(get_async_session)
):
    """List all niches."""
    query = select(Niche)
    if active_only:
        query = query.where(Niche.is_active == True)
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{niche_id}", response_model=NicheRead)
async def get_niche(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Get a specific niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    return niche


@router.post("/", response_model=NicheRead, status_code=201)
async def create_niche(
    niche: NicheCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Create a new niche."""
    # Check for duplicate name
    existing = await session.execute(
        select(Niche).where(Niche.name == niche.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Niche with this name already exists")
    
    db_niche = Niche.model_validate(niche)
    session.add(db_niche)
    await session.commit()
    await session.refresh(db_niche)

    # Create niche folder and default topic/feed files
    niche_dir = settings.niches_path / db_niche.name
    niche_dir.mkdir(parents=True, exist_ok=True)
    
    # Seed feeds and trigger scrape in background
    from app.services.scraper_service import scraper_service
    scraper_service.seed_niche_feeds(db_niche.slug, db_niche.name)
    background_tasks.add_task(scraper_service.scrape_niche, db_niche.slug)

    return db_niche


@router.patch("/{niche_id}", response_model=NicheRead)
async def update_niche(
    niche_id: int,
    niche_update: NicheUpdate,
    session: Session = Depends(get_async_session)
):
    """Update a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    update_data = niche_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(niche, key, value)
    
    niche.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(niche)
    return niche


@router.delete("/{niche_id}")
async def delete_niche(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Delete a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    await session.delete(niche)
    await session.commit()
    return {"message": "Niche deleted"}


@router.post("/{niche_id}/generate-topics")
async def generate_topics(
    niche_id: int,
    count: int = 5,
    session: Session = Depends(get_async_session)
):
    """Generate topic ideas for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    topics = await topic_service.get_trending_topics(niche.name, count=count)
    return {"topics": topics}


@router.post("/{niche_id}/toggle-auto-mode")
async def toggle_auto_mode(
    niche_id: int,
    enabled: bool,
    posts_per_day: int = 2,
    session: Session = Depends(get_async_session)
):
    """Enable or disable auto mode for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    # Update database
    niche.auto_mode = enabled
    if enabled:
        niche.posts_per_day = posts_per_day
    niche.updated_at = datetime.utcnow()
    await session.commit()

    # Update disk config
    niche_sync_service.sync_niche_to_disk(niche)

    return {
        "message": f"Auto mode {'enabled' if enabled else 'disabled'} for {niche.name}",
        "auto_mode": enabled,
        "posts_per_day": posts_per_day if enabled else niche.posts_per_day
    }


@router.get("/{niche_slug}/config")
async def get_niche_config(niche_slug: str):
    """Get niche configuration from disk."""
    validation = niche_sync_service.validate_niche_structure(niche_slug)

    if not validation['directory_exists']:
        raise HTTPException(status_code=404, detail="Niche directory not found")

    if not validation['config_exists']:
        raise HTTPException(status_code=404, detail="Niche config not found")

    # Read config file
    config_file = settings.niches_path / niche_slug / "config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")


@router.post("/automate/{niche_id}")
async def automate_niche_pipeline(
    niche_id: int,
    video_count: int = 1,
    publish: bool = False,
    video_model: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Automate the full content pipeline for a niche."""
    from app.workers.job_worker import job_worker

    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    # Generate multiple videos for this niche
    created_jobs = []
    for i in range(video_count):
        # Generate topic
        topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")

        # Create job
        job_data = {
            "niche_id": niche_id,
            "topic": topic,
            "topic_source": "auto",
            "job_type": "generate_and_publish" if publish else "generate_only",
            "video_model": video_model
        }

        job = Job(**job_data)
        session.add(job)
        await session.commit()
        await session.refresh(job)

        created_jobs.append(job)

        # Start processing in background
        if background_tasks:
            background_tasks.add_task(job_worker.process_job, job.id)

    return {
        "message": f"Created {len(created_jobs)} automated jobs for niche '{niche.name}'",
        "jobs": [{"id": job.id, "topic": job.topic} for job in created_jobs],
        "niche_id": niche_id,
        "auto_publish": publish
    }


@router.post("/bulk-automate")
async def bulk_automate_niches(
    niche_ids: List[int],
    videos_per_niche: int = 1,
    publish: bool = False,
    video_model: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Bulk automate content generation across multiple niches."""
    from app.workers.job_worker import job_worker

    all_created_jobs = []
    processed_niches = []

    for niche_id in niche_ids:
        niche = await session.get(Niche, niche_id)
        if not niche:
            continue

        # Generate videos for this niche
        niche_jobs = []
        for i in range(videos_per_niche):
            # Generate topic
            topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")

            # Create job
            job_data = {
                "niche_id": niche_id,
                "topic": topic,
                "topic_source": "bulk_auto",
                "job_type": "generate_and_publish" if publish else "generate_only",
                "video_model": video_model
            }

            job = Job(**job_data)
            session.add(job)
            await session.commit()
            await session.refresh(job)

            niche_jobs.append(job)

            # Start processing in background
            if background_tasks:
                background_tasks.add_task(job_worker.process_job, job.id)

        all_created_jobs.extend(niche_jobs)
        processed_niches.append({
            "id": niche.id,
            "name": niche.name,
            "jobs_created": len(niche_jobs)
        })

    return {
        "message": f"Created {len(all_created_jobs)} jobs across {len(processed_niches)} niches",
        "total_jobs": len(all_created_jobs),
        "niches": processed_niches,
        "jobs": [{"id": job.id, "topic": job.topic, "niche_id": job.niche_id} for job in all_created_jobs],
        "auto_publish": publish
    }


@router.post("/smart-schedule/{niche_id}")
async def smart_schedule_niche(
    niche_id: int,
    platforms: List[str],
    scheduled_date: Optional[date] = None,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_async_session)
):
    """Smart schedule content posting at optimal times."""
    from datetime import datetime

    scheduled_datetime = datetime.combine(
        scheduled_date or datetime.now().date(),
        datetime.min.time()
    ) if scheduled_date else datetime.now()

    result = await content_scheduler.schedule_optimal_posting(
        niche_id=niche_id,
        platforms=platforms,
        scheduled_date=scheduled_datetime
    )

    if result:
        return {
            "message": f"Smart scheduled {result['jobs_created']} jobs for niche {result['niche_id']}",
            "scheduled_date": result["scheduled_date"],
            "jobs_created": result["jobs_created"],
            "platforms": result["platforms"],
            "optimal_times": result["schedule"]
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create smart schedule")


@router.post("/trigger-generation")
async def trigger_generation(niche_ids: Optional[List[int]] = None):
    """Manually trigger content generation for niches."""
    try:
        await content_scheduler.trigger_manual_generation(niche_ids)
        return {"message": "Content generation triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger generation: {e}")


@router.get("/platforms/stats")
async def get_platform_stats():
    """Get statistics for all platforms."""
    with get_sync_session() as session:
        niches = session.exec(select(Niche)).all()

        platforms = {}
        for niche in niches:
            platform = niche.platform or "youtube"
            if platform not in platforms:
                platforms[platform] = {
                    "total_niches": 0,
                    "active_niches": 0,
                    "total_posts_per_day": 0,
                    "niches": []
                }

            platforms[platform]["total_niches"] += 1
            if niche.auto_mode:
                platforms[platform]["active_niches"] += 1
                platforms[platform]["total_posts_per_day"] += niche.posts_per_day or 0

            platforms[platform]["niches"].append({
                "id": niche.id,
                "name": niche.name,
                "auto_mode": niche.auto_mode,
                "posts_per_day": niche.posts_per_day or 0,
                "account_name": niche.account_name,
                "posting_schedule": niche.posting_schedule or []
            })

        return platforms
