"""
TTS service - text-to-speech using XTTS (local) or ElevenLabs (fallback).
Supports per-niche voice configuration.
Long scripts are chunked to avoid CLI timeouts (each chunk gets its own subprocess).
Narration extraction strips visual/camera directions so only spoken text goes to TTS.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
import httpx
from loguru import logger

from app.core.config import settings

# Max characters per single TTS CLI/server call; smaller = faster per-chunk, more reliable
MAX_CHARS_PER_TTS_CHUNK = 800
# Per-chunk timeout: Server mode is fast (model stays loaded); CLI reloads entire model per call
TTS_SERVER_CHUNK_TIMEOUT = 600   # Server: model in memory, just inference
TTS_CLI_CHUNK_TIMEOUT = 600      # CLI: loads 1.87GB model + inference per chunk


def _resolve_tts_cli() -> str:
    """Resolve the path to the 'tts' CLI binary, preferring the venv Scripts dir."""
    import sys
    import shutil
    # Try the same venv that's running the backend
    venv_dir = Path(sys.executable).parent
    for name in ["tts.exe", "tts"]:
        candidate = venv_dir / name
        if candidate.exists():
            return str(candidate)
    # Try the contentops-core venv explicitly
    root = Path(settings.base_path) if hasattr(settings, "base_path") else Path(__file__).resolve().parents[3]
    for scripts_dir in [root / "venv" / "Scripts", root / "venv" / "bin"]:
        for name in ["tts.exe", "tts"]:
            candidate = scripts_dir / name
            if candidate.exists():
                return str(candidate)
    # Fall back to PATH
    found = shutil.which("tts")
    if found:
        return found
    return "tts"  # Last resort — will fail with FileNotFoundError if not on PATH


def _split_tts_chunks(text: str, max_chars: int = MAX_CHARS_PER_TTS_CHUNK) -> List[str]:
    """Split text into chunks at sentence boundaries for chunked TTS. Returns list of non-empty strings."""
    text = text.strip()
    if not text or len(text) <= max_chars:
        return [text] if text else []
    chunks = []
    # Split on sentence boundaries (., !, ?, or double newline)
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n", text)
    current = []
    current_len = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 1 <= max_chars:
            current.append(p)
            current_len += len(p) + 1
        else:
            if current:
                chunks.append(" ".join(current))
            if len(p) > max_chars:
                # One very long sentence: split by commas or mid-space
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars].strip())
                current = []
                current_len = 0
            else:
                current = [p]
                current_len = len(p) + 1
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c]


def _sanitize_text_for_tts_cli(text: str) -> str:
    """Remove/replace characters that cause UnicodeEncodeError in TTS CLI on Windows (e.g. emojis)."""
    if not text:
        return text
    # Remove emoji and other non-BMP/symbols that break Windows console (cp1252)
    def replace_char(m: re.Match) -> str:
        c = m.group(0)
        return " " if ord(c) > 0xFFFF or (0x1F300 <= ord(c) <= 0x1F9FF) else c
    return re.sub(r".", replace_char, text)


# ---------------------------------------------------------------------------
# Narration extraction – strips visual/camera directions from cinematic scripts
# so that only human-spoken narration is sent to TTS.
# ---------------------------------------------------------------------------

# Patterns that indicate a line is a visual direction, NOT spoken narration
_VISUAL_DIRECTION_PATTERNS = [
    # Section / shot headers  e.g. "OPENING – LOSS (0:00–0:12)"
    re.compile(r'^[A-Z][A-Z\s\u2013\-:]*\(\d+:\d+', re.MULTILINE),
    # All-caps section headers  e.g. "THE THREAT – DECEPTION"
    re.compile(r'^[A-Z][A-Z\s\u2013\-]{5,}$', re.MULTILINE),
    # Camera / visual direction keywords
    re.compile(
        r'^\s*(Camera|Cut to|Fade |Black screen|Slow fade|Close-up|'
        r'Hold |Hard cut|Subtitle|On screen|Multiple monitors|'
        r'The (room|UI|environment|code|red|lighting|chaos|monitor)|'
        r'A (senior|steady|floating|golden)|'
        r'Three luminous|Thin emerald|'
        r'Glass shards|The nodes|'
        r'Underneath:|Everything looks|Then \u2014|'
        r'Her breathing|Subtle |Elegant typography)',
        re.IGNORECASE | re.MULTILINE
    ),
    # Timing markers  e.g. "0–20 sec → Anxiety"
    re.compile(r'^\d+[\u2013\-]\d+\s*sec', re.MULTILINE),
    # Lines that are just structural markers
    re.compile(r'^\s*(Color Story:|Emotional Structure|by Mas-AI)', re.IGNORECASE | re.MULTILINE),
]


def _extract_narration_text(text: str) -> str:
    """
    Extract only the narration/spoken text from a script that may contain
    visual directions, camera instructions, and scene descriptions.

    For cinematic scripts (like the ones used for Daena promos), this strips
    visual cues and keeps only what a voice actor would read aloud.

    If the script doesn't appear to be a cinematic directive (no visual
    direction patterns found), returns the original text unchanged.
    """
    if not text or len(text) < 100:
        return text

    lines = text.split('\n')
    # Quick heuristic: if the text has enough visual direction markers,
    # treat it as a cinematic script and extract narration only
    direction_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pat in _VISUAL_DIRECTION_PATTERNS:
            if pat.search(stripped):
                direction_count += 1
                break

    # If < 15% of lines match visual directions, this is probably pure narration
    non_empty = [l for l in lines if l.strip()]
    if not non_empty or direction_count < max(3, len(non_empty) * 0.15):
        return text

    logger.info(
        f"Extracting narration from cinematic script: {direction_count}/{len(non_empty)} "
        f"lines are visual directions; stripping them for TTS."
    )

    # Extract narration lines
    narration_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip lines that match visual direction patterns
        is_direction = False
        for pat in _VISUAL_DIRECTION_PATTERNS:
            if pat.search(stripped):
                is_direction = True
                break
        if is_direction:
            continue

        # Extract quoted text (often the actual spoken words in cinematic scripts)
        quotes = re.findall(r'[\u201c""]([^\u201d""]+)[\u201d""]', stripped)
        if quotes:
            narration_lines.extend(quotes)
            continue

        # Keep sentences that look like narration (have verbs, are > 40 chars, etc.)
        if len(stripped) > 40 and not stripped.isupper():
            narration_lines.append(stripped)

    narration = ' '.join(narration_lines).strip()

    # If extraction produced too little text, fall back to original
    if len(narration) < 50:
        logger.warning(
            "Narration extraction produced too little text; using original script for TTS."
        )
        return text

    logger.info(
        f"Narration extracted: {len(text)} chars -> {len(narration)} chars "
        f"({100 - int(len(narration)/len(text)*100)}% reduction)"
    )
    return narration


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
        
        # Extract narration-only text (strips visual/camera directions from cinematic scripts)
        narration = _extract_narration_text(text)
        if narration != text:
            logger.info(f"TTS: narration extracted from script ({len(text)} -> {len(narration)} chars)")
        
        # Determine provider
        use_provider = provider or self.default_provider
        
        if use_provider == "elevenlabs" and self.elevenlabs_key:
            return await self._generate_elevenlabs(narration, output_path, voice_id)
        elif use_provider == "xtts" or self.xtts_enabled:
            try:
                return await self._generate_xtts(
                    narration, output_path, 
                    speaker_wav=speaker_wav or voice_id,
                    language=language
                )
            except Exception as e:
                logger.warning(f"XTTS failed, trying ElevenLabs fallback: {e}")
                if self.elevenlabs_key:
                    return await self._generate_elevenlabs(narration, output_path, voice_id)
                raise
        elif self.elevenlabs_key:
            return await self._generate_elevenlabs(narration, output_path, voice_id)
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
        
        # Try XTTS server first (common setup). Server must expose POST /tts_to_audio/ or /tts_to_audio
        base = settings.xtts_server_url.rstrip("/")
        urls_to_try = [f"{base}/tts_to_audio/", f"{base}/tts_to_audio"]
        
        try:
            async with httpx.AsyncClient(timeout=TTS_SERVER_CHUNK_TIMEOUT) as client:
                # Retry server check: the model takes 30-60s to load after start_xtts.bat
                server_available = False
                for attempt in range(3):
                    try:
                        await client.get(base, timeout=8.0)
                        server_available = True
                        break
                    except Exception:
                        if attempt < 2:
                            import asyncio
                            logger.info(f"XTTS server not ready (attempt {attempt+1}/3), waiting 10s...")
                            await asyncio.sleep(10)
                        else:
                            logger.warning("XTTS server not available after 3 attempts; falling back to CLI")
                
                if server_available:
                    speaker = speaker_wav or settings.xtts_default_speaker_wav

                    # Chunk text for server mode too (avoids server timeout on very long text)
                    chunks = _split_tts_chunks(text)
                    if not chunks:
                        raise ValueError("TTS input text is empty.")

                    if len(chunks) == 1:
                        # Single chunk: simple server call
                        payload = {"text": chunks[0], "speaker_wav": speaker, "language": language}
                        response = None
                        for url in urls_to_try:
                            response = await client.post(url, json=payload)
                            if response.status_code != 404:
                                break
                        if response and response.status_code == 404:
                            raise Exception(
                                "XTTS server returned 404 for TTS. The server must expose POST /tts_to_audio/ "
                                "accepting JSON: { text, speaker_wav, language } and returning audio bytes."
                            )
                        response.raise_for_status()
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        logger.info(f"XTTS server generated audio: {output_path}")
                        return output_path
                    else:
                        # Multi-chunk: generate each chunk via server then concatenate
                        logger.info(f"XTTS server chunked mode: {len(chunks)} chunks")
                        temp_dir = Path(tempfile.mkdtemp(prefix="tts_server_chunks_"))
                        wav_paths = []
                        try:
                            for ci, chunk in enumerate(chunks):
                                chunk_path = temp_dir / f"chunk_{ci:03d}.wav"
                                payload = {"text": chunk, "speaker_wav": speaker, "language": language}
                                response = None
                                for url in urls_to_try:
                                    response = await client.post(url, json=payload)
                                    if response.status_code != 404:
                                        break
                                if response and response.status_code == 404:
                                    raise Exception("XTTS server 404 on /tts_to_audio")
                                response.raise_for_status()
                                with open(chunk_path, "wb") as f:
                                    f.write(response.content)
                                if chunk_path.exists() and chunk_path.stat().st_size > 0:
                                    wav_paths.append(chunk_path)
                                    logger.info(f"XTTS server chunk {ci+1}/{len(chunks)} done")
                            # Concatenate chunks
                            from pydub import AudioSegment
                            combined = None
                            for p in wav_paths:
                                seg = AudioSegment.from_wav(str(p))
                                combined = seg if combined is None else combined + seg
                            if combined is not None:
                                output_path = Path(output_path)
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                combined.export(str(output_path), format="wav")
                            logger.info(f"XTTS server generated audio (chunked): {output_path}")
                            return output_path
                        finally:
                            for p in wav_paths:
                                try: p.unlink(missing_ok=True)
                                except Exception: pass
                            try: temp_dir.rmdir()
                            except Exception: pass
                
        except Exception as e:
            logger.warning(f"XTTS server not available: {e}")
        
        # Fallback: Use XTTS CLI (TTS command from coqui-ai TTS)
        try:
            speaker_path = speaker_wav or settings.xtts_default_speaker_wav
            if not speaker_path:
                raise ValueError(
                    "XTTS is a multi-speaker model and needs a reference voice. "
                    "Set XTTS_SPEAKER_WAV in backend/.env to a path to a .wav file (10–30 sec of clear speech), "
                    "or add daena.wav to models/xtts/voices/ or data/assets/voices/, "
                    "or run the XTTS server (start_xtts.bat) which can use a default speaker."
                )
            # Sanitize so emoji/symbols don't cause UnicodeEncodeError when TTS CLI prints to console on Windows
            text_for_cli = _sanitize_text_for_tts_cli(text)
            env = os.environ.copy()
            env["COQUI_TOS_AGREED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            existing = env.get("PYTHONWARNINGS", "")
            env["PYTHONWARNINGS"] = f"{existing},ignore::FutureWarning" if existing else "ignore::FutureWarning"
            speaker_arg = ["--speaker_wav", str(speaker_path)]

            chunks = _split_tts_chunks(text_for_cli)
            if not chunks:
                raise ValueError("TTS input text is empty after sanitization.")
            if len(chunks) > 1:
                # Long script: generate per chunk then concatenate to avoid single-call timeout
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temp_dir = Path(tempfile.mkdtemp(prefix="tts_chunks_"))
                wav_paths = []
                try:
                    for i, chunk in enumerate(chunks):
                        chunk_path = temp_dir / f"chunk_{i:03d}.wav"
                        cmd = [
                            _resolve_tts_cli(),
                            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                            "--text", chunk,
                            "--out_path", str(chunk_path),
                            "--language_idx", language,
                        ] + speaker_arg
                        logger.info(f"XTTS CLI chunk {i + 1}/{len(chunks)} ({len(chunk)} chars), timeout {TTS_CLI_CHUNK_TIMEOUT}s")
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=TTS_CLI_CHUNK_TIMEOUT,
                            env=env, encoding="utf-8", errors="replace"
                        )
                        if not chunk_path.exists() or chunk_path.stat().st_size == 0:
                            raise Exception(
                                f"TTS CLI chunk {i + 1}/{len(chunks)} produced no audio. "
                                f"{'stderr: ' + result.stderr[:400] if result.stderr else 'Check TTS model and speaker_wav.'}"
                            )
                        wav_paths.append(chunk_path)
                    # Concatenate with pydub
                    from pydub import AudioSegment
                    combined = None
                    for p in wav_paths:
                        seg = AudioSegment.from_wav(str(p))
                        combined = seg if combined is None else combined + seg
                    if combined is not None:
                        combined.export(str(output_path), format="wav")
                    if not output_path.exists() or output_path.stat().st_size == 0:
                        raise Exception("TTS chunk concatenation produced no output")
                    logger.info(f"XTTS CLI generated audio (chunked): {output_path}")
                    return output_path
                finally:
                    for p in wav_paths:
                        try:
                            p.unlink(missing_ok=True)
                        except Exception:
                            pass
                    try:
                        temp_dir.rmdir()
                    except Exception:
                        pass
                return output_path

            # Single chunk: one TTS CLI call
            single_text = chunks[0]
            cmd = [
                _resolve_tts_cli(),
                "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
                "--text", single_text,
                "--out_path", str(output_path),
                "--language_idx", language,
            ] + speaker_arg
            logger.info(f"Running XTTS CLI: {' '.join(cmd[:5])}... (timeout {TTS_CLI_CHUNK_TIMEOUT}s)")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=TTS_CLI_CHUNK_TIMEOUT,
                env=env, encoding="utf-8", errors="replace"
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                if result.returncode != 0 and result.stderr:
                    logger.warning(f"TTS CLI had non-zero exit but produced audio; stderr: {result.stderr[:500]}")
                logger.info(f"XTTS CLI generated audio: {output_path}")
                return output_path
            if result.returncode != 0:
                raise Exception(f"TTS CLI failed: {result.stderr}")
            logger.info(f"XTTS CLI generated audio: {output_path}")
            return output_path

        except subprocess.TimeoutExpired as e:
            logger.error(f"XTTS CLI timed out: {e}")
            raise Exception(
                f"TTS CLI timed out after {TTS_CLI_CHUNK_TIMEOUT}s. "
                "Long scripts are chunked automatically. "
                "For faster TTS, start the XTTS server (start_xtts.bat) — it keeps the model in memory. "
                "Or increase TTS_CLI_CHUNK_TIMEOUT in tts_service.py."
            )
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
        language: str = "en",
        override_voice_id: Optional[str] = None,
    ) -> Path:
        """
        Generate audio using niche-specific configuration.
        When override_voice_id is set (e.g. from job), use it instead of niche default.
        """
        from app.models.niche import NicheModelConfig

        config = NicheModelConfig.from_niche(niche, settings)
        voice_id = override_voice_id if override_voice_id else config.voice_id
        return await self.generate_audio(
            text=text,
            output_path=output_path,
            provider=config.tts_provider,
            voice_id=voice_id,
            speaker_wav=override_voice_id if override_voice_id else None,
            language=language,
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
