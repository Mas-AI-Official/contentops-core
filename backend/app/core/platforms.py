"""
Platform-specific configurations for video export.
"""
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class PlatformType(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    ALL = "all"  # Universal format


@dataclass
class PlatformVideoConfig:
    """Video configuration for a specific platform."""
    name: str
    width: int
    height: int
    aspect_ratio: str
    max_duration_seconds: int
    min_duration_seconds: int
    recommended_duration_seconds: int
    max_file_size_mb: int
    fps: int
    video_codec: str
    audio_codec: str
    audio_bitrate: str
    video_bitrate: str
    container: str
    
    # Platform-specific metadata
    max_title_length: int
    max_description_length: int
    max_hashtags: int
    supports_scheduled_posting: bool


# Platform configurations based on official specs
PLATFORM_CONFIGS: Dict[PlatformType, PlatformVideoConfig] = {
    PlatformType.YOUTUBE_SHORTS: PlatformVideoConfig(
        name="YouTube Shorts",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        max_duration_seconds=60,
        min_duration_seconds=15,
        recommended_duration_seconds=30,
        max_file_size_mb=256,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        video_bitrate="8M",
        container="mp4",
        max_title_length=100,
        max_description_length=5000,
        max_hashtags=500,
        supports_scheduled_posting=True,
    ),
    PlatformType.INSTAGRAM_REELS: PlatformVideoConfig(
        name="Instagram Reels",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        max_duration_seconds=90,
        min_duration_seconds=3,
        recommended_duration_seconds=30,
        max_file_size_mb=250,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        audio_bitrate="128k",
        video_bitrate="5M",
        container="mp4",
        max_title_length=0,  # No title, only caption
        max_description_length=2200,
        max_hashtags=30,
        supports_scheduled_posting=True,
    ),
    PlatformType.TIKTOK: PlatformVideoConfig(
        name="TikTok",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        max_duration_seconds=600,  # 10 minutes
        min_duration_seconds=3,
        recommended_duration_seconds=30,
        max_file_size_mb=287,
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        audio_bitrate="128k",
        video_bitrate="6M",
        container="mp4",
        max_title_length=150,
        max_description_length=150,  # Combined with title
        max_hashtags=100,
        supports_scheduled_posting=False,
    ),
    PlatformType.ALL: PlatformVideoConfig(
        name="Universal (All Platforms)",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        max_duration_seconds=60,  # Most restrictive
        min_duration_seconds=15,
        recommended_duration_seconds=30,
        max_file_size_mb=250,  # Most restrictive
        fps=30,
        video_codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        video_bitrate="6M",
        container="mp4",
        max_title_length=100,
        max_description_length=150,  # Most restrictive
        max_hashtags=30,  # Most restrictive
        supports_scheduled_posting=True,
    ),
}


def get_platform_config(platform: PlatformType) -> PlatformVideoConfig:
    """Get configuration for a platform."""
    return PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS[PlatformType.ALL])


def get_ffmpeg_args_for_platform(platform: PlatformType) -> list:
    """Get FFmpeg arguments optimized for a platform."""
    config = get_platform_config(platform)
    
    args = [
        "-c:v", config.video_codec,
        "-preset", "medium",
        "-crf", "23",
        "-b:v", config.video_bitrate,
        "-maxrate", config.video_bitrate,
        "-bufsize", str(int(config.video_bitrate.replace("M", "")) * 2) + "M",
        "-c:a", config.audio_codec,
        "-b:a", config.audio_bitrate,
        "-ar", "44100",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
    ]
    
    return args


def validate_video_for_platform(
    duration_seconds: float,
    file_size_mb: float,
    platform: PlatformType
) -> dict:
    """Validate if a video meets platform requirements."""
    config = get_platform_config(platform)
    
    issues = []
    warnings = []
    
    if duration_seconds > config.max_duration_seconds:
        issues.append(f"Video too long: {duration_seconds:.1f}s (max: {config.max_duration_seconds}s)")
    elif duration_seconds < config.min_duration_seconds:
        issues.append(f"Video too short: {duration_seconds:.1f}s (min: {config.min_duration_seconds}s)")
    
    if file_size_mb > config.max_file_size_mb:
        issues.append(f"File too large: {file_size_mb:.1f}MB (max: {config.max_file_size_mb}MB)")
    
    if duration_seconds < config.recommended_duration_seconds:
        warnings.append(f"Video shorter than recommended ({config.recommended_duration_seconds}s)")
    elif duration_seconds > config.recommended_duration_seconds * 2:
        warnings.append(f"Video longer than optimal for engagement")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "platform": config.name
    }
