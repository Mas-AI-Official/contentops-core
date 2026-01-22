"""
API routes for niche management.
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import Niche, NicheCreate, NicheUpdate, NicheRead
from app.services import topic_service

router = APIRouter(prefix="/niches", tags=["niches"])


@router.get("/", response_model=List[NicheRead])
async def list_niches(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    session: Session = Depends(get_async_session)
):
    """List all niches."""
    query = select(Niche)
    if active_only:
        query = query.where(Niche.is_active == True)
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{niche_id}", response_model=NicheRead)
async def get_niche(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Get a specific niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    return niche


@router.post("/", response_model=NicheRead, status_code=201)
async def create_niche(
    niche: NicheCreate,
    session: Session = Depends(get_async_session)
):
    """Create a new niche."""
    # Check for duplicate name
    existing = await session.execute(
        select(Niche).where(Niche.name == niche.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Niche with this name already exists")
    
    db_niche = Niche.model_validate(niche)
    session.add(db_niche)
    await session.commit()
    await session.refresh(db_niche)
    return db_niche


@router.patch("/{niche_id}", response_model=NicheRead)
async def update_niche(
    niche_id: int,
    niche_update: NicheUpdate,
    session: Session = Depends(get_async_session)
):
    """Update a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    update_data = niche_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(niche, key, value)
    
    niche.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(niche)
    return niche


@router.delete("/{niche_id}")
async def delete_niche(
    niche_id: int,
    session: Session = Depends(get_async_session)
):
    """Delete a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    await session.delete(niche)
    await session.commit()
    return {"message": "Niche deleted"}


@router.post("/{niche_id}/generate-topics")
async def generate_topics(
    niche_id: int,
    count: int = 5,
    session: Session = Depends(get_async_session)
):
    """Generate topic ideas for a niche."""
    niche = await session.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    topics = await topic_service.get_trending_topics(niche.name, count=count)
    return {"topics": topics}
