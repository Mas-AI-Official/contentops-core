"""
Video model - output video library and metadata.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class VideoBase(SQLModel):
    """Base video model."""
    job_id: int = Field(foreign_key="jobs.id", index=True)
    niche_id: int = Field(foreign_key="niches.id", index=True)
    
    # Content info
    title: str
    description: Optional[str] = None
    topic: str
    
    # File info
    file_path: str
    thumbnail_path: Optional[str] = None
    duration_seconds: float
    file_size_bytes: int
    
    # Technical details
    width: int = 1080
    height: int = 1920
    fps: int = 30
    
    # Tags and metadata
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    hashtags: List[str] = Field(default=[], sa_column=Column(JSON))


class Video(VideoBase, table=True):
    """Video database model."""
    __tablename__ = "videos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoCreate(VideoBase):
    """Schema for creating a video."""
    pass


class VideoRead(VideoBase):
    """Schema for reading a video."""
    id: int
    created_at: datetime


class VideoPublish(SQLModel, table=True):
    """Record of video publishing to platforms."""
    __tablename__ = "video_publishes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True)
    platform: str  # youtube, instagram, tiktok
    
    # Platform-specific IDs
    platform_video_id: Optional[str] = None
    platform_url: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, published, failed, private
    error_message: Optional[str] = None
    
    # Timestamps
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
