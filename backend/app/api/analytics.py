"""
API routes for analytics.
"""
from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session, select

from app.db import get_async_session, get_sync_session
from app.models import VideoMetrics, VideoScore, Video, DailyNicheStats, Niche
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """Get analytics summary."""
    # Use sync session for analytics service
    with get_sync_session() as sync_session:
        return analytics_service.get_summary(sync_session, niche_id)


@router.get("/trends")
async def get_trends(
    days: int = 30,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """Get metrics trends over time."""
    with get_sync_session() as sync_session:
        return analytics_service.get_trends(sync_session, days, niche_id)


@router.get("/top-videos")
async def get_top_videos(
    limit: int = 10,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """Get top performing videos."""
    query = (
        select(VideoScore, Video)
        .join(Video, VideoScore.video_id == Video.id)
        .where(VideoScore.is_winner == True)
        .order_by(VideoScore.virality_score.desc())
        .limit(limit)
    )
    
    if niche_id:
        query = query.where(Video.niche_id == niche_id)
    
    result = await session.execute(query)
    rows = result.all()
    
    return [
        {
            "video_id": video.id,
            "title": video.title,
            "niche_id": video.niche_id,
            "views_velocity": score.views_velocity,
            "engagement_score": score.engagement_score,
            "virality_score": score.virality_score,
            "created_at": video.created_at.isoformat()
        }
        for score, video in rows
    ]


@router.get("/underperformers")
async def get_underperformers(
    limit: int = 10,
    niche_id: Optional[int] = None,
    session: Session = Depends(get_async_session)
):
    """Get underperforming videos for analysis."""
    query = (
        select(VideoScore, Video)
        .join(Video, VideoScore.video_id == Video.id)
        .where(VideoScore.is_underperformer == True)
        .order_by(VideoScore.virality_score.asc())
        .limit(limit)
    )
    
    if niche_id:
        query = query.where(Video.niche_id == niche_id)
    
    result = await session.execute(query)
    rows = result.all()
    
    return [
        {
            "video_id": video.id,
            "title": video.title,
            "niche_id": video.niche_id,
            "views_velocity": score.views_velocity,
            "engagement_score": score.engagement_score,
            "virality_score": score.virality_score,
            "created_at": video.created_at.isoformat()
        }
        for score, video in rows
    ]


@router.get("/by-niche")
async def get_analytics_by_niche(
    session: Session = Depends(get_async_session)
):
    """Get analytics breakdown by niche."""
    result = await session.execute(select(Niche))
    niches = result.scalars().all()
    
    niche_stats = []
    with get_sync_session() as sync_session:
        for niche in niches:
            summary = analytics_service.get_summary(sync_session, niche.id)
            niche_stats.append({
                "niche_id": niche.id,
                "niche_name": niche.name,
                **summary
            })
    
    return niche_stats


@router.get("/by-platform")
async def get_analytics_by_platform(
    session: Session = Depends(get_async_session)
):
    """Get analytics breakdown by platform."""
    platforms = ["youtube", "instagram", "tiktok"]
    
    result = []
    for platform in platforms:
        metrics_result = await session.execute(
            select(VideoMetrics).where(VideoMetrics.platform == platform)
        )
        metrics = metrics_result.scalars().all()
        
        total_views = sum(m.views for m in metrics)
        total_likes = sum(m.likes for m in metrics)
        total_comments = sum(m.comments for m in metrics)
        
        result.append({
            "platform": platform,
            "total_videos": len(set(m.video_id for m in metrics)),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_engagement_rate": (total_likes + total_comments) / max(total_views, 1)
        })
    
    return result


@router.post("/refresh")
async def refresh_analytics(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_async_session)
):
    """Trigger a refresh of analytics data from platforms."""
    
    async def refresh_task():
        with get_sync_session() as sync_session:
            await analytics_service.fetch_all_metrics(sync_session)
            analytics_service.calculate_scores(sync_session)
    
    background_tasks.add_task(refresh_task)
    return {"message": "Analytics refresh started"}


@router.get("/video/{video_id}")
async def get_video_analytics(
    video_id: int,
    session: Session = Depends(get_async_session)
):
    """Get detailed analytics for a specific video."""
    # Get video
    video = await session.get(Video, video_id)
    if not video:
        return {"error": "Video not found"}
    
    # Get metrics
    metrics_result = await session.execute(
        select(VideoMetrics)
        .where(VideoMetrics.video_id == video_id)
        .order_by(VideoMetrics.metrics_date)
    )
    metrics = metrics_result.scalars().all()
    
    # Get score
    score_result = await session.execute(
        select(VideoScore).where(VideoScore.video_id == video_id)
    )
    score = score_result.scalar_one_or_none()
    
    # Group metrics by platform
    by_platform = {}
    for m in metrics:
        if m.platform not in by_platform:
            by_platform[m.platform] = []
        by_platform[m.platform].append({
            "date": m.metrics_date.isoformat(),
            "views": m.views,
            "likes": m.likes,
            "comments": m.comments,
            "shares": m.shares
        })
    
    return {
        "video_id": video_id,
        "title": video.title,
        "created_at": video.created_at.isoformat(),
        "score": {
            "views_velocity": score.views_velocity if score else 0,
            "engagement_score": score.engagement_score if score else 0,
            "virality_score": score.virality_score if score else 0,
            "is_winner": score.is_winner if score else False,
            "is_underperformer": score.is_underperformer if score else False
        } if score else None,
        "metrics_by_platform": by_platform
    }
