"""
Trend Service - Fetches trending topics from Google Trends and other sources.
"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from loguru import logger
import urllib.parse

class TrendService:
    """Service for fetching trending topics."""
    
    def __init__(self):
        self.google_trends_url = "https://trends.google.com/trends/trendingsearches/daily/rss"
    
    async def get_google_trends(self, geo: str = "US") -> List[Dict[str, Any]]:
        """
        Fetch daily trending searches from Google Trends.
        
        Args:
            geo: Country code (US, CA, GB, etc.)
        """
        url = f"{self.google_trends_url}?geo={geo}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.text
                
            root = ET.fromstring(content)
            trends = []
            
            # Namespace for Google Trends extensions
            ns = {'ht': 'https://trends.google.com/trends/trendingsearches/daily'}
            
            for item in root.findall(".//item"):
                title = item.findtext("title")
                description = item.findtext("description")
                pub_date = item.findtext("pubDate")
                approx_traffic = item.findtext("ht:approx_traffic", namespaces=ns)
                picture = item.findtext("ht:picture", namespaces=ns)
                news_items = []
                
                for news in item.findall("ht:news_item", namespaces=ns):
                    news_title = news.findtext("ht:news_item_title", namespaces=ns)
                    news_url = news.findtext("ht:news_item_url", namespaces=ns)
                    if news_title and news_url:
                        news_items.append({"title": news_title, "url": news_url})
                
                if title:
                    trends.append({
                        "topic": title,
                        "description": description,
                        "traffic": approx_traffic,
                        "pub_date": pub_date,
                        "picture": picture,
                        "news": news_items,
                        "source": "google_trends"
                    })
            
            logger.info(f"Fetched {len(trends)} trends for {geo}")
            return trends
            
        except Exception as e:
            logger.error(f"Failed to fetch Google Trends: {e}")
            return []

    async def get_niche_trends(self, niche_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Get trending topics relevant to specific keywords.
        Since Google Trends RSS is general, we filter or use related queries.
        For now, we'll fetch general trends and score them against keywords,
        plus use a news search for the keywords.
        """
        # 1. Get General Trends
        general_trends = await self.get_google_trends()
        
        # 2. Filter/Score based on keywords (simple string matching for now)
        relevant_trends = []
        for trend in general_trends:
            trend_text = (trend['topic'] + " " + trend['description']).lower()
            score = 0
            for kw in niche_keywords:
                if kw.lower() in trend_text:
                    score += 1
            
            if score > 0:
                trend['relevance'] = score
                relevant_trends.append(trend)
        
        # 3. If no direct matches, fetch News for keywords
        if not relevant_trends:
            for kw in niche_keywords[:3]: # Limit to top 3 keywords
                news = await self._fetch_news_topic(kw)
                relevant_trends.extend(news)
        
        return relevant_trends

    async def _fetch_news_topic(self, query: str) -> List[Dict[str, Any]]:
        """Fetch news for a specific query (using Google News RSS)."""
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return []
                content = response.text
                
            root = ET.fromstring(content)
            items = []
            
            for item in root.findall(".//item")[:5]: # Top 5 only
                title = item.findtext("title")
                link = item.findtext("link")
                pub_date = item.findtext("pubDate")
                
                if title:
                    items.append({
                        "topic": title,
                        "description": f"News about {query}",
                        "url": link,
                        "pub_date": pub_date,
                        "source": "google_news",
                        "keyword": query
                    })
            return items
        except Exception as e:
            logger.warning(f"Failed to fetch news for {query}: {e}")
            return []

trend_service = TrendService()
