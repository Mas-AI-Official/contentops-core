"""
API routes for scraper service - RSS/web scraping for topic harvesting.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.scraper_service import scraper_service
from app.core.config import settings

router = APIRouter(prefix="/scraper", tags=["scraper"])


class ScrapeRequest(BaseModel):
    niche_slug: Optional[str] = None
    force: bool = False
    max_items: int = 20


class FeedsUpdate(BaseModel):
    feeds: List[str]


@router.post("/scrape")
async def scrape_topics(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape topics from RSS feeds.
    
    If niche_slug is provided, scrape only that niche.
    Otherwise, scrape all niches.
    """
    if request.niche_slug:
        result = await scraper_service.scrape_niche(
            request.niche_slug,
            max_items=request.max_items,
            force=request.force
        )
        return result
    else:
        # Scrape all niches in background
        background_tasks.add_task(scraper_service.scrape_all_niches, request.force)
        return {"status": "started", "message": "Scraping all niches in background"}


@router.post("/scrape/{niche_slug}")
async def scrape_niche_topics(
    niche_slug: str,
    force: bool = False,
    max_items: int = 20
):
    """Scrape topics for a specific niche."""
    result = await scraper_service.scrape_niche(
        niche_slug,
        max_items=max_items,
        force=force
    )
    return result


@router.get("/topics/{niche_slug}")
async def get_niche_topics(niche_slug: str, unused_only: bool = False):
    """Get topics for a niche."""
    import json
    topics_file = settings.niches_path / niche_slug / "topics.json"
    
    if not topics_file.exists():
        raise HTTPException(status_code=404, detail="Topics file not found")
    
    try:
        with open(topics_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        topics = data.get("topics", [])
        used = set(data.get("used", []))
        
        if unused_only:
            # Filter to unused topics
            filtered = []
            for t in topics:
                if isinstance(t, dict):
                    if t.get("id") not in used and not t.get("used", False):
                        filtered.append(t)
                elif isinstance(t, str) and t not in used:
                    filtered.append({"title": t, "id": t})
            topics = filtered
        
        return {
            "niche": niche_slug,
            "topics": topics,
            "total": len(topics),
            "used_count": len(used),
            "last_scraped": data.get("last_scraped")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feeds/{niche_slug}")
async def get_niche_feeds(niche_slug: str):
    """Get RSS feeds configured for a niche."""
    import json
    feeds_file = settings.niches_path / niche_slug / "feeds.json"
    
    if not feeds_file.exists():
        # Return default feeds
        default_feeds = scraper_service.get_default_feeds_for_niche(niche_slug)
        return {
            "niche": niche_slug,
            "feeds": default_feeds,
            "is_default": True
        }
    
    try:
        with open(feeds_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "niche": niche_slug,
            "feeds": data.get("feeds", []),
            "is_default": False,
            "updated_at": data.get("updated_at")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/feeds/{niche_slug}")
async def update_niche_feeds(niche_slug: str, update: FeedsUpdate):
    """Update RSS feeds for a niche."""
    import json
    from datetime import datetime
    
    feeds_file = settings.niches_path / niche_slug / "feeds.json"
    feeds_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(feeds_file, "w", encoding="utf-8") as f:
            json.dump({
                "feeds": update.feeds,
                "updated_at": datetime.utcnow().isoformat()
            }, f, indent=2)
        
        return {
            "status": "updated",
            "niche": niche_slug,
            "feeds_count": len(update.feeds)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed-feeds/{niche_slug}")
async def seed_niche_feeds(niche_slug: str, niche_name: Optional[str] = None):
    """Seed default RSS feeds for a niche."""
    name = niche_name or niche_slug.replace("-", " ").replace("_", " ")
    success = scraper_service.seed_niche_feeds(niche_slug, name)
    
    if success:
        return {"status": "seeded", "niche": niche_slug}
    else:
        raise HTTPException(status_code=500, detail="Failed to seed feeds")


class MarkTopicUsedBody(BaseModel):
    topic_id: str


@router.post("/topics/{niche_slug}/mark-used")
async def mark_topic_used(niche_slug: str, body: MarkTopicUsedBody):
    """Mark a specific topic as used."""
    ok = scraper_service.mark_topic_used(niche_slug, body.topic_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to mark topic as used")
    return {"marked_used": True, "topic_id": body.topic_id}


@router.post("/pick-topic/{niche_slug}")
async def pick_unused_topic(niche_slug: str):
    """Pick an unused topic from a niche and mark it as used."""
    topic = scraper_service.get_unused_topic(niche_slug)
    
    if not topic:
        raise HTTPException(status_code=404, detail="No unused topics available")
    
    # Mark as used
    topic_id = topic.get("id") or topic.get("title", "")
    scraper_service.mark_topic_used(niche_slug, topic_id)
    
    return {
        "topic": topic,
        "marked_used": True
    }
