"""
Niche model - defines content categories and their configurations.
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Column
from enum import Enum


class VideoStyle(str, Enum):
    """Video style types."""
    NARRATOR_BROLL = "narrator_broll"  # Voiceover with B-roll footage
    STICK_CAPTION = "stick_caption"     # Stick figure with captions
    TWO_VOICE = "two_voice"             # Two-person dialogue
    FACELESS = "faceless"               # Text on screen with music
    SLIDESHOW = "slideshow"             # Image slideshow with narration


class NicheBase(SQLModel):
    """Base niche model."""
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    style: VideoStyle = Field(default=VideoStyle.NARRATOR_BROLL)
    
    # Posting targets - platforms to publish to
    post_to_youtube: bool = Field(default=True)
    post_to_instagram: bool = Field(default=True)
    post_to_tiktok: bool = Field(default=True)
    
    # Frequency
    posts_per_day: int = Field(default=1, ge=0, le=10)
    
    # Template prompts stored as JSON
    prompt_hook: str = Field(default="Generate an attention-grabbing hook for a video about {topic}.")
    prompt_body: str = Field(default="Write the main content script for a 60-second video about {topic}.")
    prompt_cta: str = Field(default="Write a compelling call-to-action for the end of the video.")
    
    # Hashtags as JSON array
    hashtags: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Content settings
    min_duration_seconds: int = Field(default=30)
    max_duration_seconds: int = Field(default=60)
    
    # Active flag
    is_active: bool = Field(default=True)


class Niche(NicheBase, table=True):
    """Niche database model."""
    __tablename__ = "niches"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NicheCreate(NicheBase):
    """Schema for creating a niche."""
    pass


class NicheUpdate(SQLModel):
    """Schema for updating a niche."""
    name: Optional[str] = None
    description: Optional[str] = None
    style: Optional[VideoStyle] = None
    post_to_youtube: Optional[bool] = None
    post_to_instagram: Optional[bool] = None
    post_to_tiktok: Optional[bool] = None
    posts_per_day: Optional[int] = None
    prompt_hook: Optional[str] = None
    prompt_body: Optional[str] = None
    prompt_cta: Optional[str] = None
    hashtags: Optional[List[str]] = None
    min_duration_seconds: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class NicheRead(NicheBase):
    """Schema for reading a niche."""
    id: int
    created_at: datetime
    updated_at: datetime
