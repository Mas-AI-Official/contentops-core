"""
Daena Avatar Engine — Voice Generation Module.
Phase 1: TTS only (Kokoro free local / ElevenLabs production).
Phase 2: Lip sync animation (MuseTalk / SadTalker).

Budget rule: Kokoro for testing, ElevenLabs for final production only.
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contentops.avatar_engine")


class AvatarEngine:
    """Handles Daena avatar voice generation."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.audio_dir = self.data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def generate_voice(self, text: str, script_id: str, mode: str = "test") -> str:
        """Generate voice audio. mode='test' uses Kokoro (free), mode='production' uses ElevenLabs."""
        if mode == "production" and os.environ.get("ELEVENLABS_API_KEY"):
            return await self._generate_elevenlabs(text, script_id)
        return await self._generate_kokoro(text, script_id)

    async def _generate_kokoro(self, text: str, script_id: str) -> str:
        """Free local TTS using Kokoro-82M (PyTorch version)."""
        output_path = self.audio_dir / f"{script_id}.wav"
        try:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)

            from kokoro import KPipeline
            import soundfile as sf
            import numpy as np

            pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
            voice = os.environ.get("KOKORO_VOICE", "af_heart")

            # Generate all audio chunks
            audio_chunks = []
            for _, _, audio in pipeline(text, voice=voice, speed=1.05):
                audio_chunks.append(audio)

            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                sf.write(str(output_path), full_audio, 24000)
                duration = len(full_audio) / 24000
                logger.info(f"Kokoro TTS generated: {output_path} ({duration:.1f}s)")
                return str(output_path)

            logger.warning("Kokoro produced no audio")
            return await self._generate_silence(script_id, duration=30)
        except ImportError:
            logger.warning("kokoro not installed. Install: pip install kokoro soundfile")
            return await self._generate_silence(script_id, duration=30)
        except Exception as e:
            logger.error(f"Kokoro TTS failed: {e}")
            return await self._generate_silence(script_id, duration=30)

    async def _generate_elevenlabs(self, text: str, script_id: str) -> str:
        """Production TTS using ElevenLabs API."""
        output_path = self.audio_dir / f"{script_id}.wav"
        try:
            from elevenlabs import ElevenLabs

            client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
            audio = client.text_to_speech.convert(
                voice_id=os.environ.get("DAENA_VOICE_ID", "XrExE9yKIg1WjnnlVkGX"),
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128",
            )
            with open(str(output_path).replace(".wav", ".mp3"), "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            logger.info(f"ElevenLabs TTS generated: {output_path}")
            return str(output_path).replace(".wav", ".mp3")
        except Exception as e:
            logger.error(f"ElevenLabs failed: {e}. Falling back to Kokoro.")
            return await self._generate_kokoro(text, script_id)

    async def _generate_silence(self, script_id: str, duration: int = 30) -> str:
        """Generate silent WAV as placeholder."""
        import numpy as np
        import soundfile as sf

        output_path = self.audio_dir / f"{script_id}.wav"
        sample_rate = 44100
        samples = np.zeros(int(sample_rate * duration), dtype=np.float32)
        sf.write(str(output_path), samples, sample_rate)
        logger.info(f"Silence placeholder: {output_path}")
        return str(output_path)

    def get_avatar_image(self, mood: str = "default", tenant: str = "mas-ai") -> Optional[str]:
        """Select avatar image based on content mood."""
        mood_map = {
            "technical": "daena_professional_dark.png",
            "casual": "daena_casual_light.png",
            "urgent": "daena_urgent_high_contrast.png",
            "inspiring": "daena_inspiring_warm.png",
            "educational": "daena_professional_dark.png",
            "controversial": "daena_urgent_high_contrast.png",
            "humorous": "daena_casual_light.png",
            "default": "daena_neutral.png",
        }
        filename = mood_map.get(mood, mood_map["default"])
        avatar_path = Path(f"tenants/{tenant}/avatars/{filename}")
        if avatar_path.exists():
            return str(avatar_path)
        # Fallback to any available avatar
        avatars_dir = Path(f"tenants/{tenant}/avatars")
        if avatars_dir.exists():
            for f in avatars_dir.iterdir():
                if f.suffix in (".png", ".jpg", ".jpeg"):
                    return str(f)
        return None
