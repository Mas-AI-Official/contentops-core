from typing import Optional, List
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime

class NicheTarget(SQLModel, table=True):
    """
    Mapping between Niches and Publishing Accounts.
    Determines where content for a niche gets published.
    """
    __tablename__ = "niche_targets"

    id: Optional[int] = Field(default=None, primary_key=True)
    niche_id: int = Field(foreign_key="niches.id", index=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    
    platform: str = Field(index=True)  # youtube, instagram, tiktok
    enabled: bool = Field(default=True)
    priority: int = Field(default=1)
    
    # Per-target schedule override (optional)
    schedule_override: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
