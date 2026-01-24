from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_async_session
from app.models.memory import MemoryIndex
from app.services.memory_service import memory_service
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["memory"])

class CheckDuplicateRequest(BaseModel):
    account_id: int
    niche_id: int
    text: str

@router.post("/check_duplicate")
async def check_duplicate(
    request: CheckDuplicateRequest,
    session: Session = Depends(get_async_session)
):
    """Check for duplicates."""
    return await memory_service.check_duplicate(
        session=session,
        account_id=request.account_id,
        niche_id=request.niche_id,
        text=request.text
    )

@router.get("/history", response_model=List[MemoryIndex])
async def get_history(
    account_id: Optional[int] = None,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """Get memory history."""
    query = select(MemoryIndex)
    if account_id:
        query = query.where(MemoryIndex.account_id == account_id)
    if niche_id:
        query = query.where(MemoryIndex.niche_id == niche_id)
        
    query = query.order_by(MemoryIndex.created_at.desc()).limit(50)
    result = session.exec(query)
    return result.all()
