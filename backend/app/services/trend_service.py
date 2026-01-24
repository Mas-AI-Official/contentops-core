import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select
from loguru import logger

from app.services.trend_scraper_service import trend_scraper_service
from app.models.trends import TrendCandidate, PatternAnalysis
from app.models.niche import Niche

class TrendService:
    async def scan_trends(
        self, 
        session: Session,
        niche_id: int, 
        platforms: List[str], 
        region: str = "US", 
        limit: int = 20
    ) -> List[TrendCandidate]:
        """Scan for trends and save to DB."""
        niche = session.get(Niche, niche_id)
        if not niche:
            raise ValueError("Niche not found")
            
        # Call scraper service
        candidates = await trend_scraper_service.scan_niche(
            niche=niche.slug, # Use slug or keywords
            platforms=platforms,
            region=region,
            limit=limit
        )
        
        saved_candidates = []
        for cand in candidates:
            cand.niche_id = niche_id
            # Check for duplicates (by url or source_id)
            existing = session.exec(
                select(TrendCandidate).where(
                    (TrendCandidate.source_id == cand.source_id) & 
                    (TrendCandidate.platform == cand.platform)
                )
            ).first()
            
            if not existing:
                session.add(cand)
                saved_candidates.append(cand)
            else:
                # Update metrics?
                existing.metrics = cand.metrics
                session.add(existing)
                saved_candidates.append(existing)
        
        await session.commit()
        return saved_candidates

    async def analyze_candidates(
        self,
        session: Session,
        candidate_ids: List[int]
    ) -> List[PatternAnalysis]:
        """Analyze candidates using LLM."""
        analyses = []
        for cid in candidate_ids:
            cand = session.get(TrendCandidate, cid)
            if not cand:
                continue
                
            # Check if already analyzed
            if cand.analysis:
                analyses.append(cand.analysis)
                continue
                
            # Perform analysis (Mock for now, or use LLM)
            # In real implementation, pass caption/transcript to LLM
            analysis = PatternAnalysis(
                candidate_id=cid,
                hook_type="Question Hook",
                pacing="Fast",
                structure="Problem-Agitation-Solution",
                audience_intent="Entertainment",
                format_features={"text_overlay": True, "music": "Trending"}
            )
            session.add(analysis)
            analyses.append(analysis)
            
        await session.commit()
        return analyses

trend_service = TrendService()
