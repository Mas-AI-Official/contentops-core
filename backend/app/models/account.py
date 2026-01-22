"""
Account model - platform account configurations.
Secrets are NOT stored in DB - only references to env vars.
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from enum import Enum


class Platform(str, Enum):
    """Supported platforms."""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class AccountStatus(str, Enum):
    """Account connection status."""
    CONNECTED = "connected"
    MISSING_CONFIG = "missing_config"
    EXPIRED = "expired"
    ERROR = "error"


class AccountBase(SQLModel):
    """Base account model."""
    platform: Platform
    account_name: str = Field(index=True)
    account_handle: Optional[str] = None  # @username or channel ID
    
    # Reference to which env vars hold credentials (not the actual values)
    credentials_env_prefix: str = Field(default="")  # e.g., "YOUTUBE" -> looks for YOUTUBE_CLIENT_ID etc.
    
    # Status
    is_active: bool = Field(default=True)
    last_verified: Optional[datetime] = None
    
    # Platform-specific IDs (non-secret)
    platform_user_id: Optional[str] = None
    platform_channel_id: Optional[str] = None


class Account(AccountBase, table=True):
    """Account database model."""
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AccountCreate(AccountBase):
    """Schema for creating an account."""
    pass


class AccountUpdate(SQLModel):
    """Schema for updating an account."""
    account_name: Optional[str] = None
    account_handle: Optional[str] = None
    credentials_env_prefix: Optional[str] = None
    is_active: Optional[bool] = None
    platform_user_id: Optional[str] = None
    platform_channel_id: Optional[str] = None


class AccountRead(AccountBase):
    """Schema for reading an account."""
    id: int
    created_at: datetime
    updated_at: datetime
    status: AccountStatus = AccountStatus.MISSING_CONFIG  # Computed field


class AccountStatusCheck(SQLModel):
    """Schema for account status response."""
    id: int
    platform: Platform
    account_name: str
    status: AccountStatus
    message: str
