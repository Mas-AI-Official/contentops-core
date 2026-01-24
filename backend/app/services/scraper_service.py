"""
Scraper Service - Automated topic harvesting from RSS feeds and web sources.

Handles:
- Fetching from RSS/Atom feeds (primary)
- Simple web scraping for allowed domains (optional)
- Topic deduplication and scoring
- Automatic topic storage in niche folders
"""
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import xml.etree.ElementTree as ET
import httpx
from loguru import logger

from app.core.config import settings


# Default RSS feeds for common content niches
DEFAULT_RSS_FEEDS = {
    # AI & Tech
    "ai_tools": [
        "https://news.google.com/rss/search?q=AI+tools+productivity&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=artificial+intelligence+apps&hl=en-US&gl=US&ceid=US:en",
        "https://www.reddit.com/r/artificial/.rss",
    ],
    "tech_news": [
        "https://news.google.com/rss/search?q=technology+news&hl=en-US&gl=US&ceid=US:en",
        "https://www.reddit.com/r/technology/.rss",
        "https://hnrss.org/frontpage?points=100",
    ],
    # Finance - Canada
    "finance_canada": [
        "https://news.google.com/rss/search?q=Canada+personal+finance&hl=en-CA&gl=CA&ceid=CA:en",
        "https://www.reddit.com/r/PersonalFinanceCanada/.rss",
        "https://news.google.com/rss/search?q=Canadian+money+saving&hl=en-CA&gl=CA&ceid=CA:en",
    ],
    # Health
    "health_tips": [
        "https://news.google.com/rss/search?q=health+tips+natural&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=nutrition+science+benefits&hl=en-US&gl=US&ceid=US:en",
    ],
    # Productivity / Life Systems
    "productivity": [
        "https://news.google.com/rss/search?q=productivity+hacks&hl=en-US&gl=US&ceid=US:en",
        "https://www.reddit.com/r/productivity/.rss",
        "https://www.reddit.com/r/getdisciplined/.rss",
    ],
    # Cooking
    "cooking": [
        "https://www.reddit.com/r/Cooking/.rss",
        "https://www.reddit.com/r/recipes/.rss",
        "https://news.google.com/rss/search?q=cooking+hacks+tips&hl=en-US&gl=US&ceid=US:en",
    ],
    # Beauty & Fashion
    "beauty": [
        "https://www.reddit.com/r/SkincareAddiction/.rss",
        "https://news.google.com/rss/search?q=beauty+trends+2024&hl=en-US&gl=US&ceid=US:en",
    ],
    "fashion": [
        "https://www.reddit.com/r/femalefashionadvice/.rss",
        "https://news.google.com/rss/search?q=fashion+trends+affordable&hl=en-US&gl=US&ceid=US:en",
    ],
    # Home & Pets
    "home_decor": [
        "https://www.reddit.com/r/HomeImprovement/.rss",
        "https://news.google.com/rss/search?q=DIY+home+decor+budget&hl=en-US&gl=US&ceid=US:en",
    ],
    "pet_care": [
        "https://www.reddit.com/r/dogs/.rss",
        "https://www.reddit.com/r/cats/.rss",
        "https://news.google.com/rss/search?q=pet+care+tips&hl=en-US&gl=US&ceid=US:en",
    ],
    # Entertainment
    "comedy": [
        "https://www.reddit.com/r/funny/.rss",
        "https://news.google.com/rss/search?q=viral+funny+moments&hl=en-US&gl=US&ceid=US:en",
    ],
    "life_hacks": [
        "https://www.reddit.com/r/lifehacks/.rss",
        "https://news.google.com/rss/search?q=life+hacks+tips&hl=en-US&gl=US&ceid=US:en",
    ],
    # Default fallback
    "default": [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
    ]
}


class ScraperService:
    """Service for automated topic harvesting."""
    
    def __init__(self):
        self.http_client = None
        self._last_scrape: Dict[str, datetime] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
        return self.http_client
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
    
    def _get_niche_feeds_file(self, niche_slug: str) -> Path:
        """Get the feeds.json path for a niche."""
        return settings.niches_path / niche_slug / "feeds.json"
    
    def _get_niche_topics_file(self, niche_slug: str) -> Path:
        """Get the topics.json path for a niche."""
        return settings.niches_path / niche_slug / "topics.json"
    
    def get_default_feeds_for_niche(self, niche_name: str) -> List[str]:
        """Get default RSS feeds based on niche name/type."""
        name_lower = niche_name.lower()
        
        # Match niche to feed category
        if "ai" in name_lower or "tech" in name_lower:
            if "save" in name_lower or "money" in name_lower:
                return DEFAULT_RSS_FEEDS["finance_canada"] + DEFAULT_RSS_FEEDS["ai_tools"]
            return DEFAULT_RSS_FEEDS["ai_tools"] + DEFAULT_RSS_FEEDS["tech_news"]
        elif "money" in name_lower or "finance" in name_lower or "micro" in name_lower:
            return DEFAULT_RSS_FEEDS["finance_canada"]
        elif "health" in name_lower or "ginger" in name_lower:
            return DEFAULT_RSS_FEEDS["health_tips"]
        elif "cooking" in name_lower or "recipe" in name_lower or "kitchen" in name_lower:
            return DEFAULT_RSS_FEEDS["cooking"]
        elif "beauty" in name_lower or "makeup" in name_lower or "skin" in name_lower:
            return DEFAULT_RSS_FEEDS["beauty"]
        elif "fashion" in name_lower or "outfit" in name_lower or "style" in name_lower:
            return DEFAULT_RSS_FEEDS["fashion"]
        elif "home" in name_lower or "decor" in name_lower or "diy" in name_lower:
            return DEFAULT_RSS_FEEDS["home_decor"]
        elif "pet" in name_lower or "dog" in name_lower or "cat" in name_lower:
            return DEFAULT_RSS_FEEDS["pet_care"]
        elif "comedy" in name_lower or "funny" in name_lower or "sketch" in name_lower:
            return DEFAULT_RSS_FEEDS["comedy"]
        elif "hack" in name_lower or "life" in name_lower or "system" in name_lower or "productivity" in name_lower:
            return DEFAULT_RSS_FEEDS["life_hacks"] + DEFAULT_RSS_FEEDS["productivity"]
        else:
            return DEFAULT_RSS_FEEDS["default"]
    
    async def fetch_rss_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse an RSS/Atom feed."""
        client = await self._get_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            logger.warning(f"Failed to fetch feed {url}: {e}")
            return []
        
        items = []
        try:
            root = ET.fromstring(content)
            
            # Parse RSS format
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                description = (item.findtext("description") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                
                if title:
                    items.append({
                        "id": hashlib.md5(f"{title}{link}".encode()).hexdigest()[:12],
                        "title": title,
                        "url": link,
                        "summary": description[:500] if description else "",
                        "source": url,
                        "published_at": pub_date,
                        "created_at": datetime.utcnow().isoformat(),
                        "used": False,
                        "score": 50 + (10 if description else 0) + (len(title) % 20)  # Simple deterministic pseudo-score
                    })
            
            # Parse Atom format
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = entry.findtext("atom:title", default="", namespaces=ns).strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.attrib.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", default="", namespaces=ns).strip()
                content_el = entry.findtext("atom:content", default="", namespaces=ns).strip()
                published = entry.findtext("atom:published", default="", namespaces=ns).strip()
                
                if title:
                    items.append({
                        "id": hashlib.md5(f"{title}{link}".encode()).hexdigest()[:12],
                        "title": title,
                        "url": link,
                        "summary": (summary or content_el)[:500],
                        "source": url,
                        "published_at": published,
                        "created_at": datetime.utcnow().isoformat(),
                        "used": False,
                        "score": 60 + (len(title) % 30)  # Simple deterministic pseudo-score
                    })
                    
        except ET.ParseError as e:
            logger.warning(f"Failed to parse feed {url}: {e}")
            return []
        
        logger.info(f"Fetched {len(items)} items from {url}")
        return items
    
    async def scrape_niche(
        self, 
        niche_slug: str, 
        max_items: int = 20,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape topics for a specific niche.
        
        Args:
            niche_slug: The niche folder name (slug)
            max_items: Maximum items to store per scrape
            force: Force scrape even if recently scraped
            
        Returns:
            Dict with scrape results
        """
        # Check if we recently scraped this niche
        last_scrape = self._last_scrape.get(niche_slug)
        if last_scrape and not force:
            if datetime.utcnow() - last_scrape < timedelta(hours=4):
                logger.info(f"Skipping {niche_slug} - scraped recently")
                return {"status": "skipped", "reason": "recently_scraped"}
        
        feeds_file = self._get_niche_feeds_file(niche_slug)
        topics_file = self._get_niche_topics_file(niche_slug)
        
        # Load or create feeds
        feeds = []
        if feeds_file.exists():
            try:
                with open(feeds_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                feeds = data.get("feeds", [])
            except Exception as e:
                logger.error(f"Error loading feeds for {niche_slug}: {e}")
        
        # If no feeds configured, use defaults
        if not feeds:
            feeds = self.get_default_feeds_for_niche(niche_slug)
            # Save default feeds
            feeds_file.parent.mkdir(parents=True, exist_ok=True)
            with open(feeds_file, "w", encoding="utf-8") as f:
                json.dump({"feeds": feeds, "updated_at": datetime.utcnow().isoformat()}, f, indent=2)
            logger.info(f"Created default feeds for {niche_slug}: {len(feeds)} feeds")
        
        # Fetch all feeds
        all_items = []
        for feed_url in feeds:
            items = await self.fetch_rss_feed(feed_url)
            all_items.extend(items)
        
        # Deduplicate by title similarity
        seen_titles = set()
        unique_items = []
        for item in all_items:
            title_key = item["title"].lower()[:50]  # First 50 chars for comparison
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
        
        # Load existing topics
        existing_topics = {"topics": [], "used": []}
        if topics_file.exists():
            try:
                with open(topics_file, "r", encoding="utf-8") as f:
                    existing_topics = json.load(f)
            except Exception:
                pass
        
        # Merge new items with existing (avoid duplicates)
        existing_ids = {t.get("id") for t in existing_topics.get("topics", []) if isinstance(t, dict)}
        existing_titles = {t.get("title", "").lower() for t in existing_topics.get("topics", []) if isinstance(t, dict)}
        
        new_items = []
        for item in unique_items:
            if item["id"] not in existing_ids and item["title"].lower() not in existing_titles:
                new_items.append(item)
        
        # Add new items to topics
        updated_topics = existing_topics.get("topics", [])
        # Handle legacy string topics
        updated_topics = [t if isinstance(t, dict) else {"title": t, "id": hashlib.md5(t.encode()).hexdigest()[:12], "used": False, "score": 0} for t in updated_topics]
        updated_topics.extend(new_items[:max_items])
        
        # Sort by score descending to prioritize high-value topics
        updated_topics.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Save updated topics
        topics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(topics_file, "w", encoding="utf-8") as f:
            json.dump({
                "topics": updated_topics,
                "used": existing_topics.get("used", []),
                "last_scraped": datetime.utcnow().isoformat(),
                "auto_sources": feeds
            }, f, indent=2, ensure_ascii=False)
        
        self._last_scrape[niche_slug] = datetime.utcnow()
        
        logger.info(f"Scraped {niche_slug}: {len(new_items)} new topics (total: {len(updated_topics)})")
        
        return {
            "status": "success",
            "niche": niche_slug,
            "new_topics": len(new_items),
            "total_topics": len(updated_topics),
            "feeds_used": len(feeds)
        }
    
    async def scrape_all_niches(self, force: bool = False) -> Dict[str, Any]:
        """Scrape topics for all niches."""
        results = []
        
        if not settings.niches_path.exists():
            return {"status": "error", "message": "Niches path does not exist"}
        
        for niche_dir in settings.niches_path.iterdir():
            if niche_dir.is_dir() and not niche_dir.name.startswith("."):
                try:
                    result = await self.scrape_niche(niche_dir.name, force=force)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error scraping {niche_dir.name}: {e}")
                    results.append({"status": "error", "niche": niche_dir.name, "error": str(e)})
                
                # Small delay between niches to avoid rate limiting
                await asyncio.sleep(1)
        
        return {
            "status": "completed",
            "niches_processed": len(results),
            "results": results
        }
    
    def get_unused_topic(self, niche_slug: str) -> Optional[Dict[str, Any]]:
        """Get an unused topic from a niche's topic list."""
        topics_file = self._get_niche_topics_file(niche_slug)
        
        if not topics_file.exists():
            return None
        
        try:
            with open(topics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading topics for {niche_slug}: {e}")
            return None
        
        topics = data.get("topics", [])
        used_ids = set(data.get("used", []))
        
        # Find first unused topic
        for topic in topics:
            if isinstance(topic, dict):
                topic_id = topic.get("id", topic.get("title", ""))
                if topic_id not in used_ids and not topic.get("used", False):
                    return topic
            elif isinstance(topic, str) and topic not in used_ids:
                return {"title": topic, "id": topic}
        
        # If all topics used, reset and return first
        if topics:
            logger.info(f"All topics used for {niche_slug}, resetting...")
            data["used"] = []
            with open(topics_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            first_topic = topics[0]
            if isinstance(first_topic, dict):
                return first_topic
            return {"title": first_topic, "id": first_topic}
        
        return None
    
    def mark_topic_used(self, niche_slug: str, topic_id: str) -> bool:
        """Mark a topic as used."""
        topics_file = self._get_niche_topics_file(niche_slug)
        
        if not topics_file.exists():
            return False
        
        try:
            with open(topics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            used = data.get("used", [])
            if topic_id not in used:
                used.append(topic_id)
                data["used"] = used
            
            # Also mark in topics array if it's a dict
            for topic in data.get("topics", []):
                if isinstance(topic, dict) and topic.get("id") == topic_id:
                    topic["used"] = True
                    break
            
            with open(topics_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error marking topic used for {niche_slug}: {e}")
            return False
    
    def seed_niche_feeds(self, niche_slug: str, niche_name: str) -> bool:
        """Seed default RSS feeds for a new niche."""
        feeds_file = self._get_niche_feeds_file(niche_slug)
        feeds = self.get_default_feeds_for_niche(niche_name)
        
        try:
            feeds_file.parent.mkdir(parents=True, exist_ok=True)
            with open(feeds_file, "w", encoding="utf-8") as f:
                json.dump({
                    "feeds": feeds,
                    "created_at": datetime.utcnow().isoformat()
                }, f, indent=2)
            logger.info(f"Seeded {len(feeds)} feeds for {niche_slug}")
            return True
        except Exception as e:
            logger.error(f"Failed to seed feeds for {niche_slug}: {e}")
            return False


# Global instance
scraper_service = ScraperService()
