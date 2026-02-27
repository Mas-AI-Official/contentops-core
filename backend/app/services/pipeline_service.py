from datetime import datetime
from typing import Any

from loguru import logger
from sqlmodel import Session, select

from app.models import Job, JobType, JobStage, JobStageStatus


class PipelineService:
    """
    Lightweight orchestrator for job pipelines.

    Phase 1: keep behaviour the same while recording coarse stages
    ("generate", "publish") in the job_stages table. We can later
    expand this into finer-grained stages (trend_scout, script_writer, etc.)
    without changing callers.
    """

    async def run_pipeline(self, session: Session, job: Job, niche: Any, worker: "JobWorker") -> None:
        """
        Run the minimal pipeline for the given job.

        - For GENERATE_* jobs: run the generate stage (calls worker._generate_video)
        - For *_PUBLISH jobs: run the publish stage (calls worker._publish_video)
        """
        if job.job_type in (JobType.GENERATE_ONLY, JobType.GENERATE_AND_PUBLISH):
            await self._run_stage(session, job, "generate", worker._generate_video, niche)

        if job.job_type in (JobType.GENERATE_AND_PUBLISH, JobType.PUBLISH_EXISTING):
            await self._run_stage(session, job, "publish", worker._publish_video, niche)

    async def _run_stage(
        self,
        session: Session,
        job: Job,
        name: str,
        coro,
        *args: Any,
    ) -> None:
        """Record lifecycle for a single coarse stage and execute it."""
        stage = self._get_or_create_stage(session, job.id, name)
        now = datetime.utcnow()
        stage.status = JobStageStatus.RUNNING
        stage.started_at = stage.started_at or now
        stage.error_message = None
        session.add(stage)
        session.commit()

        logger.info(f"Running pipeline stage '{name}' for job {job.id}")

        try:
            # The worker method is an async coroutine
            await coro(session, job, *args)
        except Exception as e:
            logger.exception(f"Stage '{name}' failed for job {job.id}: {e}")
            stage.status = JobStageStatus.FAILED
            stage.completed_at = datetime.utcnow()
            stage.error_message = str(e)
            session.add(stage)
            session.commit()
            # Propagate so the job-level failure handling still runs
            raise
        else:
            stage.status = JobStageStatus.SUCCESS
            stage.completed_at = datetime.utcnow()
            session.add(stage)
            session.commit()

    def _get_or_create_stage(self, session: Session, job_id: int, name: str) -> JobStage:
        stage = session.exec(
            select(JobStage).where(JobStage.job_id == job_id, JobStage.name == name)
        ).first()
        if not stage:
            stage = JobStage(job_id=job_id, name=name)
            session.add(stage)
            session.commit()
            session.refresh(stage)
        return stage


pipeline_service = PipelineService()

