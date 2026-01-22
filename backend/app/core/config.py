"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Content Factory"
    debug: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # Paths - Project root
    base_path: Path = Path("D:/Ideas/content_factory")
    data_path: Path = Path("D:/Ideas/content_factory/data")
    models_path: Path = Path("D:/Ideas/content_factory/models")
    
    @property
    def assets_path(self) -> Path:
        return self.data_path / "assets"
    
    @property
    def niches_path(self) -> Path:
        return self.data_path / "niches"
    
    @property
    def outputs_path(self) -> Path:
        return self.data_path / "outputs"
    
    @property
    def logs_path(self) -> Path:
        return self.data_path / "logs"
    
    @property
    def uploads_path(self) -> Path:
        return self.data_path / "uploads"
    
    @property
    def scripts_path(self) -> Path:
        return self.data_path / "scripts"
    
    # Model Cache Paths (for local model storage)
    @property
    def ollama_models_path(self) -> Path:
        return self.models_path / "ollama"
    
    @property
    def whisper_cache_path(self) -> Path:
        return self.models_path / "whisper"
    
    @property
    def xtts_cache_path(self) -> Path:
        return self.models_path / "xtts"
    
    @property
    def torch_cache_path(self) -> Path:
        return self.models_path / "torch"
    
    @property
    def image_models_path(self) -> Path:
        return self.models_path / "image"
    
    # Environment variables for model caching
    hf_home: Optional[str] = None  # HuggingFace cache
    torch_home: Optional[str] = None  # PyTorch hub cache
    xdg_cache_home: Optional[str] = None  # General cache
    
    def setup_model_cache_env(self):
        """Set environment variables for model caching to use local paths."""
        if self.hf_home:
            os.environ["HF_HOME"] = self.hf_home
        else:
            os.environ["HF_HOME"] = str(self.whisper_cache_path / "hf")
        
        if self.torch_home:
            os.environ["TORCH_HOME"] = self.torch_home
        else:
            os.environ["TORCH_HOME"] = str(self.torch_cache_path)
        
        if self.xdg_cache_home:
            os.environ["XDG_CACHE_HOME"] = self.xdg_cache_home
        else:
            os.environ["XDG_CACHE_HOME"] = str(self.models_path / "cache")
    
    # Database
    database_url: str = "sqlite:///D:/Ideas/content_factory/data/content_factory.db"
    
    # LLM - Provider (ollama | mcp)
    llm_provider: str = "ollama"

    # LLM - Ollama (Global defaults, can be overridden per-niche)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_fast_model: str = "llama3.2:3b"

    # MCP LLM settings (OpenAI-compatible via MCP forward)
    mcp_llm_connector: Optional[str] = None
    mcp_llm_path: str = "v1/chat/completions"
    mcp_llm_model: Optional[str] = None
    
    # TTS Provider (Global default)
    tts_provider: str = "xtts"  # "xtts" or "elevenlabs"
    
    # XTTS
    xtts_enabled: bool = True
    xtts_server_url: str = "http://localhost:8020"
    xtts_model_path: Optional[str] = None
    xtts_speaker_wav: Optional[str] = None
    xtts_language: str = "en"
    
    # ElevenLabs fallback
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    elevenlabs_model: str = "eleven_monolingual_v1"
    
    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    
    # Whisper / faster-whisper
    whisper_model: str = "base"  # tiny, base, small, medium, large
    whisper_device: str = "cuda"  # "cuda" or "cpu"
    whisper_compute_type: str = "float16"  # float16, int8, float32
    
    # YouTube API
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_refresh_token: Optional[str] = None
    
    # Instagram Graph API
    instagram_access_token: Optional[str] = None
    instagram_business_account_id: Optional[str] = None
    
    # TikTok API
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    tiktok_access_token: Optional[str] = None
    tiktok_open_id: Optional[str] = None
    tiktok_verified: bool = False  # Unverified apps can only post as private
    
    # Worker settings
    worker_enabled: bool = True
    worker_interval_seconds: int = 60
    max_concurrent_jobs: int = 2
    
    # Video defaults
    default_video_width: int = 1080
    default_video_height: int = 1920
    default_video_fps: int = 30
    default_bg_music_volume: float = 0.1

    # Video generation provider (ffmpeg | ltx)
    video_gen_provider: str = "ffmpeg"
    ltx_api_url: Optional[str] = None  # ComfyUI API URL (fallback)
    ltx_model_path: Optional[str] = None  # Path to LTX-2 model checkpoint
    ltx_use_fp8: bool = True  # Use FP8 quantization for 8GB VRAM
    
    # MCP / External connectors (optional)
    mcp_enabled: bool = False
    mcp_connectors_json: Optional[str] = None
    mcp_default_timeout: int = 60

    # Required Python version (for startup check)
    required_python_version: str = "3.11"

    def get_env_value(self, key: str) -> Optional[str]:
        """Fetch an environment value safely."""
        return os.environ.get(key)


settings = Settings()

# Setup model cache environment on import
settings.setup_model_cache_env()
