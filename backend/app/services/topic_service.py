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


class TopicService:
    """Service for topic generation and selection."""
    
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"
    
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

    def _feeds_file(self, niche_name: str) -> Path:
        return settings.niches_path / niche_name / "feeds.json"

    def _load_feeds(self, niche_name: str) -> List[str]:
        feeds_file = self._feeds_file(niche_name)
        if not feeds_file.exists():
            return []
        try:
            with open(feeds_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("feeds", [])
        except Exception as e:
            logger.warning(f"Failed to load feeds for {niche_name}: {e}")
            return []

    async def _fetch_feed(self, url: str) -> List[Dict[str, str]]:
        """Fetch and parse RSS/Atom feed items."""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.text
        except Exception as e:
            logger.warning(f"Failed to fetch feed {url}: {e}")
            return []

        items = []
        try:
            root = ET.fromstring(content)
            # RSS
            for item in root.findall(".//item"):
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="").strip()
                if title:
                    items.append({"title": title, "link": link})
            # Atom
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title = entry.findtext("{http://www.w3.org/2005/Atom}title", default="").strip()
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.attrib.get("href", "") if link_el is not None else ""
                if title:
                    items.append({"title": title, "link": link})
        except Exception as e:
            logger.warning(f"Failed to parse feed {url}: {e}")
            return []

        return items

    async def get_news_topics(self, niche_name: str, max_items: int = 20) -> List[Dict[str, str]]:
        """Get news topics from RSS/Atom feeds for a niche."""
        feeds = self._load_feeds(niche_name)
        if not feeds:
            return []

        results: List[Dict[str, str]] = []
        for url in feeds:
            results.extend(await self._fetch_feed(url))
            if len(results) >= max_items:
                break

        # Deduplicate by title
        seen = set()
        unique = []
        for item in results:
            title = item.get("title", "")
            if title and title not in seen:
                seen.add(title)
                unique.append(item)
        return unique[:max_items]

    async def pick_best_topic_from_news(
        self,
        niche_name: str,
        niche_description: str,
        news_items: List[Dict[str, str]]
    ) -> Optional[str]:
        """Use LLM to pick best topic from news headlines."""
        if not news_items:
            return None

        headlines = [f"- {i['title']}" for i in news_items[:20]]
        prompt = f"""You are a viral content strategist.

Niche: {niche_name}
Description: {niche_description}

Pick ONE headline that would perform best as a short video.
Return ONLY the headline text exactly as written.

Headlines:
{chr(10).join(headlines)}
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
                choice = data.get("response", "").strip().strip('"\'')
                return choice if choice else None
        except Exception as e:
            logger.warning(f"Failed to rank news headlines: {e}")
            return None
    
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
        news = await self.get_news_topics(niche_name)
        if news:
            choice = await self.pick_best_topic_from_news(niche_name, niche_description, news)
            if choice:
                return choice

        list_topic = self.select_from_list(niche_name)
        if list_topic:
            return list_topic

        return await self.generate_topic(niche_name, niche_description)


topic_service = TopicService()
