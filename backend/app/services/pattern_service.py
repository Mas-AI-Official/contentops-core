from typing import List, Optional
from sqlmodel import select, Session
from app.db import sync_engine as engine
from app.models.pattern import Pattern, PatternCreate

class PatternService:
    def get_patterns(self, niche: Optional[str] = None) -> List[Pattern]:
        with Session(engine) as session:
            query = select(Pattern)
            if niche:
                query = query.where(Pattern.niche == niche)
            return session.exec(query).all()

    def create_pattern(self, pattern_data: PatternCreate) -> Pattern:
        with Session(engine) as session:
            pattern = Pattern.model_validate(pattern_data)
            session.add(pattern)
            session.commit()
            session.refresh(pattern)
            return pattern

    def analyze_signal(self, signal_id: int) -> Optional[Pattern]:
        # Mock analysis: Convert a signal into a pattern card
        # In real impl, use LLM to extract pattern from signal content
        return None

pattern_service = PatternService()
