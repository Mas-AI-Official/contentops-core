"""
API routes for settings management.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Public settings (no secrets)."""
    # Paths
    base_path: str
    data_path: str
    
    # LLM
    ollama_base_url: str
    ollama_model: str
    ollama_fast_model: str
    
    # TTS
    xtts_enabled: bool
    elevenlabs_configured: bool
    
    # Whisper
    whisper_model: str
    whisper_device: str
    
    # Video defaults
    default_video_width: int
    default_video_height: int
    default_video_fps: int
    default_bg_music_volume: float
    
    # Worker
    worker_enabled: bool
    worker_interval_seconds: int
    max_concurrent_jobs: int
    
    # Platform status (configured or not)
    youtube_configured: bool
    instagram_configured: bool
    tiktok_configured: bool
    tiktok_verified: bool


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (excludes secrets)."""
    return SettingsResponse(
        base_path=str(settings.base_path),
        data_path=str(settings.data_path),
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_fast_model=settings.ollama_fast_model,
        xtts_enabled=settings.xtts_enabled,
        elevenlabs_configured=bool(settings.elevenlabs_api_key),
        whisper_model=settings.whisper_model,
        whisper_device=settings.whisper_device,
        default_video_width=settings.default_video_width,
        default_video_height=settings.default_video_height,
        default_video_fps=settings.default_video_fps,
        default_bg_music_volume=settings.default_bg_music_volume,
        worker_enabled=settings.worker_enabled,
        worker_interval_seconds=settings.worker_interval_seconds,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        youtube_configured=bool(settings.youtube_client_id and settings.youtube_refresh_token),
        instagram_configured=bool(settings.instagram_access_token and settings.instagram_business_account_id),
        tiktok_configured=bool(settings.tiktok_access_token and settings.tiktok_open_id),
        tiktok_verified=settings.tiktok_verified
    )


@router.get("/paths")
async def get_paths():
    """Get all configured paths."""
    return {
        "base_path": str(settings.base_path),
        "data_path": str(settings.data_path),
        "assets_path": str(settings.assets_path),
        "niches_path": str(settings.niches_path),
        "outputs_path": str(settings.outputs_path),
        "logs_path": str(settings.logs_path),
        "uploads_path": str(settings.uploads_path),
    }


@router.get("/paths/check")
async def check_paths():
    """Check if all required paths exist."""
    paths = {
        "data_path": settings.data_path,
        "assets_path": settings.assets_path,
        "niches_path": settings.niches_path,
        "outputs_path": settings.outputs_path,
        "logs_path": settings.logs_path,
        "uploads_path": settings.uploads_path,
        "music_path": settings.assets_path / "music",
        "logos_path": settings.assets_path / "logos",
        "fonts_path": settings.assets_path / "fonts",
        "stock_path": settings.assets_path / "stock",
    }
    
    return {
        name: {
            "path": str(path),
            "exists": path.exists(),
            "is_dir": path.is_dir() if path.exists() else False
        }
        for name, path in paths.items()
    }


@router.get("/services/status")
async def check_services():
    """Check status of required services."""
    import httpx
    
    results = {}
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            results["ollama"] = {
                "status": "running",
                "models": [m["name"] for m in response.json().get("models", [])]
            }
    except Exception as e:
        results["ollama"] = {"status": "not_running", "error": str(e)}
    
    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run([settings.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            results["ffmpeg"] = {"status": "installed", "version": version}
        else:
            results["ffmpeg"] = {"status": "error", "error": result.stderr}
    except Exception as e:
        results["ffmpeg"] = {"status": "not_found", "error": str(e)}
    
    # Check XTTS (if enabled)
    if settings.xtts_enabled:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8020/")
                results["xtts_server"] = {"status": "running"}
        except:
            # Check if TTS CLI is available
            try:
                result = subprocess.run(["tts", "--help"], capture_output=True, text=True, timeout=5)
                results["xtts_server"] = {"status": "cli_available", "note": "XTTS server not running, using CLI fallback"}
            except:
                results["xtts_server"] = {"status": "not_available"}
    
    return results


@router.get("/env-template")
async def get_env_template():
    """Get a template for the .env file."""
    return {
        "template": """# Content Factory Environment Configuration

# ============================================
# LLM Settings (Ollama)
# ============================================
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_FAST_MODEL=llama3.2:3b

# ============================================
# TTS Settings
# ============================================
XTTS_ENABLED=true
# XTTS_SPEAKER_WAV=path/to/speaker.wav

# ElevenLabs (optional fallback)
# ELEVENLABS_API_KEY=your_api_key_here
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# ============================================
# Whisper Settings
# ============================================
WHISPER_MODEL=base
WHISPER_DEVICE=cuda

# ============================================
# YouTube API
# Follow: https://developers.google.com/youtube/v3/getting-started
# ============================================
# YOUTUBE_CLIENT_ID=your_client_id
# YOUTUBE_CLIENT_SECRET=your_client_secret
# YOUTUBE_REFRESH_TOKEN=your_refresh_token

# ============================================
# Instagram Graph API
# Follow: https://developers.facebook.com/docs/instagram-api/getting-started
# ============================================
# INSTAGRAM_ACCESS_TOKEN=your_access_token
# INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id

# ============================================
# TikTok Content Posting API
# Follow: https://developers.tiktok.com/doc/content-posting-api-get-started
# NOTE: Unverified apps can only post as PRIVATE until audit approval
# ============================================
# TIKTOK_CLIENT_KEY=your_client_key
# TIKTOK_CLIENT_SECRET=your_client_secret
# TIKTOK_ACCESS_TOKEN=your_access_token
# TIKTOK_OPEN_ID=your_open_id
# TIKTOK_VERIFIED=false

# ============================================
# Worker Settings
# ============================================
WORKER_ENABLED=true
WORKER_INTERVAL_SECONDS=60
MAX_CONCURRENT_JOBS=2
"""
    }
