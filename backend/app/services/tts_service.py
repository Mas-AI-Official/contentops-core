"""
TTS service - text-to-speech using XTTS (local) or ElevenLabs (fallback).
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
        self.use_xtts = settings.xtts_enabled
        self.elevenlabs_key = settings.elevenlabs_api_key
    
    async def generate_audio(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
        speaker_wav: Optional[str] = None
    ) -> Path:
        """Generate audio from text."""
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.use_xtts:
            try:
                return await self._generate_xtts(text, output_path, speaker_wav)
            except Exception as e:
                logger.warning(f"XTTS failed, trying fallback: {e}")
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
        speaker_wav: Optional[str] = None
    ) -> Path:
        """Generate audio using local XTTS."""
        
        # Check if XTTS server is running (common setup) or use CLI
        xtts_server_url = "http://localhost:8020/tts_to_audio/"
        
        try:
            # Try XTTS server first
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Check if server is available
                try:
                    await client.get("http://localhost:8020/", timeout=5.0)
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
                            "language": "en"
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
            # Write text to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(text)
                text_file = f.name
            
            speaker_arg = []
            if speaker_wav or settings.xtts_speaker_wav:
                speaker_arg = ["--speaker_wav", speaker_wav or settings.xtts_speaker_wav]
            
            cmd = [
                "tts",
                "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                "--text", text,
                "--out_path", str(output_path),
                "--language_idx", "en",
            ] + speaker_arg
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            os.unlink(text_file)
            
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
            "model_id": "eleven_monolingual_v1",
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
                
                logger.info(f"ElevenLabs generated audio: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            raise
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        try:
            cmd = [
                settings.ffmpeg_path.replace("ffmpeg", "ffprobe"),
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


tts_service = TTSService()
