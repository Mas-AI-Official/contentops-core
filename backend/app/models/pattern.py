from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field

class PatternBase(SQLModel):
    name: str = Field(index=True)
    niche: Optional[str] = None
    hook_type: str  # question, statement, visual_shock, etc.
    structure_template: str  # problem-agitate-solve, listicle, story, etc.
    editing_grammar: str  # fast-paced, cinematic, vlog, etc.
    caption_style: str  # minimal, karaoke, descriptive
    performance_score: float = Field(default=0.0)
    example_url: Optional[str] = None

class Pattern(PatternBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = Field(default=0)

class PatternCreate(PatternBase):
    pass

class PatternRead(PatternBase):
    id: int
    created_at: datetime
    usage_count: int
