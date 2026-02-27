"""
MCP Publisher - Handles publishing via Model Context Protocol servers (X, YouTube).
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger
from app.services.mcp_service import mcp_service
from app.services.publish_service import PublishResult, PublishStatus

class MCPPublisher:
    """Publishing via external MCP connectors."""

    async def publish_to_x(self, video_path: Path, text: str, credentials: Optional[Dict] = None) -> PublishResult:
        """Post a video to X using the mcp-x MCP server."""
        logger.info(f"Posting to X via MCP: {text[:50]}...")
        
        # Prepare arguments
        args = {
            "text": text,
            "media_paths": [str(video_path.absolute())]
        }
        if credentials:
            args["auth"] = credentials

        try:
            result = await mcp_service.call_tool(
                server_name="mcp-x",
                tool_name="post_tweet",
                arguments=args
            )
            
            if "error" in result:
                return PublishResult(
                    platform="x",
                    status=PublishStatus.FAILED,
                    message=f"MCP Error: {result['message']}"
                )
                
            return PublishResult(
                platform="x",
                status=PublishStatus.SUCCESS,
                video_id=result.get("tweet_id"),
                video_url=result.get("url"),
                message="Posted to X successfully"
            )
        except Exception as e:
            logger.error(f"X MCP Publishing failed: {e}")
            return PublishResult(platform="x", status=PublishStatus.FAILED, message=str(e))

    async def publish_to_youtube(self, video_path: Path, title: str, description: str, credentials: Optional[Dict] = None) -> PublishResult:
        """Upload to YouTube Shorts via yutu MCP server."""
        logger.info(f"Uploading to YouTube via MCP: {title}...")
        
        args = {
            "path": str(video_path.absolute()),
            "title": title,
            "description": description,
            "privacy": "public"
        }
        if credentials:
            args["auth"] = credentials

        try:
            result = await mcp_service.call_tool(
                server_name="yutu",
                tool_name="upload_video",
                arguments=args
            )
            
            if "error" in result:
                return PublishResult(
                    platform="youtube",
                    status=PublishStatus.FAILED,
                    message=f"MCP Error: {result['message']}"
                )
                
            return PublishResult(
                platform="youtube",
                status=PublishStatus.SUCCESS,
                video_id=result.get("video_id"),
                video_url=f"https://youtube.com/shorts/{result.get('video_id')}",
                message="Uploaded to YouTube successfully"
            )
        except Exception as e:
            logger.error(f"YouTube MCP Publishing failed: {e}")
            return PublishResult(platform="youtube", status=PublishStatus.FAILED, message=str(e))

    async def publish_to_instagram(self, video_path: Path, caption: str, hashtags: list, credentials: Optional[Dict] = None) -> PublishResult:
        """Upload to Instagram via MCP server (placeholder)."""
        logger.info(f"Uploading to Instagram via MCP: {caption[:50]}...")
        # Placeholder for MCP call when instagram MCP server exists
        # result = await mcp_service.call_tool(server_name="instagram_mcp", tool_name="upload_reels", arguments={...})
        return PublishResult(platform="instagram", status=PublishStatus.FAILED, message="Instagram MCP not implemented yet")

    async def publish_to_tiktok(self, video_path: Path, title: str, hashtags: list, credentials: Optional[Dict] = None) -> PublishResult:
        """Upload to TikTok via MCP server (placeholder)."""
        logger.info(f"Uploading to TikTok via MCP: {title[:50]}...")
        # Placeholder for MCP call when tiktok MCP server exists
        # result = await mcp_service.call_tool(server_name="tiktok_mcp", tool_name="upload_video", arguments={...})
        return PublishResult(platform="tiktok", status=PublishStatus.FAILED, message="TikTok MCP not implemented yet")

mcp_publisher = MCPPublisher()
