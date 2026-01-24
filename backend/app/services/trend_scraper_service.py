import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from loguru import logger
from app.models.trends import TrendCandidate

class ScraperAdapter(ABC):
    @abstractmethod
    async def discover_trends(self, niche: str, region: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> TrendCandidate:
        pass

class MockAdapter(ScraperAdapter):
    def __init__(self, platform: str):
        self.platform = platform
        
    async def discover_trends(self, niche: str, region: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Return mock data
        return [
            {
                "id": f"mock_{self.platform}_{i}",
                "url": f"https://{self.platform}.com/video/{i}",
                "creator": f"creator_{i}",
                "caption": f"This is a trending video about {niche} #{niche} #viral",
                "hashtags": [niche, "viral", "trending"],
                "metrics": {"views": 1000 * i, "likes": 100 * i},
                "platform": self.platform
            }
            for i in range(1, limit + 1)
        ]
        
    def normalize(self, raw_data: Dict[str, Any]) -> TrendCandidate:
        return TrendCandidate(
            platform=raw_data["platform"],
            source_id=raw_data["id"],
            url=raw_data["url"],
            creator=raw_data["creator"],
            caption=raw_data["caption"],
            hashtags=raw_data["hashtags"],
            metrics=raw_data["metrics"],
            discovered_at=datetime.utcnow()
        )

class TrendScraperService:
    def __init__(self):
        self.adapters: Dict[str, ScraperAdapter] = {
            "instagram": MockAdapter("instagram"),
            "tiktok": MockAdapter("tiktok"),
            "youtube": MockAdapter("youtube"),
        }
    
    async def scan_niche(self, niche: str, platforms: List[str], region: str = "US", limit: int = 10) -> List[TrendCandidate]:
        results = []
        for platform in platforms:
            adapter = self.adapters.get(platform)
            if adapter:
                try:
                    raw_items = await adapter.discover_trends(niche, region, limit)
                    candidates = [adapter.normalize(item) for item in raw_items]
                    results.extend(candidates)
                except Exception as e:
                    logger.error(f"Error scraping {platform} for {niche}: {e}")
        return results

trend_scraper_service = TrendScraperService()
