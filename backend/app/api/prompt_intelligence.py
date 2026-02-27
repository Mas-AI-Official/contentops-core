from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db import get_async_session
from app.models import Niche, Job
from app.services.prompt_intelligence_service import prompt_intelligence_service
from app.models.prompt_intelligence import PromptBundle

router = APIRouter(prefix="/prompt-intelligence", tags=["prompt-intelligence"])


class AnalyzePromptRequest(BaseModel):
    niche_id: int
    topic: str

@router.post("/build/{job_id}", response_model=PromptBundle)
async def build_prompt_bundle(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    """Generate a prompt bundle for a job."""
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    niche = await session.get(Niche, job.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
        
    try:
        bundle = await prompt_intelligence_service.build_bundle(
            job_id=job.id,
            niche=niche,
            topic=job.topic
        )
        
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)
        return bundle
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bundle/{job_id}", response_model=PromptBundle)
async def get_bundle(
    job_id: int,
    session: Session = Depends(get_async_session)
):
    query = select(PromptBundle).where(PromptBundle.job_id == job_id)
    result = await session.execute(query)
    bundle = result.scalars().first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.post("/analyze")
async def analyze_prompt(
    request: AnalyzePromptRequest,
    session: Session = Depends(get_async_session),
):
    niche = await session.get(Niche, request.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    # Lightweight ad-hoc analysis path (does not require pre-existing job)
    bundle = await prompt_intelligence_service.build_bundle(
        job_id=0,
        niche=niche,
        topic=request.topic,
    )
    return {
        "script_prompt_json": bundle.script_prompt_json,
        "storyboard_json": bundle.storyboard_json,
        "visual_prompts_json": bundle.visual_prompts_json,
        "voice_spec_json": bundle.voice_spec_json,
        "edit_recipe_json": bundle.edit_recipe_json,
        "hashtags_json": bundle.hashtags_json,
        "caption_text": bundle.caption_text,
    }
