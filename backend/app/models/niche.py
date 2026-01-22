"""
Niche model - defines content categories and their configurations.
Includes per-niche AI model settings for flexible content generation.
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


class TTSProvider(str, Enum):
    """Text-to-speech provider options."""
    XTTS = "xtts"           # Local XTTS (Coqui)
    ELEVENLABS = "elevenlabs"  # ElevenLabs API


class WhisperDevice(str, Enum):
    """Device for Whisper inference."""
    CUDA = "cuda"   # GPU (NVIDIA)
    CPU = "cpu"     # CPU fallback


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
    
    # === Per-Niche AI Model Settings ===
    
    # LLM Settings (for script generation)
    llm_model: Optional[str] = Field(
        default=None, 
        description="Ollama model for this niche (e.g., 'llama3.1:8b'). If null, uses global default."
    )
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # TTS Settings (for voice generation)
    tts_provider: Optional[str] = Field(
        default=None,
        description="TTS provider: 'xtts' or 'elevenlabs'. If null, uses global default."
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="Voice ID for TTS. For ElevenLabs: voice ID. For XTTS: speaker wav path."
    )
    voice_name: Optional[str] = Field(
        default=None,
        description="Human-readable voice name for display."
    )
    
    # Whisper Settings (for subtitles)
    whisper_model: Optional[str] = Field(
        default=None,
        description="Whisper model size: 'tiny', 'base', 'small', 'medium', 'large'. If null, uses global."
    )
    whisper_device: Optional[str] = Field(
        default=None,
        description="Device for Whisper: 'cuda' or 'cpu'. If null, uses global default."
    )
    
    # Style Preset (future use for visual templates)
    style_preset: Optional[str] = Field(
        default=None,
        description="Visual style preset name for rendering templates."
    )
    
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
    
    # Per-niche AI settings
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    tts_provider: Optional[str] = None
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    whisper_model: Optional[str] = None
    whisper_device: Optional[str] = None
    style_preset: Optional[str] = None


class NicheRead(NicheBase):
    """Schema for reading a niche."""
    id: int
    created_at: datetime
    updated_at: datetime


class NicheModelConfig(SQLModel):
    """Helper class to get effective model config for a niche (with fallbacks to global)."""
    llm_model: str
    llm_temperature: float
    tts_provider: str
    voice_id: Optional[str]
    whisper_model: str
    whisper_device: str
    
    @classmethod
    def from_niche(cls, niche: Niche, settings) -> "NicheModelConfig":
        """Create config from niche with fallback to global settings."""
        return cls(
            llm_model=niche.llm_model or settings.ollama_model,
            llm_temperature=niche.llm_temperature,
            tts_provider=niche.tts_provider or settings.tts_provider,
            voice_id=niche.voice_id or (
                settings.elevenlabs_voice_id if (niche.tts_provider or settings.tts_provider) == "elevenlabs"
                else settings.xtts_speaker_wav
            ),
            whisper_model=niche.whisper_model or settings.whisper_model,
            whisper_device=niche.whisper_device or settings.whisper_device,
        )
