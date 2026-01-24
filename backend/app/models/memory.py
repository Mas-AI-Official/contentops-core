from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class MemoryIndex(SQLModel, table=True):
    __tablename__ = "memory_index"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    niche_id: int = Field(foreign_key="niches.id")
    
    embedding: List[float] = Field(sa_column=Column(JSON)) # Store as JSON for compatibility
    fingerprint: str
    promptpack_id: Optional[int] = Field(default=None, foreign_key="promptpacks.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
