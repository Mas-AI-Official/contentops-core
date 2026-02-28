"""
Job worker - processes video generation jobs.
Uses APScheduler for scheduling and multiprocessing for parallel execution.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
from sqlmodel import Session, select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db import get_sync_session, sync_engine
from app.models import Job, JobStatus, JobType, JobLog, Niche, Video, VideoPublish
from app.services import (
    topic_service, script_service, tts_service,
    visual_service, subtitle_service, render_service,
    publish_service, RenderConfig
)
from app.services.script_storage import script_storage


class JobWorker:
    """Worker that processes video generation jobs."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running = False
        self.current_job_id: Optional[int] = None
    
    def start(self):
        """Start the job worker."""
        if self.running:
            return
        
        self.scheduler.add_job(
            self._process_pending_jobs,
            IntervalTrigger(seconds=settings.worker_interval_seconds),
            id="job_processor",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self._process_scheduled_jobs,
            IntervalTrigger(minutes=1),
            id="scheduled_processor",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.running = True
        logger.info("Job worker started")
    
    def stop(self):
        """Stop the job worker."""
        if not self.running:
            return
        
        self.scheduler.shutdown()
        self.running = False
        logger.info("Job worker stopped")
    
    async def _process_pending_jobs(self):
        """Process pending jobs from the queue."""
        
        with get_sync_session() as session:
            # Get pending jobs
            jobs = session.exec(
                select(Job)
                .where(Job.status == JobStatus.PENDING)
                .where(Job.scheduled_at == None)
                .order_by(Job.created_at)
                .limit(settings.max_concurrent_jobs)
            ).all()
            
            for job in jobs:
                await self._process_job(job.id)
    
    async def _process_scheduled_jobs(self):
        """Process scheduled jobs that are due."""
        
        with get_sync_session() as session:
            now = datetime.utcnow()
            jobs = session.exec(
                select(Job)
                .where(Job.status == JobStatus.PENDING)
                .where(Job.scheduled_at != None)
                .where(Job.scheduled_at <= now)
                .order_by(Job.scheduled_at)
            ).all()
            
            for job in jobs:
                await self._process_job(job.id)
    
    async def _process_job(self, job_id: int):
        """Process a single job."""
        
        self.current_job_id = job_id
        
        with get_sync_session() as session:
            job = session.get(Job, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            niche = session.get(Niche, job.niche_id)
            if not niche:
                self._fail_job(session, job, "Niche not found")
                return
            
            try:
                # Update status
                job.status = JobStatus.QUEUED
                job.started_at = datetime.utcnow()
                session.commit()
                
                self._log(session, job_id, "INFO", "Job processing started")
                
                # Generate or use existing content based on job type
                if job.job_type in [JobType.GENERATE_ONLY, JobType.GENERATE_AND_PUBLISH]:
                    await self._generate_video(session, job, niche)
                
                # Publish if requested
                if job.job_type in [JobType.GENERATE_AND_PUBLISH, JobType.PUBLISH_EXISTING]:
                    await self._publish_video(session, job, niche)
                
                # Mark complete
                job.status = JobStatus.READY_FOR_REVIEW if job.job_type == JobType.GENERATE_ONLY else JobStatus.PUBLISHED
                job.completed_at = datetime.utcnow()
                job.progress_percent = 100
                session.commit()
                
                self._log(session, job_id, "INFO", "Job completed successfully")
                
            except Exception as e:
                logger.exception(f"Job {job_id} failed")
                self._fail_job(session, job, str(e))
        
        self.current_job_id = None
    
    async def _generate_video(self, session: Session, job: Job, niche: Niche):
        """Generate video content."""
        
        job_id = job.id
        outputs_dir = settings.outputs_path / str(job_id)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Generate script (or use existing full_script from manual prompt)
        job.status = JobStatus.GENERATING_SCRIPT
        job.progress_percent = 10
        session.commit()
        
        if job.full_script and job.full_script.strip():
            self._log(session, job_id, "INFO", "Using manual script (no LLM expansion)")
            script_hook = ""
            script_body = job.full_script.strip()
            script_cta = ""
            script_full = job.full_script.strip()
            word_count = len(script_full.split())
            estimated_duration = max(30, int((word_count / 150) * 60))
            script_storage.save_script(
                job_id=job_id,
                niche_name=niche.name,
                topic=job.topic,
                script_data={
                    "hook": script_hook,
                    "body": script_body,
                    "cta": script_cta,
                    "full_script": script_full,
                    "estimated_duration": estimated_duration
                },
                metadata={"niche_id": niche.id, "manual_script": True}
            )
            job.script_hook = script_hook
            job.script_body = script_body
            job.script_cta = script_cta
            session.commit()
        else:
            self._log(session, job_id, "INFO", "Generating script...")
            target_sec = getattr(job, "target_duration_seconds", None) or niche.max_duration_seconds
            script = await script_service.generate_with_niche_config(
                topic=job.topic,
                niche=niche,
                target_duration=target_sec,
                character_description=getattr(job, "character_description", None),
            )
            job.script_hook = script.hook
            job.script_body = script.body
            job.script_cta = script.cta
            job.full_script = script.full_script
            if getattr(script, "visual_cues", None):
                job.visual_cues = script.visual_cues
            session.commit()
            script_storage.save_script(
                job_id=job_id,
                niche_name=niche.name,
                topic=job.topic,
                script_data={
                    "hook": script.hook,
                    "body": script.body,
                    "cta": script.cta,
                    "full_script": script.full_script,
                    "estimated_duration": script.estimated_duration
                },
                metadata={
                    "niche_id": niche.id,
                    "style": niche.style.value,
                    "prompts": {
                        "hook": niche.prompt_hook,
                        "body": niche.prompt_body,
                        "cta": niche.prompt_cta
                    }
                }
            )
            script_full = script.full_script
            self._log(session, job_id, "INFO", f"Script generated and saved: {len(script.full_script)} chars")
        
        # Optional: set short bullet-style caption from script (for library/social)
        if job.full_script and not getattr(job, "caption", None):
            import re
            sentences = re.split(r"[.!?]+", job.full_script.strip())
            sentences = [s.strip() for s in sentences if s.strip()][:3]
            if sentences:
                job.caption = " • ".join(sentences)[:400]
                session.add(job)
                session.commit()

        # Step 2: Generate audio
        job.status = JobStatus.GENERATING_AUDIO
        job.progress_percent = 30
        session.commit()
        self._log(session, job_id, "INFO", "Generating audio...")
        
        audio_path = outputs_dir / "narration.wav"
        await tts_service.generate_with_niche_config(
            text=job.full_script,
            output_path=audio_path,
            niche=niche,
            language=settings.xtts_language,
            override_voice_id=getattr(job, "voice_id", None),
        )
        
        job.audio_path = str(audio_path.relative_to(settings.data_path))
        session.commit()
        
        duration = tts_service.get_audio_duration(audio_path)
        self._log(session, job_id, "INFO", f"Audio generated: {duration:.1f}s")
        
        # Step 3: Generate subtitles
        job.status = JobStatus.GENERATING_SUBTITLES
        job.progress_percent = 50
        session.commit()
        self._log(session, job_id, "INFO", "Generating subtitles...")
        
        subtitle_path = outputs_dir / "subtitles.srt"
        subtitle_service.generate_srt_with_niche_config(
            audio_path=audio_path,
            output_path=subtitle_path,
            niche=niche
        )
        
        job.subtitle_path = str(subtitle_path.relative_to(settings.data_path))
        session.commit()
        
        self._log(session, job_id, "INFO", "Subtitles generated")
        
        # Step 4: Render video
        job.status = JobStatus.RENDERING
        job.progress_percent = 70
        session.commit()
        self._log(session, job_id, "INFO", "Rendering video...")
        
        # Get visual assets
        bg_videos = visual_service.get_stock_videos(niche.name, count=1)
        bg_video = bg_videos[0] if bg_videos else None
        bg_music = visual_service.get_background_music(niche.name)
        # Logo disabled for now (user can re-enable later via config)
        logo = None  # visual_service.get_logo(niche.name)
        
        video_path = outputs_dir / f"{job_id}_final.mp4"
        
        render_config = RenderConfig(
            width=settings.default_video_width,
            height=settings.default_video_height,
            fps=settings.default_video_fps,
            audio_path=audio_path,
            bg_music_path=bg_music,
            bg_music_volume=settings.default_bg_music_volume,
            background_video=bg_video,
            subtitle_path=subtitle_path,
            burn_subtitles=True,
            logo_path=logo,
            output_path=video_path,
            video_model=job.video_model  # Pass LTX model selection
        )
        
        await render_service.render_video(render_config, script_text=job.full_script)
        
        job.video_path = str(video_path.relative_to(settings.data_path))
        job.duration_seconds = render_service.get_video_duration(video_path)
        job.file_size_bytes = video_path.stat().st_size
        session.commit()
        
        # Generate thumbnail
        thumbnail_path = outputs_dir / "thumbnail.jpg"
        render_service.generate_thumbnail(video_path, thumbnail_path)
        job.thumbnail_path = str(thumbnail_path.relative_to(settings.data_path))
        session.commit()
        
        self._log(session, job_id, "INFO", f"Video rendered: {job.duration_seconds:.1f}s, {job.file_size_bytes / 1024 / 1024:.2f} MB")
        
        # Create video record (use caption if set, else script snippet)
        desc = (getattr(job, "caption", None) or job.full_script or "")[:500]
        video = Video(
            job_id=job_id,
            niche_id=niche.id,
            title=job.topic[:100],
            description=desc,
            topic=job.topic,
            file_path=job.video_path,
            thumbnail_path=job.thumbnail_path,
            duration_seconds=job.duration_seconds,
            file_size_bytes=job.file_size_bytes,
            hashtags=niche.hashtags
        )
        session.add(video)
        session.commit()
    
    async def _publish_video(self, session: Session, job: Job, niche: Niche):
        """Publish video to platforms."""
        
        job_id = job.id
        
        if not job.video_path:
            raise ValueError("No video to publish")
        
        video_path = settings.data_path / job.video_path
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        job.status = JobStatus.PUBLISHING
        job.progress_percent = 90
        session.commit()
        self._log(session, job_id, "INFO", "Publishing video...")
        
        platforms = []
        if job.publish_youtube:
            platforms.append("youtube")
        if job.publish_instagram:
            platforms.append("instagram")
        if job.publish_tiktok:
            platforms.append("tiktok")
        
        if not platforms:
            self._log(session, job_id, "WARNING", "No platforms selected for publishing")
            return
        
        # Prepare account IDs
        account_ids = {
            "youtube": niche.youtube_account_id or niche.account_id,
            "instagram": niche.instagram_account_id or niche.account_id,
            "tiktok": niche.tiktok_account_id or niche.account_id
        }

        # Publish to platforms
        results = await publish_service.publish(
            video_path=video_path,
            title=job.topic,
            description=job.full_script or "",
            tags=niche.hashtags,
            hashtags=[f"#{tag}" for tag in niche.hashtags],
            platforms=platforms,
            account_ids=account_ids
        )
        
        # Store results
        job.publish_results = {
            platform: {
                "status": result.status.value,
                "video_id": result.video_id,
                "video_url": result.video_url,
                "message": result.message
            }
            for platform, result in results.items()
        }
        session.commit()
        
        # Create publish records
        video = session.exec(
            select(Video).where(Video.job_id == job_id)
        ).first()
        
        if video:
            for platform, result in results.items():
                publish_record = VideoPublish(
                    video_id=video.id,
                    platform=platform,
                    platform_video_id=result.video_id,
                    platform_url=result.video_url,
                    status=result.status.value,
                    error_message=result.message if result.status.value == "failed" else None,
                    published_at=datetime.utcnow() if result.status.value == "success" else None
                )
                session.add(publish_record)
        
        session.commit()
        
        for platform, result in results.items():
            self._log(session, job_id, "INFO", f"{platform}: {result.status.value} - {result.message}")
    
    def _fail_job(self, session: Session, job: Job, error: str):
        """Mark a job as failed."""
        job.status = JobStatus.FAILED
        job.error_message = error
        job.completed_at = datetime.utcnow()
        session.commit()
        self._log(session, job.id, "ERROR", f"Job failed: {error}")
    
    def _log(self, session: Session, job_id: int, level: str, message: str):
        """Add a log entry for a job."""
        log = JobLog(
            job_id=job_id,
            level=level,
            message=message
        )
        session.add(log)
        session.commit()
        logger.log(level, f"[Job {job_id}] {message}")


# Global worker instance
job_worker = JobWorker()


async def run_job_now(job_id: int):
    """Run a specific job immediately."""
    await job_worker._process_job(job_id)
