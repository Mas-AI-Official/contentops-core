import json
from typing import List, Dict, Any, Optional
from sqlmodel import Session
from loguru import logger
from app.models.trends import PromptPack, TrendCandidate, PatternAnalysis
from app.models.niche import Niche
from app.services.script_service import script_service
from app.services.memory_service import memory_service

class PromptService:
    async def generate_prompt_pack(
        self,
        session: Session,
        account_id: int,
        niche_id: int,
        candidate_id: Optional[int] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> PromptPack:
        """Generate a prompt pack (A/B/C variants)."""
        
        niche = session.get(Niche, niche_id)
        if not niche:
            raise ValueError("Niche not found")
            
        candidate = None
        analysis = None
        if candidate_id:
            candidate = session.get(TrendCandidate, candidate_id)
            if candidate and candidate.analysis:
                analysis = candidate.analysis
        
        # Generate 3 variants
        variants = {}
        for variant_type in ["A", "B", "C"]:
            # Logic to vary prompt based on type
            # A: Safe, B: Trend, C: Wild
            
            topic = f"Content for {niche.name}"
            if candidate:
                topic = f"Remix of: {candidate.caption[:50]}..."
            
            # Use script service to generate script
            script = await script_service.generate_with_niche_config(
                topic=topic,
                niche=niche
            )
            
            variants[variant_type] = {
                "script": script.full_script,
                "hook": script.hook,
                "visual_prompt": f"Visuals for {variant_type}: {topic}",
                "reasoning": f"Generated variant {variant_type} based on {topic}"
            }
            
        # Create PromptPack
        pack = PromptPack(
            account_id=account_id,
            niche_id=niche_id,
            source_candidate_id=candidate_id,
            variants=variants,
            caption_data={"default": "Check this out! #viral"},
            hashtags_data={"default": ["#fyp", f"#{niche.slug}"]},
            status="draft"
        )
        
        # Check duplicates
        # We check duplicate against Variant A's hook/script
        text_to_check = variants["A"]["script"]
        dup_result = await memory_service.check_duplicate(session, account_id, niche_id, text_to_check)
        
        if dup_result["is_duplicate"]:
            logger.warning(f"Generated duplicate content: {dup_result}")
            # In real app, we might regenerate or flag it.
            # For now, we save it but maybe mark status?
            # pack.status = "flagged_duplicate"
        
        session.add(pack)
        await session.commit()
        
        # Save to memory index if not duplicate? 
        # Usually we save only approved ones, but let's save drafts for now or wait for approval.
        
        return pack

prompt_service = PromptService()
