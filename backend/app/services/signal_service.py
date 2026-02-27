from typing import List, Optional
from sqlmodel import select, Session
from app.db import sync_engine as engine
from app.models.signal import Signal, SignalCreate

class SignalService:
    def get_signals(self, niche: Optional[str] = None, limit: int = 50) -> List[Signal]:
        with Session(engine) as session:
            query = select(Signal)
            if niche:
                query = query.where(Signal.niche == niche)
            query = query.order_by(Signal.timestamp.desc()).limit(limit)
            return session.exec(query).all()

    def ingest_signal(self, signal_data: SignalCreate) -> Signal:
        with Session(engine) as session:
            # Check for duplicates (simple URL check)
            if signal_data.source_url:
                existing = session.exec(select(Signal).where(Signal.source_url == signal_data.source_url)).first()
                if existing:
                    return existing
            
            signal = Signal.model_validate(signal_data)
            session.add(signal)
            session.commit()
            session.refresh(signal)
            return signal

    def score_signals(self, niche: str) -> List[Signal]:
        # Mock scoring logic
        signals = self.get_signals(niche)
        # In a real impl, we'd use LLM or heuristics to update engagement_score
        return signals

signal_service = SignalService()
