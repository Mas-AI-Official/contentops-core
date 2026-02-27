from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.signal_service import signal_service
from app.models.signal import Signal, SignalCreate
from app.db import get_async_session
from sqlmodel import Session
from fastapi import Depends

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("/", response_model=List[Signal])
async def get_signals(niche: Optional[str] = None, limit: int = 50):
    return signal_service.get_signals(niche, limit)

@router.post("/", response_model=Signal)
async def ingest_signal(signal: SignalCreate):
    return signal_service.ingest_signal(signal)

@router.post("/score")
async def score_signals(niche: str):
    return signal_service.score_signals(niche)


@router.post("/{signal_id}/acknowledge")
async def acknowledge_signal(signal_id: int, session: Session = Depends(get_async_session)):
    signal = await session.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    signal.status = "processed"
    session.add(signal)
    await session.commit()
    return {"id": signal_id, "status": signal.status}
