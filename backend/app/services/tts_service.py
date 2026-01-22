"""
TTS service - text-to-speech using XTTS (local) or ElevenLabs (fallback).
Supports per-niche voice configuration.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import httpx
from loguru import logger

from app.core.config import settings


class TTSService:
    """Service for text-to-speech generation."""
    
    def __init__(self):
        self.xtts_enabled = settings.xtts_enabled
        self.elevenlabs_key = settings.elevenlabs_api_key
        self.default_provider = settings.tts_provider
    
    async def generate_audio(
        self,
        text: str,
        output_path: Path,
        provider: Optional[str] = None,
        voice_id: Optional[str] = None,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> Path:
        """
        Generate audio from text.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            provider: TTS provider ('xtts' or 'elevenlabs'), defaults to global setting
            voice_id: Voice ID (for ElevenLabs) or speaker wav path (for XTTS)
            speaker_wav: Explicit speaker wav path for XTTS voice cloning
            language: Language code for XTTS
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine provider
        use_provider = provider or self.default_provider
        
        if use_provider == "elevenlabs" and self.elevenlabs_key:
            return await self._generate_elevenlabs(text, output_path, voice_id)
        elif use_provider == "xtts" or self.xtts_enabled:
            try:
                return await self._generate_xtts(
                    text, output_path, 
                    speaker_wav=speaker_wav or voice_id,
                    language=language
                )
            except Exception as e:
                logger.warning(f"XTTS failed, trying ElevenLabs fallback: {e}")
                if self.elevenlabs_key:
                    return await self._generate_elevenlabs(text, output_path, voice_id)
                raise
        elif self.elevenlabs_key:
            return await self._generate_elevenlabs(text, output_path, voice_id)
        else:
            raise ValueError("No TTS service configured. Enable XTTS or provide ElevenLabs API key.")
    
    async def _generate_xtts(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> Path:
        """Generate audio using local XTTS."""
        
        # Try XTTS server first (common setup)
        xtts_server_url = f"{settings.xtts_server_url}/tts_to_audio/"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Check if server is available
                try:
                    await client.get(settings.xtts_server_url, timeout=5.0)
                    server_available = True
                except:
                    server_available = False
                
                if server_available:
                    # Use XTTS server
                    speaker = speaker_wav or settings.xtts_speaker_wav
                    response = await client.post(
                        xtts_server_url,
                        json={
                            "text": text,
                            "speaker_wav": speaker,
                            "language": language
                        }
                    )
                    response.raise_for_status()
                    
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    
                    logger.info(f"XTTS server generated audio: {output_path}")
                    return output_path
                
        except Exception as e:
            logger.warning(f"XTTS server not available: {e}")
        
        # Fallback: Use XTTS CLI (TTS command from coqui-ai TTS)
        try:
            speaker_arg = []
            if speaker_wav or settings.xtts_speaker_wav:
                speaker_arg = ["--speaker_wav", speaker_wav or settings.xtts_speaker_wav]
            
            cmd = [
                "tts",
                "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                "--text", text,
                "--out_path", str(output_path),
                "--language_idx", language,
            ] + speaker_arg
            
            logger.info(f"Running XTTS CLI: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(f"TTS CLI failed: {result.stderr}")
            
            logger.info(f"XTTS CLI generated audio: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"XTTS generation failed: {e}")
            raise
    
    async def _generate_elevenlabs(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None
    ) -> Path:
        """Generate audio using ElevenLabs API."""
        
        voice = voice_id or settings.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key
        }
        
        data = {
            "text": text,
            "model_id": settings.elevenlabs_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                
                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"ElevenLabs generated audio with voice {voice}: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            raise
    
    async def generate_with_niche_config(
        self,
        text: str,
        output_path: Path,
        niche,
        language: str = "en"
    ) -> Path:
        """
        Generate audio using niche-specific configuration.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio
            niche: Niche object with TTS configuration
            language: Language code
        """
        from app.models.niche import NicheModelConfig
        
        config = NicheModelConfig.from_niche(niche, settings)
        
        return await self.generate_audio(
            text=text,
            output_path=output_path,
            provider=config.tts_provider,
            voice_id=config.voice_id,
            language=language
        )
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        try:
            ffprobe = settings.ffprobe_path
            cmd = [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    async def list_elevenlabs_voices(self) -> list:
        """List available ElevenLabs voices."""
        if not self.elevenlabs_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": self.elevenlabs_key}
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "voice_id": v["voice_id"],
                        "name": v["name"],
                        "category": v.get("category", "unknown"),
                        "labels": v.get("labels", {})
                    }
                    for v in data.get("voices", [])
                ]
        except Exception as e:
            logger.error(f"Failed to list ElevenLabs voices: {e}")
            return []


tts_service = TTSService()
