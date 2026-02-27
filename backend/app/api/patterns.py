from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.pattern_service import pattern_service
from app.models.pattern import Pattern, PatternCreate

router = APIRouter(prefix="/patterns", tags=["patterns"])

@router.get("/", response_model=List[Pattern])
async def get_patterns(niche: Optional[str] = None):
    return pattern_service.get_patterns(niche)

@router.post("/", response_model=Pattern)
async def create_pattern(pattern: PatternCreate):
    return pattern_service.create_pattern(pattern)

@router.post("/analyze/{signal_id}")
async def analyze_signal(signal_id: int):
    result = pattern_service.analyze_signal(signal_id)
    if not result:
        raise HTTPException(status_code=404, detail="Could not analyze signal or signal not found")
    return result
