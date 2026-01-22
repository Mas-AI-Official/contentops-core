"""
Analytics models - video performance tracking.
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field


class VideoMetrics(SQLModel, table=True):
    """Video performance metrics per platform."""
    __tablename__ = "video_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True)
    platform: str  # youtube, instagram, tiktok
    
    # Date of metrics snapshot
    metrics_date: date = Field(index=True)
    
    # Common metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    
    # Platform-specific
    watch_time_seconds: Optional[int] = None  # YouTube
    average_view_duration: Optional[float] = None  # YouTube
    impressions: Optional[int] = None  # Instagram, TikTok
    reach: Optional[int] = None  # Instagram
    saves: Optional[int] = None  # Instagram
    
    # Engagement rate calculation
    engagement_rate: Optional[float] = None
    
    # Timestamps
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class DailyNicheStats(SQLModel, table=True):
    """Aggregated daily stats per niche."""
    __tablename__ = "daily_niche_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    niche_id: int = Field(foreign_key="niches.id", index=True)
    stats_date: date = Field(index=True)
    
    # Counts
    videos_created: int = 0
    videos_published: int = 0
    videos_failed: int = 0
    
    # Aggregated metrics across all platforms
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    
    # Best performer of the day
    top_video_id: Optional[int] = None
    top_video_views: int = 0


class VideoScore(SQLModel, table=True):
    """Video scoring for winner detection."""
    __tablename__ = "video_scores"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True, unique=True)
    
    # Scoring components
    views_velocity: float = 0.0  # Views per hour in first 24h
    engagement_score: float = 0.0  # Weighted engagement
    virality_score: float = 0.0  # Combined score
    
    # Classification
    is_winner: bool = False  # Top 10% performer
    is_underperformer: bool = False  # Bottom 10%
    
    # Timestamps
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSummary(SQLModel):
    """Schema for analytics summary response."""
    total_videos: int
    total_views: int
    total_likes: int
    total_comments: int
    avg_views_per_video: float
    avg_engagement_rate: float
    top_performing_niche: Optional[str]
    winner_count: int
