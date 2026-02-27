"""
Niche-Account Map model - Many-to-Many relationship between Niches and Accounts.
Allows a niche to publish to multiple accounts, and an account to serve multiple niches.
"""
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class NicheAccountMap(SQLModel, table=True):
    """Mapping between Niches and Accounts."""
    __tablename__ = "niche_account_map"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    niche_id: int = Field(foreign_key="niches.id", index=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    
    # Configuration for this specific link
    enabled: bool = Field(default=True)
    cadence_profile_id: Optional[str] = Field(default=None)  # Future: link to a schedule profile
    content_type_mask: Optional[str] = Field(default=None)   # e.g., "shorts,reels"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
