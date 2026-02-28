from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import os
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
            
    # Daena voice (explicit config or well-known paths)
    daena_path = None
    if getattr(settings, "xtts_daena_voice_wav", None) and Path(settings.xtts_daena_voice_wav).exists():
        daena_path = str(Path(settings.xtts_daena_voice_wav).resolve())
    if not daena_path:
        candidates = [
            settings.models_path / "xtts" / "voices" / "daena.wav",
            settings.data_path / "assets" / "voices" / "daena.wav",
            Path(__file__).resolve().parents[2] / "data" / "assets" / "voices" / "daena.wav",
        ]
        if os.environ.get("MODELS_ROOT"):
            candidates.insert(0, Path(os.environ["MODELS_ROOT"]) / "xtts" / "voices" / "daena.wav")
        for candidate in candidates:
            if candidate.exists():
                daena_path = str(candidate.resolve())
                break
        if not daena_path and os.environ.get("MODELS_ROOT"):
            voices_dir = Path(os.environ["MODELS_ROOT"]) / "xtts" / "voices"
            if voices_dir.exists():
                first_wav = next(voices_dir.glob("*.wav"), None)
                if first_wav:
                    daena_path = str(first_wav.resolve())
    if daena_path and not any(v.voice_id == daena_path for v in voices):
        voices.insert(0, VoiceInfo(voice_id=daena_path, name="Daena", category="cloned", provider="xtts"))

    # XTTS Voices (Local) from MODELS_ROOT/xtts/voices and models/xtts/voices/
    for xtts_voices_path in [
        Path(os.environ["MODELS_ROOT"]) / "xtts" / "voices" if os.environ.get("MODELS_ROOT") else None,
        settings.models_path / "xtts" / "voices",
    ]:
        if not xtts_voices_path or not xtts_voices_path.exists():
            continue
        for wav_file in xtts_voices_path.glob("*.wav"):
            path_str = str(wav_file.resolve())
            if any(v.voice_id == path_str for v in voices):
                continue
            name = wav_file.stem.replace("_", " ").replace("voice", "").strip().title() or wav_file.stem
            voices.append(VoiceInfo(voice_id=path_str, name=name, category="cloned", provider="xtts"))

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
