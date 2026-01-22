"""
Job model - content generation and publishing jobs.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from enum import Enum


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    QUEUED = "queued"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_SUBTITLES = "generating_subtitles"
    RENDERING = "rendering"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job operation type."""
    GENERATE_ONLY = "generate_only"
    GENERATE_AND_PUBLISH = "generate_and_publish"
    PUBLISH_EXISTING = "publish_existing"


class JobBase(SQLModel):
    """Base job model."""
    niche_id: int = Field(foreign_key="niches.id")
    job_type: JobType = Field(default=JobType.GENERATE_ONLY)
    
    # Topic
    topic: str
    topic_source: str = Field(default="manual")  # "manual", "generated", "list"
    
    # Generated content
    script_hook: Optional[str] = None
    script_body: Optional[str] = None
    script_cta: Optional[str] = None
    full_script: Optional[str] = None
    
    # File paths (relative to data folder)
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    
    # Processing status
    status: JobStatus = Field(default=JobStatus.PENDING)
    progress_percent: int = Field(default=0)
    error_message: Optional[str] = None
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    
    # Publishing targets
    publish_youtube: bool = Field(default=False)
    publish_instagram: bool = Field(default=False)
    publish_tiktok: bool = Field(default=False)
    
    # Publish results stored as JSON
    publish_results: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    # Metadata
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None


class Job(JobBase, table=True):
    """Job database model."""
    __tablename__ = "jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobCreate(SQLModel):
    """Schema for creating a job."""
    niche_id: int
    job_type: JobType = JobType.GENERATE_ONLY
    topic: str
    topic_source: str = "manual"
    scheduled_at: Optional[datetime] = None
    publish_youtube: bool = False
    publish_instagram: bool = False
    publish_tiktok: bool = False


class JobUpdate(SQLModel):
    """Schema for updating a job."""
    status: Optional[JobStatus] = None
    script_hook: Optional[str] = None
    script_body: Optional[str] = None
    script_cta: Optional[str] = None
    full_script: Optional[str] = None
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    progress_percent: Optional[int] = None
    error_message: Optional[str] = None
    publish_youtube: Optional[bool] = None
    publish_instagram: Optional[bool] = None
    publish_tiktok: Optional[bool] = None


class JobRead(JobBase):
    """Schema for reading a job."""
    id: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class JobLog(SQLModel, table=True):
    """Job execution log entries."""
    __tablename__ = "job_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field(default="INFO")  # INFO, WARNING, ERROR
    message: str
    details: Optional[str] = None


class JobLogCreate(SQLModel):
    """Schema for creating a job log."""
    job_id: int
    level: str = "INFO"
    message: str
    details: Optional[str] = None
