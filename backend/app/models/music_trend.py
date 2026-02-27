from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime

class MusicTrendBase(SQLModel):
    title: str = Field(index=True)
    artist: str
    platform: str = Field(default="tiktok")  # tiktok, instagram, youtube
    usage_count: int = Field(default=0)
    viral_score: float = Field(default=0.0)
    audio_url: Optional[str] = None
    bpm: Optional[int] = None
    mood: Optional[str] = None

class MusicTrend(MusicTrendBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MusicTrendCreate(MusicTrendBase):
    pass

class MusicTrendRead(MusicTrendBase):
    id: int
    created_at: datetime
