from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel

class SignalBase(SQLModel):
    source: str = Field(index=True)  # google_trends, rss, reddit, youtube, tiktok
    source_url: Optional[str] = None
    niche: str = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    keywords: str  # Comma-separated or JSON list
    engagement_score: float = Field(default=0.0)
    metadata_json: Optional[str] = None  # JSON string for extra data (views, likes, etc.)
    status: str = Field(default="new")  # new, processed, ignored

class Signal(SignalBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SignalCreate(SignalBase):
    pass

class SignalRead(SignalBase):
    id: int
    created_at: datetime
