from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.services.governance_service import governance_service
from app.models.governance import ComplianceCheck, Policy, AuditLog
from app.db import get_async_session
from sqlmodel import Session, select

router = APIRouter(prefix="/governance", tags=["governance"])

@router.get("/")
async def list_governance_rules(session: Session = Depends(get_async_session), limit: int = 50):
    policies_res = await session.execute(select(Policy).where(Policy.is_active == True).limit(limit))
    audits_res = await session.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20))
    policies = policies_res.scalars().all()
    audits = audits_res.scalars().all()
    return {
        "policies": policies,
        "recent_audit_logs": audits,
    }

@router.post("/check", response_model=ComplianceCheck)
async def check_compliance(content: str, entity_type: str, entity_id: str):
    return governance_service.check_compliance(content, entity_type, entity_id)
