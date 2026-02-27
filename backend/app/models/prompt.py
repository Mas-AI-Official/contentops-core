from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text

class PromptPackBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    category: str = Field(default="general")
    tags: Optional[str] = None  # Comma-separated
    is_public: bool = Field(default=False)

class PromptPack(PromptPackBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
    
    # Content
    hook_template: str
    body_template: str
    cta_template: str
    system_prompt: Optional[str] = None

class PromptPackCreate(PromptPackBase):
    hook_template: str
    body_template: str
    cta_template: str
    system_prompt: Optional[str] = None

class PromptPackRead(PromptPackBase):
    id: int
    created_at: datetime
    updated_at: datetime
    version: int
    hook_template: str
    body_template: str
    cta_template: str
    system_prompt: Optional[str]

class PromptOptimizationRequest(SQLModel):
    original_prompt: str
    goal: str = "improve_clarity"
    target_audience: Optional[str] = None

class PromptsLog(SQLModel, table=True):
    """Log of all prompts sent to LLMs."""
    __tablename__ = "prompts_log"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[int] = Field(default=None, foreign_key="jobs.id")
    
    # Request
    prompt_text: str = Field(sa_column=Column(Text))
    system_prompt: Optional[str] = None
    model: str
    
    # Response
    response_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    duration_ms: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
