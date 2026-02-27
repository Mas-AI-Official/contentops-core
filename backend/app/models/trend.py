from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel

class TrendBase(SQLModel):
    query: str = Field(index=True)
    source: str = Field(default="google_trends")  # google_trends, twitter, tiktok, manual
    volume: int = Field(default=0)
    sentiment: float = Field(default=0.0)  # -1.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    region: str = Field(default="US")
    category: Optional[str] = None
    metadata_json: Optional[str] = None  # JSON string for extra data

class Trend(TrendBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True)
    processed: bool = Field(default=False)

class TrendCreate(TrendBase):
    pass

class TrendRead(TrendBase):
    id: int
    is_active: bool
    processed: bool

class TrendAnalysis(BaseModel):
    trend_id: int
    relevance_score: float
    potential_hooks: List[str]
    suggested_niche: Optional[str]
    analysis_text: str
