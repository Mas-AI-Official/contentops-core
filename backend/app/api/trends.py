from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_async_session
from app.models.trends import TrendCandidate, PatternAnalysis
from app.services.trend_service import trend_service
from pydantic import BaseModel

router = APIRouter(prefix="/trends", tags=["trends"])

class ScanRequest(BaseModel):
    niche_id: int
    platforms: List[str]
    region: str = "US"
    limit: int = 20

class AnalyzeRequest(BaseModel):
    candidate_ids: List[int]

@router.post("/scan", response_model=List[TrendCandidate])
async def scan_trends(
    request: ScanRequest,
    session: Session = Depends(get_async_session)
):
    """Scan for trends."""
    return await trend_service.scan_trends(
        session=session,
        niche_id=request.niche_id,
        platforms=request.platforms,
        region=request.region,
        limit=request.limit
    )

@router.post("/analyze", response_model=List[PatternAnalysis])
async def analyze_trends(
    request: AnalyzeRequest,
    session: Session = Depends(get_async_session)
):
    """Analyze trend candidates."""
    return await trend_service.analyze_candidates(
        session=session,
        candidate_ids=request.candidate_ids
    )

@router.get("/candidates", response_model=List[TrendCandidate])
async def list_candidates(
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """List stored candidates."""
    query = select(TrendCandidate)
    if niche_id:
        query = query.where(TrendCandidate.niche_id == niche_id)
    query = query.order_by(TrendCandidate.discovered_at.desc()).limit(100)
    result = await session.execute(query)
    return list(result.scalars().all())
