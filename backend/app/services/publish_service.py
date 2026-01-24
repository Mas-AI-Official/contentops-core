"""
Publish service - handles publishing to YouTube, Instagram, and TikTok.
Uses official APIs where possible.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import httpx

from app.core.config import settings
from app.db import get_sync_session
from app.models import Account
from sqlmodel import select


class PublishStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"
    PRIVATE = "private"  # TikTok unverified
    MANUAL_REQUIRED = "manual_required"


@dataclass
class PublishResult:
    """Result of a publish operation."""
    platform: str
    status: PublishStatus
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    message: str = ""
    raw_response: Optional[Dict] = None


class YouTubePublisher:
    """YouTube publishing via Data API v3."""
    
    def __init__(self):
        self.client_id = settings.youtube_client_id
        self.client_secret = settings.youtube_client_secret
        self.refresh_token = settings.youtube_refresh_token
        self._access_token = None
    
    def is_configured(self, credentials: Optional[Dict] = None) -> bool:
        """Check if YouTube API is configured."""
        if credentials:
            return all([credentials.get("client_id"), credentials.get("client_secret"), credentials.get("refresh_token")])
        return all([self.client_id, self.client_secret, self.refresh_token])
    
    async def _get_access_token(self, credentials: Optional[Dict] = None) -> str:
        """Get or refresh access token."""
        # Use provided credentials or defaults
        client_id = credentials.get("client_id") if credentials else self.client_id
        client_secret = credentials.get("client_secret") if credentials else self.client_secret
        refresh_token = credentials.get("refresh_token") if credentials else self.refresh_token
        
        # If using defaults and we have a cached token, use it
        if not credentials and self._access_token:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            data = response.json()
            token = data["access_token"]
            
            # Cache only if using defaults
            if not credentials:
                self._access_token = token
                
            return token
    
    async def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        privacy: str = "private",  # private, unlisted, public
        credentials: Optional[Dict] = None
    ) -> PublishResult:
        """Upload video to YouTube."""
        
        if not self.is_configured(credentials):
            return PublishResult(
                platform="youtube",
                status=PublishStatus.MANUAL_REQUIRED,
                message="YouTube API not configured. Export video for manual upload."
            )
        
        try:
            access_token = await self._get_access_token(credentials)
            
            # Prepare metadata
            metadata = {
                "snippet": {
                    "title": title[:100],  # YouTube limit
                    "description": description[:5000],
                    "tags": tags[:500],
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Upload using resumable upload
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Step 1: Initialize upload
                init_response = await client.post(
                    "https://www.googleapis.com/upload/youtube/v3/videos",
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Upload-Content-Type": "video/*"
                    },
                    json=metadata
                )
                init_response.raise_for_status()
                upload_url = init_response.headers.get("Location")
                
                # Step 2: Upload video content
                with open(video_path, "rb") as f:
                    video_data = f.read()
                
                upload_response = await client.put(
                    upload_url,
                    headers={"Content-Type": "video/*"},
                    content=video_data
                )
                upload_response.raise_for_status()
                result = upload_response.json()
                
                video_id = result.get("id")
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                logger.info(f"YouTube upload successful: {video_url}")
                
                return PublishResult(
                    platform="youtube",
                    status=PublishStatus.SUCCESS,
                    video_id=video_id,
                    video_url=video_url,
                    message="Video uploaded successfully",
                    raw_response=result
                )
                
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return PublishResult(
                platform="youtube",
                status=PublishStatus.FAILED,
                message=str(e)
            )


class InstagramPublisher:
    """Instagram publishing via Graph API."""
    
    def __init__(self):
        self.access_token = settings.instagram_access_token
        self.account_id = settings.instagram_business_account_id
    
    def is_configured(self, credentials: Optional[Dict] = None) -> bool:
        """Check if Instagram API is configured."""
        if credentials:
            return all([credentials.get("access_token"), credentials.get("account_id")])
        return all([self.access_token, self.account_id])
    
    async def upload(
        self,
        video_path: Path,
        caption: str,
        hashtags: list,
        credentials: Optional[Dict] = None
    ) -> PublishResult:
        """Upload video to Instagram Reels."""
        
        if not self.is_configured(credentials):
            return PublishResult(
                platform="instagram",
                status=PublishStatus.MANUAL_REQUIRED,
                message="Instagram API not configured. Export video for manual upload."
            )
        
        try:
            access_token = credentials.get("access_token") if credentials else self.access_token
            account_id = credentials.get("account_id") if credentials else self.account_id
            
            full_caption = f"{caption}\n\n{' '.join(hashtags)}"[:2200]
            
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Step 1: Create container
                # Note: Instagram requires video to be hosted at a public URL
                # This is a simplified version - real implementation would need
                # to upload to a temporary hosting service first
                
                container_response = await client.post(
                    f"https://graph.facebook.com/v18.0/{account_id}/media",
                    params={
                        "access_token": access_token,
                        "media_type": "REELS",
                        "video_url": str(video_path),  # Would need to be a public URL
                        "caption": full_caption
                    }
                )
                container_response.raise_for_status()
                container_data = container_response.json()
                container_id = container_data.get("id")
                
                # Step 2: Publish container
                publish_response = await client.post(
                    f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
                    params={
                        "access_token": access_token,
                        "creation_id": container_id
                    }
                )
                publish_response.raise_for_status()
                result = publish_response.json()
                
                media_id = result.get("id")
                
                logger.info(f"Instagram upload successful: {media_id}")
                
                return PublishResult(
                    platform="instagram",
                    status=PublishStatus.SUCCESS,
                    video_id=media_id,
                    video_url=f"https://www.instagram.com/reel/{media_id}",
                    message="Video published to Instagram",
                    raw_response=result
                )
                
        except Exception as e:
            logger.error(f"Instagram upload failed: {e}")
            return PublishResult(
                platform="instagram",
                status=PublishStatus.FAILED,
                message=str(e)
            )


class TikTokPublisher:
    """TikTok publishing via Content Posting API.
    
    IMPORTANT: Unverified apps can only post videos as PRIVATE until audit approval.
    See: https://developers.tiktok.com/doc/content-posting-api-get-started
    """
    
    def __init__(self):
        self.client_key = settings.tiktok_client_key
        self.client_secret = settings.tiktok_client_secret
        self.access_token = settings.tiktok_access_token
        self.open_id = settings.tiktok_open_id
        self.is_verified = settings.tiktok_verified
    
    def is_configured(self, credentials: Optional[Dict] = None) -> bool:
        """Check if TikTok API is configured."""
        if credentials:
            return all([credentials.get("client_key"), credentials.get("access_token"), credentials.get("open_id")])
        return all([self.client_key, self.access_token, self.open_id])
    
    async def upload(
        self,
        video_path: Path,
        title: str,
        hashtags: list,
        credentials: Optional[Dict] = None
    ) -> PublishResult:
        """Upload video to TikTok.
        
        Note: Unverified apps can only post as private.
        """
        
        if not self.is_configured(credentials):
            return PublishResult(
                platform="tiktok",
                status=PublishStatus.MANUAL_REQUIRED,
                message="TikTok API not configured. Export video for manual upload."
            )
        
        try:
            access_token = credentials.get("access_token") if credentials else self.access_token
            is_verified = credentials.get("verified", False) if credentials else self.is_verified
            
            caption = f"{title} {' '.join(hashtags)}"[:150]  # TikTok limit
            
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Step 1: Initialize upload
                init_response = await client.post(
                    "https://open.tiktokapis.com/v2/post/publish/video/init/",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "post_info": {
                            "title": caption,
                            "privacy_level": "SELF_ONLY" if not is_verified else "PUBLIC_TO_EVERYONE",
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False
                        },
                        "source_info": {
                            "source": "FILE_UPLOAD",
                            "video_size": os.path.getsize(video_path),
                            "chunk_size": 10000000,  # 10MB chunks
                            "total_chunk_count": 1
                        }
                    }
                )
                init_response.raise_for_status()
                init_data = init_response.json()
                
                upload_url = init_data.get("data", {}).get("upload_url")
                publish_id = init_data.get("data", {}).get("publish_id")
                
                # Step 2: Upload video chunks
                with open(video_path, "rb") as f:
                    video_data = f.read()
                
                upload_response = await client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}"
                    },
                    content=video_data
                )
                upload_response.raise_for_status()
                
                # Determine status based on verification
                if not is_verified:
                    logger.warning("TikTok app is unverified - video will be posted as PRIVATE")
                    return PublishResult(
                        platform="tiktok",
                        status=PublishStatus.PRIVATE,
                        video_id=publish_id,
                        message="Video uploaded as PRIVATE (unverified app). Complete TikTok audit for public posting.",
                        raw_response=init_data
                    )
                
                return PublishResult(
                    platform="tiktok",
                    status=PublishStatus.SUCCESS,
                    video_id=publish_id,
                    message="Video published to TikTok",
                    raw_response=init_data
                )
                
        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            return PublishResult(
                platform="tiktok",
                status=PublishStatus.FAILED,
                message=str(e)
            )


class PublishService:
    """Main service for publishing to all platforms."""
    
    def __init__(self):
        self.youtube = YouTubePublisher()
        self.instagram = InstagramPublisher()
        self.tiktok = TikTokPublisher()
    
    def get_platform_status(self) -> Dict[str, Dict]:
        """Get configuration status for all platforms."""
        return {
            "youtube": {
                "configured": self.youtube.is_configured(),
                "message": "Ready" if self.youtube.is_configured() else "Missing API credentials"
            },
            "instagram": {
                "configured": self.instagram.is_configured(),
                "message": "Ready" if self.instagram.is_configured() else "Missing API credentials"
            },
            "tiktok": {
                "configured": self.tiktok.is_configured(),
                "verified": self.tiktok.is_verified,
                "message": self._get_tiktok_status_message()
            }
        }
    
    def _get_tiktok_status_message(self) -> str:
        if not self.tiktok.is_configured():
            return "Missing API credentials"
        if not self.tiktok.is_verified:
            return "Configured but UNVERIFIED - posts will be private until audit approval"
        return "Ready (verified)"
    
    async def publish(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
        hashtags: list,
        platforms: list,
        account_ids: Optional[Dict[str, int]] = None
    ) -> Dict[str, PublishResult]:
        """Publish video to specified platforms."""
        
        results = {}
        
        # Fetch accounts if IDs provided
        accounts = {}
        if account_ids:
            with get_sync_session() as session:
                for platform, acc_id in account_ids.items():
                    if acc_id:
                        account = session.get(Account, acc_id)
                        if account:
                            accounts[platform] = account
        
        if "youtube" in platforms:
            creds = accounts.get("youtube").credentials_json if accounts.get("youtube") else None
            results["youtube"] = await self.youtube.upload(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                privacy="private",  # Start private, let user make public
                credentials=creds
            )
        
        if "instagram" in platforms:
            creds = accounts.get("instagram").credentials_json if accounts.get("instagram") else None
            results["instagram"] = await self.instagram.upload(
                video_path=video_path,
                caption=description,
                hashtags=[f"#{tag}" for tag in hashtags],
                credentials=creds
            )
        
        if "tiktok" in platforms:
            creds = accounts.get("tiktok").credentials_json if accounts.get("tiktok") else None
            results["tiktok"] = await self.tiktok.upload(
                video_path=video_path,
                title=title,
                hashtags=[f"#{tag}" for tag in hashtags],
                credentials=creds
            )
        
        return results
    
    def export_for_manual_upload(
        self,
        video_path: Path,
        metadata: Dict,
        output_dir: Path
    ) -> Path:
        """Export video with metadata file for manual upload."""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy video
        import shutil
        video_name = Path(video_path).name
        export_video = output_dir / video_name
        shutil.copy2(video_path, export_video)
        
        # Write metadata
        metadata_file = output_dir / f"{Path(video_path).stem}_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Write upload instructions
        instructions = output_dir / "UPLOAD_INSTRUCTIONS.txt"
        with open(instructions, "w") as f:
            f.write("MANUAL UPLOAD INSTRUCTIONS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Video: {video_name}\n\n")
            f.write(f"Title: {metadata.get('title', 'N/A')}\n\n")
            f.write(f"Description:\n{metadata.get('description', 'N/A')}\n\n")
            f.write(f"Hashtags: {' '.join(metadata.get('hashtags', []))}\n\n")
            f.write(f"Tags: {', '.join(metadata.get('tags', []))}\n\n")
            f.write("\nPlatform-specific notes:\n")
            f.write("- YouTube: Upload via YouTube Studio\n")
            f.write("- Instagram: Upload via Instagram app or Creator Studio\n")
            f.write("- TikTok: Upload via TikTok app or TikTok Studio\n")
        
        logger.info(f"Exported for manual upload: {output_dir}")
        return export_video


publish_service = PublishService()
