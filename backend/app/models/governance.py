from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field

class PolicyBase(SQLModel):
    name: str = Field(index=True)
    description: str
    rules_json: str  # JSON list of rules
    is_active: bool = Field(default=True)
    severity: str = Field(default="warning")  # warning, block

class Policy(PolicyBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str  # generate, publish, delete
    entity_type: str  # video, script, signal
    entity_id: Optional[str] = None
    user_id: Optional[str] = None  # "system" or user
    details_json: Optional[str] = None
    status: str = Field(default="success")

class ComplianceCheck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entity_type: str
    entity_id: str
    passed: bool
    issues_json: Optional[str] = None
    score: float = Field(default=1.0)
