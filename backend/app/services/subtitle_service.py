"""
Subtitle service - generates subtitles using Whisper/faster-whisper.
"""
import subprocess
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings


@dataclass
class SubtitleSegment:
    """A single subtitle segment."""
    start: float
    end: float
    text: str


class SubtitleService:
    """Service for generating and processing subtitles."""
    
    def __init__(self):
        self.model_size = settings.whisper_model
        self.device = settings.whisper_device
        self._model = None
    
    def _get_model(self):
        """Lazy load the whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type="float16" if self.device == "cuda" else "int8"
                )
                logger.info(f"Loaded faster-whisper model: {self.model_size}")
            except Exception as e:
                logger.error(f"Failed to load whisper model: {e}")
                raise
        return self._model
    
    def transcribe(self, audio_path: Path) -> List[SubtitleSegment]:
        """Transcribe audio file to subtitle segments."""
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        model = self._get_model()
        
        try:
            segments, info = model.transcribe(
                str(audio_path),
                beam_size=5,
                word_timestamps=True,
                vad_filter=True
            )
            
            result = []
            for segment in segments:
                result.append(SubtitleSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip()
                ))
            
            logger.info(f"Transcribed {len(result)} segments from {audio_path}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def generate_srt(
        self,
        audio_path: Path,
        output_path: Path,
        max_chars_per_line: int = 40
    ) -> Path:
        """Generate SRT subtitle file from audio."""
        
        segments = self.transcribe(audio_path)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                # Format timestamps
                start_time = self._format_srt_time(seg.start)
                end_time = self._format_srt_time(seg.end)
                
                # Wrap text if needed
                text = self._wrap_text(seg.text, max_chars_per_line)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        
        logger.info(f"Generated SRT file: {output_path}")
        return output_path
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _wrap_text(self, text: str, max_chars: int) -> str:
        """Wrap text to fit within max characters per line."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def generate_ass(
        self,
        audio_path: Path,
        output_path: Path,
        style: str = "default"
    ) -> Path:
        """Generate ASS subtitle file with styling."""
        
        segments = self.transcribe(audio_path)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ASS header with styling
        ass_content = """[Script Info]
Title: Content Factory Subtitles
ScriptType: v4.00+
PlayDepth: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,30,30,100,1
Style: Highlighted,Arial,80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,30,30,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        for seg in segments:
            start_time = self._format_ass_time(seg.start)
            end_time = self._format_ass_time(seg.end)
            text = seg.text.replace("\n", "\\N")
            
            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        logger.info(f"Generated ASS file: {output_path}")
        return output_path
    
    def _format_ass_time(self, seconds: float) -> str:
        """Format seconds to ASS time format (H:MM:SS.cc)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
    
    def convert_to_srt(self, ass_path: Path, srt_path: Path) -> Path:
        """Convert ASS to SRT using FFmpeg."""
        
        cmd = [
            settings.ffmpeg_path,
            "-i", str(ass_path),
            "-y",
            str(srt_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"ASS to SRT conversion failed: {result.stderr}")
            raise Exception(f"Conversion failed: {result.stderr}")
        
        return srt_path


subtitle_service = SubtitleService()
