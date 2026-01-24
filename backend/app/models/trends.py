from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

class TrendCandidate(SQLModel, table=True):
    __tablename__ = "trend_candidates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    source_id: str  # e.g. video ID or post ID
    url: str
    creator: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    metrics: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    niche_id: Optional[int] = Field(default=None, foreign_key="niches.id")
    
    # Analysis link
    analysis: Optional["PatternAnalysis"] = Relationship(back_populates="candidate")

class PatternAnalysis(SQLModel, table=True):
    __tablename__ = "pattern_analysis"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="trend_candidates.id")
    hook_type: Optional[str] = None
    pacing: Optional[str] = None
    structure: Optional[str] = None
    audience_intent: Optional[str] = None
    format_features: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    candidate: Optional[TrendCandidate] = Relationship(back_populates="analysis")

class PromptPack(SQLModel, table=True):
    __tablename__ = "promptpacks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    niche_id: int = Field(foreign_key="niches.id")
    source_candidate_id: Optional[int] = Field(default=None, foreign_key="trend_candidates.id")
    
    variants: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # A, B, C
    caption_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    hashtags_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    status: str = Field(default="draft") # draft, approved, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    artifacts: List["Artifact"] = Relationship(back_populates="promptpack")

class Artifact(SQLModel, table=True):
    __tablename__ = "artifacts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    promptpack_id: int = Field(foreign_key="promptpacks.id")
    type: str # video, thumbnail, script
    path: str
    url: Optional[str] = None
    status: str = Field(default="created")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    promptpack: Optional[PromptPack] = Relationship(back_populates="artifacts")

class ComplianceEvent(SQLModel, table=True):
    __tablename__ = "compliance_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    severity: str
    message: str
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
