"""
Topic service - generates or selects topics for video content.
Supports RSS/Atom feeds for automated news-based topics.
"""
import json
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict
import httpx
from loguru import logger

from app.core.config import settings


from app.services.scraper_service import scraper_service

class TopicService:
    """Service for topic generation and selection."""
    
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"
    
    async def generate_topic_from_rss(self, niche_slug: str) -> Optional[str]:
        """Get an unused topic from the niche's scraped pool."""
        topic_data = scraper_service.get_unused_topic(niche_slug)
        if topic_data:
            topic_id = topic_data.get("id")
            title = topic_data.get("title")
            
            # Mark as used immediately to avoid duplicates
            if topic_id:
                scraper_service.mark_topic_used(niche_slug, topic_id)
                
            logger.info(f"Selected RSS topic for {niche_slug}: {title}")
            return title
            
        # If no topics, try to scrape fresh ones
        logger.info(f"No unused topics for {niche_slug}, triggering scrape...")
        await scraper_service.scrape_niche(niche_slug)
        
        # Try again
        topic_data = scraper_service.get_unused_topic(niche_slug)
        if topic_data:
            topic_id = topic_data.get("id")
            title = topic_data.get("title")
            if topic_id:
                scraper_service.mark_topic_used(niche_slug, topic_id)
            return title
            
        return None

    async def generate_topic(self, niche_name: str, niche_description: str) -> str:
        """Generate a new topic using LLM."""
        prompt = f"""You are a content strategist for viral short-form videos.

Niche: {niche_name}
Description: {niche_description}

Generate ONE specific, engaging video topic that would perform well on TikTok, YouTube Shorts, and Instagram Reels.
The topic should be:
- Specific and actionable
- Emotionally engaging or surprising
- Easy to explain in 60 seconds or less

Return ONLY the topic title, nothing else. No quotes, no explanation.
"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": settings.ollama_fast_model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                topic = data.get("response", "").strip()
                
                # Clean up the topic
                topic = topic.strip('"\'')
                if topic.startswith("Topic:"):
                    topic = topic[6:].strip()
                
                logger.info(f"Generated topic: {topic}")
                return topic
                
        except Exception as e:
            logger.error(f"Failed to generate topic: {e}")
            raise

    def select_from_list(self, niche_name: str) -> Optional[str]:
        """Select a topic from a pre-defined list for the niche."""
        topics_file = settings.niches_path / niche_name / "topics.json"
        
        if not topics_file.exists():
            logger.warning(f"No topics file found for niche: {niche_name}")
            return None
        
        try:
            with open(topics_file, "r") as f:
                data = json.load(f)
            
            topics = data.get("topics", [])
            used = set(data.get("used", []))
            
            # Filter out used topics
            available = [t for t in topics if t not in used]
            
            if not available:
                # Reset used list if all topics exhausted
                available = topics
                data["used"] = []
            
            if not available:
                return None
            
            # Select random topic
            topic = random.choice(available)
            
            # Mark as used
            data["used"].append(topic)
            with open(topics_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Selected topic from list: {topic}")
            return topic
            
        except Exception as e:
            logger.error(f"Failed to select topic from list: {e}")
            return None
    
    async def get_trending_topics(self, niche_name: str, count: int = 5) -> List[str]:
        """Generate multiple trending topic ideas."""
        prompt = f"""You are a viral content strategist.

Generate {count} trending video topic ideas for the "{niche_name}" niche.
These should be topics that would perform well on TikTok, YouTube Shorts, and Instagram Reels right now.

Format: Return a JSON array of topic strings only.
Example: ["Topic 1", "Topic 2", "Topic 3"]
"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": settings.ollama_fast_model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "").strip()
                
                # Parse JSON from response
                # Find JSON array in response
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    topics = json.loads(text[start:end])
                    return topics[:count]
                
                return []
                
        except Exception as e:
            logger.error(f"Failed to get trending topics: {e}")
            return []

    async def generate_topic_auto(self, niche_name: str, niche_description: str) -> str:
        """Auto-pick topic: RSS news > saved list > LLM."""
        # 1. Try RSS/Scraped topics first
        rss_topic = await self.generate_topic_from_rss(niche_name)
        if rss_topic:
            return rss_topic

        # 2. Try manual list
        list_topic = self.select_from_list(niche_name)
        if list_topic:
            return list_topic

        # 3. Fallback to LLM generation
        return await self.generate_topic(niche_name, niche_description)


topic_service = TopicService()
