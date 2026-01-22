"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""
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
    
    # Paths
    base_path: Path = Path("D:/Ideas/content_factory")
    data_path: Path = Path("D:/Ideas/content_factory/data")
    
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
    
    # Database
    database_url: str = "sqlite:///D:/Ideas/content_factory/data/content_factory.db"
    
    # LLM - Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_fast_model: str = "llama3.2:3b"
    
    # TTS
    xtts_enabled: bool = True
    xtts_model_path: Optional[str] = None
    xtts_speaker_wav: Optional[str] = None
    
    # ElevenLabs fallback
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    
    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    
    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cuda"  # or "cpu"
    
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


settings = Settings()
