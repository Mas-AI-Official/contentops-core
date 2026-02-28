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
        niche = await session.get(Niche, niche_id)
        if not niche:
            raise ValueError("Niche not found")

        candidates = await trend_scraper_service.scan_niche(
            niche=niche.slug,
            platforms=platforms,
            region=region,
            limit=limit
        )

        saved_candidates = []
        for cand in candidates:
            cand.niche_id = niche_id
            r = await session.execute(
                select(TrendCandidate).where(
                    (TrendCandidate.source_id == cand.source_id) &
                    (TrendCandidate.platform == cand.platform)
                )
            )
            existing = r.scalars().first()
            if not existing:
                session.add(cand)
                saved_candidates.append(cand)
            else:
                existing.metrics = cand.metrics
                session.add(existing)
                saved_candidates.append(existing)

        await session.commit()
        return saved_candidates

    async def _analyze_with_llm(self, text: str) -> Dict[str, Any]:
        """Analyze text using Reasoning model."""
        from app.core.config import settings
        import httpx
        import json
        
        prompt = f"""Analyze this viral video content and extract the pattern.
        
        Content: "{text}"
        
        Return JSON with:
        - hook_type (e.g. Question, Statement, Visual)
        - pacing (Fast, Medium, Slow)
        - structure (e.g. PAS, Listicle, Story)
        - audience_intent (e.g. Education, Entertainment)
        - format_features (list of features)
        
        JSON:"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_reasoning_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }
                )
                if response.status_code != 200:
                    logger.error(f"LLM error: {response.text}")
                    return {}
                    
                data = response.json()
                content = data.get("response", "{}")
                return json.loads(content)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {}

    async def analyze_candidates(
        self,
        session: Session,
        candidate_ids: List[int]
    ) -> List[PatternAnalysis]:
        """Analyze candidates using LLM."""
        analyses = []
        for cid in candidate_ids:
            cand = await session.get(TrendCandidate, cid)
            if not cand:
                continue
            r = await session.execute(select(PatternAnalysis).where(PatternAnalysis.candidate_id == cid))
            existing_analysis = r.scalars().first()
            if existing_analysis:
                analyses.append(existing_analysis)
                continue
            result = await self._analyze_with_llm(cand.caption or "")
            analysis = PatternAnalysis(
                candidate_id=cid,
                hook_type=result.get("hook_type", "Unknown"),
                pacing=result.get("pacing", "Medium"),
                structure=result.get("structure", "Unknown"),
                audience_intent=result.get("audience_intent", "Unknown"),
                format_features=result.get("format_features", {})
            )
            session.add(analysis)
            analyses.append(analysis)
        await session.commit()
        return analyses

trend_service = TrendService()
