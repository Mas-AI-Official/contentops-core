from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_async_session
from app.models.trends import PromptPack
from app.services.prompt_service import prompt_service
from pydantic import BaseModel

router = APIRouter(prefix="/promptpack", tags=["promptpack"])

class GenerateRequest(BaseModel):
    account_id: int
    niche_id: int
    candidate_id: Optional[int] = None
    constraints: Optional[Dict[str, Any]] = None

@router.post("/generate", response_model=PromptPack)
async def generate_promptpack(
    request: GenerateRequest,
    session: Session = Depends(get_async_session)
):
    """Generate a prompt pack."""
    return await prompt_service.generate_prompt_pack(
        session=session,
        account_id=request.account_id,
        niche_id=request.niche_id,
        candidate_id=request.candidate_id,
        constraints=request.constraints
    )

@router.get("/", response_model=List[PromptPack])
async def list_promptpacks(
    niche_id: Optional[int] = None,
    account_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """List prompt packs."""
    query = select(PromptPack)
    if niche_id:
        query = query.where(PromptPack.niche_id == niche_id)
    if account_id:
        query = query.where(PromptPack.account_id == account_id)
        
    query = query.order_by(PromptPack.created_at.desc()).limit(50)
    result = session.exec(query)
    return result.all()

@router.get("/{id}", response_model=PromptPack)
async def get_promptpack(
    id: int,
    session: Session = Depends(get_async_session)
):
    """Get a prompt pack."""
    pack = session.get(PromptPack, id)
    if not pack:
        raise HTTPException(status_code=404, detail="PromptPack not found")
    return pack
