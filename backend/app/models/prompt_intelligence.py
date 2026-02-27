from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from datetime import datetime

class ScriptPrompt(BaseModel):
    system: str
    user: str
    estimated_duration: int

class StoryboardScene(BaseModel):
    scene_number: int
    description: str
    duration: int
    visual_prompt: str
    audio_cue: Optional[str] = None

class Storyboard(BaseModel):
    scenes: List[StoryboardScene]
    total_duration: int

class VisualPrompts(BaseModel):
    scenes: Dict[str, str]  # scene_id -> prompt

class VoiceSpec(BaseModel):
    provider: str
    voice_id: str
    stability: float
    similarity_boost: float
    speed: float
    tone: str

class EditRecipe(BaseModel):
    captions_enabled: bool
    caption_style: str
    transition_style: str
    bg_music_genre: str
    beat_markers: List[float]

class PromptBundle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Stored as JSON strings
    script_prompt_json: str
    storyboard_json: str
    visual_prompts_json: str
    voice_spec_json: str
    edit_recipe_json: str
    hashtags_json: str
    caption_text: str
    
    # Dedup
    embedding_json: Optional[str] = None
