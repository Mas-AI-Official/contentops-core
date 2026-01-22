"""
API routes for settings management.
Includes model paths, cache directories, and service status checks.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
import sys
import json
from pathlib import Path

from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Public settings (no secrets)."""
    # Paths
    base_path: str
    data_path: str
    models_path: str
    
    # LLM
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    ollama_fast_model: str
    mcp_enabled: bool
    mcp_connector_count: int
    mcp_llm_connector: Optional[str]
    mcp_llm_model: Optional[str]
    mcp_llm_path: Optional[str]
    
    # TTS
    tts_provider: str
    xtts_enabled: bool
    xtts_server_url: str
    elevenlabs_configured: bool
    
    # Whisper
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    
    # Video defaults
    default_video_width: int
    default_video_height: int
    default_video_fps: int
    default_bg_music_volume: float
    video_gen_provider: str
    ltx_api_url: Optional[str]
    
    # Worker
    worker_enabled: bool
    worker_interval_seconds: int
    max_concurrent_jobs: int
    
    # Platform status (configured or not)
    youtube_configured: bool
    instagram_configured: bool
    tiktok_configured: bool
    tiktok_verified: bool
    
    # Python version
    python_version: str
    required_python_version: str


class ModelPathsResponse(BaseModel):
    """Model cache paths configuration."""
    models_path: str
    ollama_models_path: str
    whisper_cache_path: str
    xtts_cache_path: str
    torch_cache_path: str
    image_models_path: str
    hf_home: Optional[str]
    torch_home: Optional[str]


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (excludes secrets)."""
    connectors_count = 0
    if settings.mcp_connectors_json:
        try:
            parsed = json.loads(settings.mcp_connectors_json)
            connectors_count = len(parsed) if isinstance(parsed, list) else 0
        except Exception:
            connectors_count = 0

    return SettingsResponse(
        base_path=str(settings.base_path),
        data_path=str(settings.data_path),
        models_path=str(settings.models_path),
        llm_provider=settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_fast_model=settings.ollama_fast_model,
        mcp_enabled=settings.mcp_enabled,
        mcp_connector_count=connectors_count,
        mcp_llm_connector=settings.mcp_llm_connector,
        mcp_llm_model=settings.mcp_llm_model,
        mcp_llm_path=settings.mcp_llm_path,
        tts_provider=settings.tts_provider,
        xtts_enabled=settings.xtts_enabled,
        xtts_server_url=settings.xtts_server_url,
        elevenlabs_configured=bool(settings.elevenlabs_api_key),
        whisper_model=settings.whisper_model,
        whisper_device=settings.whisper_device,
        whisper_compute_type=settings.whisper_compute_type,
        default_video_width=settings.default_video_width,
        default_video_height=settings.default_video_height,
        default_video_fps=settings.default_video_fps,
        default_bg_music_volume=settings.default_bg_music_volume,
        video_gen_provider=settings.video_gen_provider,
        ltx_api_url=settings.ltx_api_url,
        worker_enabled=settings.worker_enabled,
        worker_interval_seconds=settings.worker_interval_seconds,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        youtube_configured=bool(settings.youtube_client_id and settings.youtube_refresh_token),
        instagram_configured=bool(settings.instagram_access_token and settings.instagram_business_account_id),
        tiktok_configured=bool(settings.tiktok_access_token and settings.tiktok_open_id),
        tiktok_verified=settings.tiktok_verified,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        required_python_version=settings.required_python_version
    )


@router.get("/paths")
async def get_paths():
    """Get all configured data paths."""
    return {
        "base_path": str(settings.base_path),
        "data_path": str(settings.data_path),
        "assets_path": str(settings.assets_path),
        "niches_path": str(settings.niches_path),
        "outputs_path": str(settings.outputs_path),
        "logs_path": str(settings.logs_path),
        "uploads_path": str(settings.uploads_path),
        "scripts_path": str(settings.scripts_path),
    }


@router.get("/model-paths", response_model=ModelPathsResponse)
async def get_model_paths():
    """Get model cache paths configuration."""
    return ModelPathsResponse(
        models_path=str(settings.models_path),
        ollama_models_path=str(settings.ollama_models_path),
        whisper_cache_path=str(settings.whisper_cache_path),
        xtts_cache_path=str(settings.xtts_cache_path),
        torch_cache_path=str(settings.torch_cache_path),
        image_models_path=str(settings.image_models_path),
        hf_home=os.environ.get("HF_HOME"),
        torch_home=os.environ.get("TORCH_HOME")
    )


@router.get("/paths/check")
async def check_paths():
    """Check if all required paths exist and are writable."""
    paths = {
        "data_path": settings.data_path,
        "assets_path": settings.assets_path,
        "niches_path": settings.niches_path,
        "outputs_path": settings.outputs_path,
        "logs_path": settings.logs_path,
        "uploads_path": settings.uploads_path,
        "scripts_path": settings.scripts_path,
        "music_path": settings.assets_path / "music",
        "logos_path": settings.assets_path / "logos",
        "fonts_path": settings.assets_path / "fonts",
        "stock_path": settings.assets_path / "stock",
    }
    
    def check_path(path: Path) -> dict:
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        writable = os.access(path, os.W_OK) if exists else False
        return {
            "path": str(path),
            "exists": exists,
            "is_dir": is_dir,
            "writable": writable
        }
    
    return {name: check_path(path) for name, path in paths.items()}


@router.get("/model-paths/check")
async def check_model_paths():
    """Check if model cache directories exist and are writable."""
    paths = {
        "models_path": settings.models_path,
        "ollama_models_path": settings.ollama_models_path,
        "whisper_cache_path": settings.whisper_cache_path,
        "xtts_cache_path": settings.xtts_cache_path,
        "torch_cache_path": settings.torch_cache_path,
        "image_models_path": settings.image_models_path,
    }
    
    def check_path(path: Path) -> dict:
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        writable = os.access(path, os.W_OK) if exists else False
        
        # Count files/size if exists
        file_count = 0
        total_size = 0
        if exists and is_dir:
            for f in path.rglob("*"):
                if f.is_file():
                    file_count += 1
                    total_size += f.stat().st_size
        
        return {
            "path": str(path),
            "exists": exists,
            "is_dir": is_dir,
            "writable": writable,
            "file_count": file_count,
            "size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    results = {name: check_path(path) for name, path in paths.items()}
    
    # Add OLLAMA_MODELS env var status
    ollama_models_env = os.environ.get("OLLAMA_MODELS")
    results["ollama_models_env"] = {
        "env_var": "OLLAMA_MODELS",
        "value": ollama_models_env,
        "is_set": ollama_models_env is not None,
        "matches_config": ollama_models_env == str(settings.ollama_models_path) if ollama_models_env else False
    }
    
    return results


@router.post("/model-paths/create")
async def create_model_paths():
    """Create all model cache directories if they don't exist."""
    paths = [
        settings.models_path,
        settings.ollama_models_path,
        settings.whisper_cache_path,
        settings.xtts_cache_path,
        settings.torch_cache_path,
        settings.image_models_path,
    ]
    
    results = {}
    for path in paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
            results[str(path)] = {"created": True, "exists": path.exists()}
        except Exception as e:
            results[str(path)] = {"created": False, "error": str(e)}
    
    return results


@router.get("/services/status")
async def check_services():
    """Check status of required services."""
    import httpx
    import subprocess
    
    results = {}
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    required = settings.required_python_version
    version_ok = py_version.startswith(required)
    results["python"] = {
        "status": "ok" if version_ok else "warning",
        "version": py_version,
        "required": required,
        "message": None if version_ok else f"Recommended Python version is {required}.x"
    }
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            models = [m["name"] for m in response.json().get("models", [])]
            results["ollama"] = {
                "status": "running",
                "models": models,
                "model_count": len(models)
            }
    except Exception as e:
        results["ollama"] = {"status": "not_running", "error": str(e)}
    
    # Check FFmpeg
    try:
        result = subprocess.run([settings.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            results["ffmpeg"] = {"status": "installed", "version": version}
        else:
            results["ffmpeg"] = {"status": "error", "error": result.stderr}
    except FileNotFoundError:
        results["ffmpeg"] = {"status": "not_found", "error": "FFmpeg not in PATH"}
    except Exception as e:
        results["ffmpeg"] = {"status": "error", "error": str(e)}
    
    # Check FFprobe
    try:
        result = subprocess.run([settings.ffprobe_path, "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            results["ffprobe"] = {"status": "installed", "version": version}
        else:
            results["ffprobe"] = {"status": "error", "error": result.stderr}
    except FileNotFoundError:
        results["ffprobe"] = {"status": "not_found", "error": "FFprobe not in PATH"}
    except Exception as e:
        results["ffprobe"] = {"status": "error", "error": str(e)}
    
    # Check XTTS
    if settings.xtts_enabled:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(settings.xtts_server_url)
                results["xtts_server"] = {"status": "running", "url": settings.xtts_server_url}
        except:
            # Check if TTS CLI is available
            try:
                result = subprocess.run(["tts", "--help"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    results["xtts_server"] = {
                        "status": "cli_available", 
                        "note": "XTTS server not running, CLI fallback available"
                    }
                else:
                    results["xtts_server"] = {"status": "not_available"}
            except:
                results["xtts_server"] = {"status": "not_available", "note": "Neither server nor CLI found"}
    else:
        results["xtts_server"] = {"status": "disabled"}
    
    # Check ElevenLabs
    if settings.elevenlabs_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": settings.elevenlabs_api_key}
                )
                if response.status_code == 200:
                    voice_count = len(response.json().get("voices", []))
                    results["elevenlabs"] = {"status": "configured", "voice_count": voice_count}
                else:
                    results["elevenlabs"] = {"status": "error", "error": f"API returned {response.status_code}"}
        except Exception as e:
            results["elevenlabs"] = {"status": "error", "error": str(e)}
    else:
        results["elevenlabs"] = {"status": "not_configured"}

    # MCP status
    connector_count = 0
    if settings.mcp_connectors_json:
        try:
            parsed = json.loads(settings.mcp_connectors_json)
            connector_count = len(parsed) if isinstance(parsed, list) else 0
        except Exception:
            connector_count = 0
    results["mcp"] = {
        "status": "configured" if settings.mcp_enabled and connector_count > 0 else ("disabled" if not settings.mcp_enabled else "not_configured"),
        "connector_count": connector_count,
        "provider": settings.llm_provider
    }

    # LTX video status (optional)
    if settings.video_gen_provider == "ltx" and settings.ltx_api_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(settings.ltx_api_url)
                results["ltx_video"] = {"status": "running" if response.status_code < 400 else "error", "url": settings.ltx_api_url}
        except Exception as e:
            results["ltx_video"] = {"status": "not_running", "error": str(e)}
    else:
        results["ltx_video"] = {"status": "not_configured"}
    
    return results


@router.get("/env-template")
async def get_env_template():
    """Get a template for the .env file."""
    return {
        "template": """# Content Factory Environment Configuration
# Python 3.11 recommended for best compatibility

# ============================================
# Paths (optional - defaults work for most setups)
# ============================================
# BASE_PATH=D:/Ideas/content_factory
# DATA_PATH=D:/Ideas/content_factory/data
# MODELS_PATH=D:/Ideas/content_factory/models

# Model cache paths (set these to keep downloads in project folder)
# HF_HOME=D:/Ideas/content_factory/models/whisper/hf
# TORCH_HOME=D:/Ideas/content_factory/models/torch
# XDG_CACHE_HOME=D:/Ideas/content_factory/models/cache

# ============================================
# LLM Settings (Ollama / MCP)
# ============================================
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_FAST_MODEL=llama3.2:3b

# ============================================
# TTS Settings
# ============================================
TTS_PROVIDER=xtts
XTTS_ENABLED=true
XTTS_SERVER_URL=http://localhost:8020
# XTTS_SPEAKER_WAV=path/to/speaker.wav
XTTS_LANGUAGE=en

# ElevenLabs (optional fallback)
# ELEVENLABS_API_KEY=your_api_key_here
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
# ELEVENLABS_MODEL=eleven_monolingual_v1

# ============================================
# Whisper Settings (subtitles)
# ============================================
WHISPER_MODEL=base
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

# ============================================
# FFmpeg Settings
# ============================================
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe

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

# ============================================
# MCP / External Connectors (optional)
# ============================================
# MCP_ENABLED=false
# MCP_DEFAULT_TIMEOUT=60
# MCP_CONNECTORS_JSON=[{"name":"openai","type":"llm","base_url":"https://api.openai.com/v1","auth_header":"Authorization","auth_env":"OPENAI_API_KEY","auth_prefix":"Bearer "}]
# MCP_LLM_CONNECTOR=openai
# MCP_LLM_PATH=v1/chat/completions
# MCP_LLM_MODEL=gpt-4o-mini

# ============================================
# Video Defaults
# ============================================
DEFAULT_VIDEO_WIDTH=1080
DEFAULT_VIDEO_HEIGHT=1920
DEFAULT_VIDEO_FPS=30
DEFAULT_BG_MUSIC_VOLUME=0.1

# Video Generator Provider (optional)
# VIDEO_GEN_PROVIDER=ffmpeg
# LTX_API_URL=http://127.0.0.1:8188
"""
    }


@router.get("/voices")
async def get_available_voices():
    """Get available voices for TTS."""
    from app.services.tts_service import tts_service
    
    voices = {
        "xtts": {
            "enabled": settings.xtts_enabled,
            "note": "XTTS uses voice cloning from speaker wav files",
            "voices": []  # Custom speaker wavs would be listed here
        },
        "elevenlabs": {
            "enabled": bool(settings.elevenlabs_api_key),
            "voices": []
        }
    }
    
    # Get ElevenLabs voices if configured
    if settings.elevenlabs_api_key:
        try:
            voices["elevenlabs"]["voices"] = await tts_service.list_elevenlabs_voices()
        except:
            voices["elevenlabs"]["error"] = "Failed to fetch voices"
    
    return voices
