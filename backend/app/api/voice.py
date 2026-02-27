from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import uuid

from app.services import tts_service
from app.core.config import settings

router = APIRouter(prefix="/voice", tags=["voice"])

class SynthesizeRequest(BaseModel):
    text: str
    provider: Optional[str] = None  # xtts, elevenlabs
    voice_id: Optional[str] = None
    language: str = "en"

class VoiceInfo(BaseModel):
    voice_id: str
    name: str
    category: Optional[str] = None
    provider: str

@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """
    Generate speech from text using the configured provider.
    Prioritizes ElevenLabs if configured, falls back to XTTS.
    """
    try:
        # Create a temporary file path
        filename = f"speech_{uuid.uuid4()}.wav"
        output_path = settings.data_path / "temp" / filename
        
        # Generate audio
        audio_path = await tts_service.generate_audio(
            text=request.text,
            output_path=output_path,
            provider=request.provider,
            voice_id=request.voice_id,
            language=request.language
        )
        
        return FileResponse(
            path=audio_path,
            media_type="audio/wav",
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices():
    """List available voices from all providers."""
    voices = []
    
    # ElevenLabs voices
    if settings.elevenlabs_api_key:
        try:
            el_voices = await tts_service.list_elevenlabs_voices()
            for v in el_voices:
                voices.append(VoiceInfo(
                    voice_id=v["voice_id"],
                    name=v["name"],
                    category=v["category"],
                    provider="elevenlabs"
                ))
        except Exception as e:
            print(f"Failed to fetch ElevenLabs voices: {e}")
            
    # XTTS Voices (Local)
    xtts_voices_path = settings.models_path / "xtts" / "voices"
    if xtts_voices_path.exists():
        for wav_file in xtts_voices_path.glob("*.wav"):
            voices.append(VoiceInfo(
                voice_id=str(wav_file),
                name=wav_file.stem.replace("_", " ").replace("voice", "").strip().title(),
                category="cloned",
                provider="xtts"
            ))
    
    # Ensure default is included if set and not already found
    if settings.xtts_speaker_wav:
        default_path = str(Path(settings.xtts_speaker_wav))
        if not any(v.voice_id == default_path for v in voices):
            voices.append(VoiceInfo(
                voice_id=default_path,
                name="Local Default (XTTS)",
                category="cloned",
                provider="xtts"
            ))
        
    return voices
