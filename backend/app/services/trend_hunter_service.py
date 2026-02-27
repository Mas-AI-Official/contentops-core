"""
Trend Hunter Service - Autonomous loop for scraping and script generation.
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlmodel import Session, select

from app.core.config import settings
from app.services.mcp_service import mcp_service
from app.db import get_sync_session
from app.models import Niche, Job, JobStatus, JobType
import httpx

class TrendHunterService:
    """Service to independently scrape trends and generate video jobs."""

    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"

    async def _call_mcp_with_retry(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        max_attempts: int = 3,
        delay_seconds: float = 2.0,
    ) -> Dict[str, Any]:
        """Call MCP tool with retries and backoff to handle transient failures."""
        last_error = None
        for attempt in range(max_attempts):
            try:
                result = await mcp_service.call_tool(server_name, tool_name, arguments)
                if "error" not in result:
                    return result
                last_error = result.get("message", result.get("error", "unknown"))
            except Exception as e:
                last_error = str(e)
                logger.debug(f"MCP {server_name}/{tool_name} attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay_seconds)
        return {"error": "tool_call_failed", "message": last_error or "All connection attempts failed"}

    async def hunt_trends(self, niche_slug: str) -> List[str]:
        """Scrape trending topics for a specific niche using MCP servers."""
        logger.info(f"Hunting trends for niche: {niche_slug}")
        
        trends = []
        
        # 0. Check for existing unused scraped topics first
        from app.services.scraper_service import scraper_service
        try:
            unused_topic = scraper_service.pick_topic(niche_slug, mark_used=True)
            if unused_topic and unused_topic.get("title"):
                logger.info(f"Found unused scraped topic for {niche_slug}: {unused_topic['title']}")
                return [unused_topic["title"]]
        except Exception as e:
            logger.warning(f"Failed to check scraper topics: {e}")
        
        # 1. Use Xpoz MCP for Twitter/TikTok trends (with retries)
        try:
            xpoz_result = await self._call_mcp_with_retry(
                server_name="xpoz",
                tool_name="get_trending_topics",
                arguments={"niche": niche_slug, "count": 5},
            )
            if "data" in xpoz_result:
                trends.extend(xpoz_result["data"])
        except Exception as e:
            logger.warning(f"Xpoz trend scraping failed: {e}")

        # 2. Use YouTube Data MCP (with retries)
        try:
            yt_result = await self._call_mcp_with_retry(
                server_name="youtube_data",
                tool_name="search_trending_videos",
                arguments={"query": niche_slug, "count": 3},
            )
            if "data" in yt_result:
                trends.extend([v.get("title") for v in yt_result["data"]])
        except Exception as e:
            logger.warning(f"YouTube trend scraping failed: {e}")

        # 3. Fallback: Use internal scraper sources
        if not trends:
            logger.info("Falling back to internal scraper for trends...")
            from app.services.scraper_service import scraper_service
            try:
                for source in ["youtube_trending", "reddit", "google_trends"]:
                    internal_trends = scraper_service.scrape_trends(source, niche_slug)
                    if internal_trends:
                        trends.extend([v.get("title") for v in internal_trends if v.get("title")])
            except Exception as e:
                 logger.warning(f"Internal scraper failed: {e}")

        # 4. Final Fallback: Ask LLM for trends
        if not trends:
             logger.info("Falling back to LLM for trending topics...")
             from app.services.topic_service import topic_service
             try:
                 llm_trends = await topic_service.get_trending_topics(niche_slug, count=3)
                 if llm_trends:
                     trends.extend(llm_trends)
             except Exception as e:
                  logger.warning(f"LLM trend generation failed: {e}")

        # Remove duplicates and empty strings
        return list(set([t for t in trends if t and isinstance(t, str)]))

    async def generate_autonomous_job(self, niche: Niche, trend_data: str, auto_publish: bool = False):
        """Use Ollama to generate a complete structured job from trend data."""
        logger.info(f"Generating autonomous job for niche {niche.name} from trend: {trend_data}")
        
        prompt = f"""
        Act as a Viral Content Director. Build a 60-second video script about: "{trend_data}"
        
        Target Niche: {niche.name} ({niche.description})
        
        OUTPUT FORMAT (STRICT JSON ONLY):
        {{
          "topic": "Engaging Title",
          "script": "The spoken narration script, conversational and punchy.",
          "visual_prompts": [
            "Detailed scene 1 description for video generation",
            "Detailed scene 2 description for video generation",
            "Detailed scene 3 description for video generation",
            "Detailed scene 4 description for video generation",
            "Detailed scene 5 description for video generation"
          ],
          "caption": "Social media caption",
          "hashtags": ["list", "of", "hashtags"],
          "estimated_duration": 60
        }}
        
        Requirement: The script must be optimized for speech (approx 150 words).
        """

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": settings.ollama_reasoning_model, # Use reasoning model (deepseek-r1:7b)
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "keep_alive": 0  # Unload from VRAM immediately
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "").strip()
                # Strip markdown code block if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = "\n".join(lines)
                
                # Parse JSON
                job_data = json.loads(content)
                
                # Safe extraction with defaults (LLM may omit or rename keys)
                topic = job_data.get("topic") or trend_data or "Generated topic"
                script = job_data.get("script") or job_data.get("full_script") or ""
                raw_visual = job_data.get("visual_prompts")
                if isinstance(raw_visual, list) and len(raw_visual) > 0:
                    visual_prompts = raw_visual
                else:
                    # Derive from script lines (like studio_service) or single topic
                    visual_prompts = [line.strip() for line in script.split("\n") if len(line.strip()) > 20]
                    if not visual_prompts:
                        visual_prompts = [topic]
                
                # Create the job in the DB
                with get_sync_session() as session:
                    new_job = Job(
                        niche_id=niche.id,
                        topic=topic,
                        full_script=script,
                        visual_cues=json.dumps(visual_prompts),
                        status=JobStatus.PENDING,
                        job_type=JobType.GENERATE_AND_PUBLISH if auto_publish else JobType.GENERATE_ONLY,
                        publish_youtube=niche.post_to_youtube,
                        publish_instagram=niche.post_to_instagram,
                        publish_tiktok=niche.post_to_tiktok,
                        created_at=datetime.utcnow()
                    )
                    session.add(new_job)
                    session.commit()
                    logger.info(f"Autonomous job created: ID {new_job.id}")
                    return new_job
                    
        except Exception as e:
            logger.error(f"Failed to generate autonomous job: {e}")
            return None

    async def run_hunter_cycle(self):
        """Main loop to process all active niches."""
        logger.info("Starting Trend Hunter cycle...")
        
        with get_sync_session() as session:
            niches = session.exec(
                select(Niche).where(Niche.is_active == True).where(Niche.auto_mode == True)
            ).all()
            
            for niche in niches:
                # Cooldown guard to avoid generating too many jobs for same niche.
                cutoff = datetime.utcnow() - timedelta(minutes=settings.autopilot_job_cooldown_minutes)
                existing = session.exec(
                    select(Job)
                    .where(Job.niche_id == niche.id)
                    .where(Job.created_at >= cutoff)
                    .where(Job.status.in_([JobStatus.PENDING, JobStatus.QUEUED, JobStatus.GENERATING_SCRIPT, JobStatus.GENERATING_AUDIO, JobStatus.GENERATING_SUBTITLES, JobStatus.RENDERING, JobStatus.READY_FOR_REVIEW]))
                ).first()
                if existing:
                    logger.info(
                        f"Skipping niche {niche.name}: recent/in-flight job {existing.id} exists within cooldown window."
                    )
                    continue

                trends = await self.hunt_trends(niche.slug or niche.name.lower())
                if not trends:
                    logger.info(f"No trends found for {niche.name}, skipping.")
                    continue
                
                # Pick the top trend
                top_trend = trends[0]
                
                # Generate job
                await self.generate_autonomous_job(
                    niche=niche,
                    trend_data=top_trend,
                    auto_publish=bool(settings.auto_publish_on_autopilot),
                )

trend_hunter_service = TrendHunterService()
