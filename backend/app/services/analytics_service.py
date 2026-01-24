"""
Analytics service - fetches and processes video performance metrics.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import json
from loguru import logger
import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.models import VideoMetrics, DailyNicheStats, VideoScore, Video, VideoPublish, Job, Niche
from app.services.growth_engine_service import growth_engine


class YouTubeAnalytics:
    """Fetch analytics from YouTube Data API."""
    
    def __init__(self):
        self.client_id = settings.youtube_client_id
        self.client_secret = settings.youtube_client_secret
        self.refresh_token = settings.youtube_refresh_token
        self._access_token = None
    
    def is_configured(self) -> bool:
        return all([self.client_id, self.client_secret, self.refresh_token])
    
    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token
    
    async def get_video_stats(self, video_id: str) -> Optional[Dict]:
        """Get statistics for a specific video."""
        
        if not self.is_configured():
            return None
        
        try:
            access_token = await self._get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "id": video_id,
                        "part": "statistics",
                        "access_token": access_token
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("items"):
                    return None
                
                stats = data["items"][0].get("statistics", {})
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "favorites": int(stats.get("favoriteCount", 0))
                }
                
        except Exception as e:
            logger.error(f"Failed to fetch YouTube stats: {e}")
            return None


class InstagramAnalytics:
    """Fetch analytics from Instagram Graph API."""
    
    def __init__(self):
        self.access_token = settings.instagram_access_token
        self.account_id = settings.instagram_business_account_id
    
    def is_configured(self) -> bool:
        return all([self.access_token, self.account_id])
    
    async def get_media_insights(self, media_id: str) -> Optional[Dict]:
        """Get insights for a specific media."""
        
        if not self.is_configured():
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v18.0/{media_id}/insights",
                    params={
                        "access_token": self.access_token,
                        "metric": "plays,likes,comments,shares,saved,reach,impressions"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                metrics = {}
                for item in data.get("data", []):
                    metrics[item["name"]] = item["values"][0]["value"]
                
                return {
                    "views": metrics.get("plays", 0),
                    "likes": metrics.get("likes", 0),
                    "comments": metrics.get("comments", 0),
                    "shares": metrics.get("shares", 0),
                    "saves": metrics.get("saved", 0),
                    "reach": metrics.get("reach", 0),
                    "impressions": metrics.get("impressions", 0)
                }
                
        except Exception as e:
            logger.error(f"Failed to fetch Instagram insights: {e}")
            return None


class TikTokAnalytics:
    """Fetch analytics from TikTok API.
    
    Note: Full analytics requires verified app status.
    """
    
    def __init__(self):
        self.access_token = settings.tiktok_access_token
        self.open_id = settings.tiktok_open_id
        self.is_verified = settings.tiktok_verified
    
    def is_configured(self) -> bool:
        return all([self.access_token, self.open_id])
    
    async def get_video_stats(self, video_id: str) -> Optional[Dict]:
        """Get statistics for a specific video.
        
        Note: Limited functionality for unverified apps.
        """
        
        if not self.is_configured():
            return None
        
        if not self.is_verified:
            logger.warning("TikTok analytics limited for unverified apps")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.tiktokapis.com/v2/video/query/",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "filters": {
                            "video_ids": [video_id]
                        },
                        "fields": ["view_count", "like_count", "comment_count", "share_count"]
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                videos = data.get("data", {}).get("videos", [])
                if not videos:
                    return None
                
                video = videos[0]
                return {
                    "views": video.get("view_count", 0),
                    "likes": video.get("like_count", 0),
                    "comments": video.get("comment_count", 0),
                    "shares": video.get("share_count", 0)
                }
                
        except Exception as e:
            logger.error(f"Failed to fetch TikTok stats: {e}")
            return None


class AnalyticsService:
    """Main analytics service."""
    
    def __init__(self):
        self.youtube = YouTubeAnalytics()
        self.instagram = InstagramAnalytics()
        self.tiktok = TikTokAnalytics()
    
    async def fetch_all_metrics(self, session: Session) -> int:
        """Fetch metrics for all published videos. Returns count updated."""
        
        updated = 0
        today = date.today()
        
        # Get all video publishes
        publishes = session.exec(
            select(VideoPublish).where(VideoPublish.status == "published")
        ).all()
        
        for publish in publishes:
            stats = None
            
            if publish.platform == "youtube" and publish.platform_video_id:
                stats = await self.youtube.get_video_stats(publish.platform_video_id)
            elif publish.platform == "instagram" and publish.platform_video_id:
                stats = await self.instagram.get_media_insights(publish.platform_video_id)
            elif publish.platform == "tiktok" and publish.platform_video_id:
                stats = await self.tiktok.get_video_stats(publish.platform_video_id)
            
            if stats:
                # Check if we already have metrics for today
                existing = session.exec(
                    select(VideoMetrics).where(
                        VideoMetrics.video_id == publish.video_id,
                        VideoMetrics.platform == publish.platform,
                        VideoMetrics.metrics_date == today
                    )
                ).first()
                
                if existing:
                    # Update existing
                    existing.views = stats.get("views", 0)
                    existing.likes = stats.get("likes", 0)
                    existing.comments = stats.get("comments", 0)
                    existing.shares = stats.get("shares", 0)
                    existing.impressions = stats.get("impressions")
                    existing.reach = stats.get("reach")
                    existing.saves = stats.get("saves")
                    existing.fetched_at = datetime.utcnow()
                else:
                    # Create new
                    metrics = VideoMetrics(
                        video_id=publish.video_id,
                        platform=publish.platform,
                        metrics_date=today,
                        views=stats.get("views", 0),
                        likes=stats.get("likes", 0),
                        comments=stats.get("comments", 0),
                        shares=stats.get("shares", 0),
                        impressions=stats.get("impressions"),
                        reach=stats.get("reach"),
                        saves=stats.get("saves")
                    )
                    session.add(metrics)
                
                updated += 1
        
        session.commit()
        logger.info(f"Updated metrics for {updated} video publishes")
        return updated
    
    def calculate_scores(self, session: Session) -> int:
        """Calculate performance scores for videos. Returns count updated."""
        
        updated = 0
        
        # Get all videos with metrics
        videos = session.exec(select(Video)).all()
        
        for video in videos:
            # Get latest metrics across all platforms
            metrics = session.exec(
                select(VideoMetrics)
                .where(VideoMetrics.video_id == video.id)
                .order_by(VideoMetrics.metrics_date.desc())
            ).all()
            
            if not metrics:
                continue
            
            # Aggregate metrics
            total_views = sum(m.views for m in metrics)
            total_likes = sum(m.likes for m in metrics)
            total_comments = sum(m.comments for m in metrics)
            total_shares = sum(m.shares for m in metrics)
            
            # Calculate scores
            # Views velocity: views per hour since creation
            hours_since_creation = max(1, (datetime.utcnow() - video.created_at).total_seconds() / 3600)
            views_velocity = total_views / hours_since_creation
            
            # Engagement score: weighted sum of interactions
            engagement_score = (
                total_likes * 1.0 +
                total_comments * 2.0 +
                total_shares * 3.0
            )
            
            # Virality score: combination of velocity and engagement
            virality_score = (views_velocity * 0.5) + (engagement_score * 0.5)
            
            # Get or create score record
            score = session.exec(
                select(VideoScore).where(VideoScore.video_id == video.id)
            ).first()
            
            if score:
                score.views_velocity = views_velocity
                score.engagement_score = engagement_score
                score.virality_score = virality_score
                score.calculated_at = datetime.utcnow()
            else:
                score = VideoScore(
                    video_id=video.id,
                    views_velocity=views_velocity,
                    engagement_score=engagement_score,
                    virality_score=virality_score
                )
                session.add(score)
            
            updated += 1
            
            # FEEDBACK LOOP: Update growth engine with template performance
            try:
                job = session.get(Job, video.job_id)
                if job and job.description:
                    desc_data = json.loads(job.description)
                    template = desc_data.get('template')
                    if template and 'name' in template:
                        niche = session.get(Niche, video.niche_id)
                        if niche:
                            growth_engine.update_template_performance(
                                niche.slug,
                                template['name'],
                                int(total_views),
                                int(total_likes),
                                int(total_comments)
                            )
            except Exception as e:
                logger.warning(f"Failed to update growth engine for video {video.id}: {e}")
        
        # Determine winners (top 10%)
        all_scores = session.exec(
            select(VideoScore).order_by(VideoScore.virality_score.desc())
        ).all()
        
        if all_scores:
            top_10_threshold = len(all_scores) // 10 or 1
            bottom_10_threshold = len(all_scores) - (len(all_scores) // 10)
            
            for i, score in enumerate(all_scores):
                score.is_winner = i < top_10_threshold
                score.is_underperformer = i >= bottom_10_threshold
        
        session.commit()
        logger.info(f"Calculated scores for {updated} videos")
        return updated
    
    def get_summary(self, session: Session, niche_id: Optional[int] = None) -> Dict:
        """Get analytics summary."""
        
        query = select(Video)
        if niche_id:
            query = query.where(Video.niche_id == niche_id)
        
        videos = session.exec(query).all()
        
        if not videos:
            return {
                "total_videos": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "avg_views_per_video": 0,
                "avg_engagement_rate": 0,
                "top_performing_niche": None,
                "winner_count": 0
            }
        
        video_ids = [v.id for v in videos]
        
        # Aggregate metrics
        metrics = session.exec(
            select(VideoMetrics).where(VideoMetrics.video_id.in_(video_ids))
        ).all()
        
        total_views = sum(m.views for m in metrics)
        total_likes = sum(m.likes for m in metrics)
        total_comments = sum(m.comments for m in metrics)
        
        # Count winners
        winners = session.exec(
            select(VideoScore)
            .where(VideoScore.video_id.in_(video_ids))
            .where(VideoScore.is_winner == True)
        ).all()
        
        return {
            "total_videos": len(videos),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_views_per_video": total_views / len(videos) if videos else 0,
            "avg_engagement_rate": (total_likes + total_comments) / max(total_views, 1),
            "top_performing_niche": None,  # TODO: Calculate
            "winner_count": len(winners)
        }
    
    def get_trends(
        self,
        session: Session,
        days: int = 30,
        niche_id: Optional[int] = None
    ) -> List[Dict]:
        """Get metrics trends over time."""
        
        start_date = date.today() - timedelta(days=days)
        
        query = select(VideoMetrics).where(VideoMetrics.metrics_date >= start_date)
        
        if niche_id:
            # Join with videos to filter by niche
            video_ids = [v.id for v in session.exec(
                select(Video).where(Video.niche_id == niche_id)
            ).all()]
            query = query.where(VideoMetrics.video_id.in_(video_ids))
        
        metrics = session.exec(query.order_by(VideoMetrics.metrics_date)).all()
        
        # Group by date
        daily_data = {}
        for m in metrics:
            date_str = m.metrics_date.isoformat()
            if date_str not in daily_data:
                daily_data[date_str] = {"date": date_str, "views": 0, "likes": 0, "comments": 0}
            daily_data[date_str]["views"] += m.views
            daily_data[date_str]["likes"] += m.likes
            daily_data[date_str]["comments"] += m.comments
        
        return list(daily_data.values())


analytics_service = AnalyticsService()
