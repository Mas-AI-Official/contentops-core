"""
Scheduler Service
Manages automated content generation using APScheduler
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import List, Optional
import json
from pathlib import Path
from loguru import logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.core.config import settings
from app.db import get_sync_session
from app.models import Niche, Job, JobCreate, JobStatus, JobType
from app.services.topic_service import topic_service
from app.services.growth_engine_service import growth_engine
from app.services.smart_scheduler import smart_scheduler
from app.services.scraper_service import scraper_service


class ContentScheduler:
    """Automated content generation scheduler."""

    def __init__(self):
        self.scheduler = None
        self._is_running = False

    def initialize(self):
        """Initialize the scheduler."""
        if self.scheduler:
            return

        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 3,
            'misfire_grace_time': 30
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        logger.info("Content scheduler initialized")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler:
            self.initialize()

        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Content scheduler started")

            # Schedule daily content generation
            self._schedule_daily_generation()
            
            # Schedule RSS scraping (every 3 hours)
            self.scheduler.add_job(
                func=self._scrape_rss_feeds,
                trigger=CronTrigger(minute=0, hour="*/3"),
                id="rss_scraping",
                name="RSS Feed Scraping",
                replace_existing=True
            )
            logger.info("Scheduled RSS scraping every 3 hours")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self._is_running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Content scheduler stopped")

    async def _scrape_rss_feeds(self):
        """Scrape RSS feeds for all niches."""
        logger.info("Starting scheduled RSS scraping...")
        try:
            result = await scraper_service.scrape_all_niches()
            logger.info(f"RSS scraping completed: {result.get('niches_processed', 0)} niches processed")
        except Exception as e:
            logger.error(f"Scheduled RSS scraping failed: {e}")

    def _schedule_daily_generation(self):
        """Schedule daily content generation for all niches."""
        # Clear existing jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("niche_"):
                self.scheduler.remove_job(job.id)

        # Get all niches with auto mode enabled and schedule them individually
        with get_sync_session() as session:
            active_niches = session.query(Niche).filter(Niche.auto_mode == True).all()

            for niche in active_niches:
                schedule = niche.posting_schedule or ["09:00", "19:00"]

                for time_str in schedule:
                    try:
                        # Parse time string (HH:MM format)
                        hour, minute = map(int, time_str.split(':'))

                        self.scheduler.add_job(
                            func=self._generate_niche_content,
                            args=[niche, {'posts_per_day': niche.posts_per_day or 2}],
                            trigger=CronTrigger(hour=hour, minute=minute),
                            id=f"niche_{niche.id}_{time_str.replace(':', '')}",
                            name=f"{niche.name} - {time_str} UTC",
                            replace_existing=True
                        )

                        logger.debug(f"Scheduled {niche.name} for {time_str} UTC")

                    except (ValueError, IndexError) as e:
                        logger.error(f"Invalid time format '{time_str}' for niche {niche.name}: {e}")

        total_jobs = len([j for j in self.scheduler.get_jobs() if j.id.startswith("niche_")])
        logger.info(f"Scheduled content generation for {len(active_niches)} niches ({total_jobs} total jobs)")

    async def _generate_daily_content(self):
        """Legacy method - kept for compatibility. Now uses individual niche scheduling."""
        logger.info("Legacy _generate_daily_content called - use individual niche scheduling")

    async def _generate_niche_content(self, niche: Niche, config: dict):
        """Generate content for a specific niche using growth engine."""
        posts_per_day = config.get('posts_per_day', 2)
        logger.info(f"Generating {posts_per_day} posts for niche: {niche.name}")

        # Get daily content plan from growth engine
        content_plan = growth_engine.create_daily_content_plan(niche, posts_per_day)

        # Generate topics and create jobs based on plan
        for plan_item in content_plan:
            try:
                # Use growth engine to generate topic based on template
                template = plan_item['template']
                base_topic = plan_item['idea']

                # Generate more specific topic if needed
                if template.get('type') == 'health_tips':
                    # Use the hook as the topic for health tips
                    topic = base_topic
                else:
                    # Generate additional topic variation
                    topic = await topic_service.generate_topic_auto(niche.name, niche.description or "")
                    if not topic:
                        topic = base_topic

                # Create job with template metadata
                job_data = JobCreate(
                    niche_id=niche.id,
                    topic=topic,
                    topic_source="auto_growth_engine",
                    job_type=JobType.GENERATE_AND_PUBLISH,
                    publish_youtube=niche.post_to_youtube,
                    publish_instagram=niche.post_to_instagram,
                    publish_tiktok=niche.post_to_tiktok,
                    status=JobStatus.PENDING
                )

                job = Job.model_validate(job_data)

                # Add template metadata to job
                job.description = json.dumps({
                    'template': template,
                    'is_experiment': plan_item['is_experiment'],
                    'growth_engine_slot': plan_item['slot']
                })

                with get_sync_session() as session:
                    session.add(job)
                    session.commit()
                    session.refresh(job)

                    experiment_indicator = " [EXPERIMENT]" if plan_item['is_experiment'] else " [PROVEN]"
                    logger.info(f"Created auto job {job.id} for niche {niche.name}{experiment_indicator}: {topic[:50]}...")

            except Exception as e:
                logger.error(f"Failed to create job for niche {niche.name}: {e}")

    def get_scheduler_status(self) -> dict:
        """Get scheduler status and job information."""
        if not self.scheduler:
            return {"status": "not_initialized"}

        jobs = []
        if hasattr(self.scheduler, 'get_jobs'):
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })

        return {
            "status": "running" if self._is_running else "stopped",
            "jobs": jobs,
            "job_count": len(jobs)
        }

    async def trigger_manual_generation(self, niche_ids: Optional[List[int]] = None):
        """Manually trigger content generation for specific niches or all auto-enabled niches."""
        logger.info("Manual content generation triggered")

        try:
            with get_sync_session() as session:
                if niche_ids:
                    niches = session.query(Niche).filter(Niche.id.in_(niche_ids)).all()
                    logger.info(f"Generating content for specific niches: {[n.name for n in niches]}")
                else:
                    niches = session.query(Niche).filter(Niche.auto_mode == True).all()
                    logger.info(f"Generating content for all auto-enabled niches: {[n.name for n in niches]}")

                # Generate content for each niche
                for niche in niches:
                    try:
                        config = {'posts_per_day': niche.posts_per_day or 2}
                        # Load additional config from file
                        config_file = settings.niches_path / niche.slug / "config.json"
                        if config_file.exists():
                            try:
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    file_config = json.load(f)
                                    config.update(file_config)
                            except Exception as e:
                                logger.error(f"Failed to read config for niche {niche.name}: {e}")

                        await self._generate_niche_content(niche, config)
                    except Exception as e:
                        logger.error(f"Failed to generate content for niche {niche.name}: {e}")

        except Exception as e:
            logger.error(f"Manual content generation failed: {e}")

    async def schedule_optimal_posting(
        self,
        niche_id: int,
        platforms: List[str],
        scheduled_date: Optional[datetime] = None
    ):
        """Schedule content posting at optimal times for the given platforms."""
        if scheduled_date is None:
            scheduled_date = datetime.now()

        logger.info(f"Scheduling optimal posting for niche {niche_id} on platforms: {platforms}")

        try:
            with get_sync_session() as session:
                niche = session.query(Niche).filter(Niche.id == niche_id).first()
                if not niche:
                    logger.error(f"Niche {niche_id} not found")
                    return

                # Get existing schedules for the day to avoid conflicts
                existing_jobs = session.query(Job).filter(
                    Job.niche_id == niche_id,
                    Job.scheduled_at >= scheduled_date.replace(hour=0, minute=0, second=0),
                    Job.scheduled_at < (scheduled_date + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                ).all()

                existing_times = {}
                for job in existing_jobs:
                    if job.scheduled_at:
                        for platform in platforms:
                            if platform not in existing_times:
                                existing_times[platform] = []
                            existing_times[platform].append(job.scheduled_at)

                # Get optimal schedule
                optimal_schedule = smart_scheduler.schedule_content_for_day(
                    platforms=platforms,
                    date=scheduled_date,
                    existing_schedules=existing_times
                )

                # Create jobs at optimal times
                created_jobs = []
                for platform, posting_times in optimal_schedule.items():
                    for posting_time in posting_times:
                        scheduled_datetime = posting_time.to_datetime(scheduled_date)

                        # Create job
                        job_data = {
                            "niche_id": niche_id,
                            "topic": f"Auto-scheduled content for {platform}",
                            "topic_source": "auto_schedule",
                            "job_type": JobType.GENERATE_AND_PUBLISH,
                            "scheduled_at": scheduled_datetime,
                            "publish_youtube": platform == "youtube",
                            "publish_instagram": platform == "instagram",
                            "publish_tiktok": platform == "tiktok"
                        }

                        job = Job.model_validate(job_data)
                        session.add(job)
                        session.commit()
                        session.refresh(job)

                        created_jobs.append(job)
                        logger.info(f"Scheduled job {job.id} for {platform} at {scheduled_datetime}")

                return {
                    "niche_id": niche_id,
                    "scheduled_date": scheduled_date.isoformat(),
                    "jobs_created": len(created_jobs),
                    "platforms": platforms,
                    "schedule": optimal_schedule
                }

        except Exception as e:
            logger.error(f"Failed to schedule optimal posting: {e}")
            return None


# Global scheduler instance
content_scheduler = ContentScheduler()