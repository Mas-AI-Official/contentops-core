from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text, JSON

class ScrapedItem(SQLModel, table=True):
    """Raw scraped content from various sources."""
    __tablename__ = "scraped_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_url: str = Field(index=True)
    source_platform: str = Field(index=True)  # tiktok, instagram, youtube, web
    content_type: str = "video"  # video, image, text
    
    # Content
    title: Optional[str] = None
    description: Optional[str] = None
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    raw_data: Dict = Field(default={}, sa_column=Column(JSON))
    
    # Metadata
    author: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    published_at: Optional[datetime] = None
    
    # Processing status
    is_processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ViralDNA(SQLModel, table=True):
    """Analyzed patterns from high-performing content."""
    __tablename__ = "viral_dna"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    scraped_item_id: Optional[int] = Field(default=None, foreign_key="scraped_items.id")
    
    # Analysis
    hook_type: str
    pacing_score: float
    emotional_triggers: List[str] = Field(default=[], sa_column=Column(JSON))
    visual_patterns: List[str] = Field(default=[], sa_column=Column(JSON))
    audio_patterns: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Embedding for similarity search
    embedding: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GeneratedAsset(SQLModel, table=True):
    """Intermediate assets generated during creation."""
    __tablename__ = "generated_assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[int] = Field(default=None, foreign_key="jobs.id")
    
    asset_type: str  # image, audio, video_segment, script
    file_path: str
    
    # Metadata
    prompt_used: Optional[str] = None
    model_used: Optional[str] = None
    parameters: Dict = Field(default={}, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
