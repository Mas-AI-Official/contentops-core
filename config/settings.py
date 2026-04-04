"""ContentOps configuration — single source of truth for all settings."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Project
    project_root: Path = Path("D:/Ideas/contentops-core")
    models_root: Path = Path("D:/Ideas/MODELS_ROOT")

    # LLM
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_quality_model: str = "gemma4:31b"

    # Voice
    elevenlabs_api_key: Optional[str] = None
    daena_voice_id: Optional[str] = None
    kokoro_model_path: str = "models/kokoro-v0_19.onnx"
    kokoro_voices_path: str = "models/voices.bin"

    # B-Roll
    pexels_api_key: Optional[str] = None

    # Claude API
    anthropic_api_key: Optional[str] = None

    # Social
    youtube_api_key: Optional[str] = None
    tiktok_access_token: Optional[str] = None
    instagram_access_token: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None

    # System
    log_level: str = "INFO"
    budget_mode: bool = True
    default_tenant: str = "mas-ai"

    # Derived paths
    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def tenants_dir(self) -> Path:
        return self.project_root / "tenants"

    @property
    def intelligence_dir(self) -> Path:
        return self.project_root / "src" / "intelligence"


settings = Settings()
