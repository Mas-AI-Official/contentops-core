"""
Voice profiles and routing: per-account, per-niche, and scene-level speaker mapping.
TTS priority: xtts_local -> qwen3_tts -> elevenlabs.
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from enum import Enum


class VoiceStyle(str, Enum):
    """Voice style tags for selection."""
    CALM = "calm"
    MALE = "male"
    FEMALE = "female"
    STORYTELLING = "storytelling"
    ENERGETIC = "energetic"
    SERIOUS = "serious"


class VoiceProfileBase(SQLModel):
    """Named voice profile: provider, style tags, reference path (for XTTS/clone)."""
    name: str = Field(index=True)
    provider: str = Field(description="xtts, qwen3_tts, elevenlabs")
    style_tags: List[str] = Field(default=[], sa_column=Column(JSON))  # calm, female, energetic, etc.
    sample_reference_path: Optional[str] = None  # Path to .wav for XTTS/Qwen clone
    language_accent: Optional[str] = None
    default_speed: Optional[float] = None
    default_pitch: Optional[float] = None
    external_voice_id: Optional[str] = None  # ElevenLabs voice ID when provider=elevenlabs


class VoiceProfile(VoiceProfileBase, table=True):
    """Stored voice profile."""
    __tablename__ = "voice_profiles"
    id: Optional[int] = Field(default=None, primary_key=True)


class NicheVoiceRuleBase(SQLModel):
    """Default voice and tone for a niche; allows multi-speaker."""
    niche_id: int = Field(foreign_key="niches.id")
    default_voice_profile_id: Optional[int] = Field(default=None, foreign_key="voice_profiles.id")
    tone_preset: Optional[str] = None  # e.g. professional, casual
    multi_speaker_allowed: bool = Field(default=True)


class NicheVoiceRule(NicheVoiceRuleBase, table=True):
    """Stored niche voice rule (one per niche)."""
    __tablename__ = "niche_voice_rules"
    id: Optional[int] = Field(default=None, primary_key=True)


class AccountVoiceRuleBase(SQLModel):
    """Preferred voice for an account; niche can override if allowed."""
    account_id: int = Field(foreign_key="accounts.id")
    preferred_voice_profile_id: Optional[int] = Field(default=None, foreign_key="voice_profiles.id")
    brand_voice_style: Optional[str] = None
    allow_override_from_niche: bool = Field(default=True)


class AccountVoiceRule(AccountVoiceRuleBase, table=True):
    """Stored account voice rule (one per account)."""
    __tablename__ = "account_voice_rules"
    id: Optional[int] = Field(default=None, primary_key=True)


class SceneSpeakerMapBase(SQLModel):
    """Maps scene index to voice style or profile for multi-speaker scripts."""
    job_id: int = Field(foreign_key="jobs.id")
    scene_index: int = Field(description="0-based scene number")
    voice_profile_id: Optional[int] = Field(default=None, foreign_key="voice_profiles.id")
    style_hint: Optional[str] = None  # female calm, male narrator, etc.


class SceneSpeakerMap(SceneSpeakerMapBase, table=True):
    """Stored scene->speaker mapping for a job."""
    __tablename__ = "scene_speaker_map"
    id: Optional[int] = Field(default=None, primary_key=True)
