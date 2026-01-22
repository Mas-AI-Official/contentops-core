"""
Render service - creates final video using FFmpeg or LTX.
Supports hybrid: LTX generates base video, FFmpeg adds audio/subtitles/logo.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger

from app.core.config import settings

# Import LTX service conditionally
try:
    from app.services.ltx_service import ltx_service
    LTX_AVAILABLE = True
except ImportError:
    LTX_AVAILABLE = False
    ltx_service = None


@dataclass
class RenderConfig:
    """Video render configuration."""
    width: int = 1080
    height: int = 1920
    fps: int = 30
    
    # Audio
    audio_path: Optional[Path] = None
    bg_music_path: Optional[Path] = None
    bg_music_volume: float = 0.1
    
    # Visuals
    background_video: Optional[Path] = None
    background_color: str = "#000000"
    
    # Subtitles
    subtitle_path: Optional[Path] = None
    burn_subtitles: bool = True
    
    # Watermark
    logo_path: Optional[Path] = None
    logo_position: str = "top_right"  # top_left, top_right, bottom_left, bottom_right
    logo_scale: float = 0.1  # Relative to video width
    
    # Output
    output_path: Optional[Path] = None
    quality_preset: str = "medium"  # ultrafast, fast, medium, slow


class RenderService:
    """Service for rendering final videos."""
    
    def __init__(self):
        self.ffmpeg = settings.ffmpeg_path
    
    async def render_video(self, config: RenderConfig, script_text: Optional[str] = None) -> Path:
        """
        Render a video with all components.
        
        Args:
            config: Render configuration
            script_text: Optional script text for LTX generation
        """
        
        if not config.output_path:
            raise ValueError("Output path is required")
        
        output_path = Path(config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use LTX if enabled and script provided
        if (settings.video_gen_provider == "ltx" and script_text and 
            LTX_AVAILABLE and ltx_service):
            try:
                logger.info("Using LTX for video generation...")
                # Generate base video with LTX
                ltx_output = output_path.parent / f"{output_path.stem}_ltx.mp4"
                
                # Get audio duration for LTX clip length
                audio_duration = 5  # default
                if config.audio_path and Path(config.audio_path).exists():
                    audio_duration = self.get_audio_duration(config.audio_path)
                
                # Limit to 5 seconds for 8GB VRAM
                ltx_duration = min(int(audio_duration), 5)
                
                await ltx_service.generate_video_from_text(
                    text=script_text,
                    output_path=ltx_output,
                    prompt=None,  # Use text as prompt
                    width=854,  # 480p for 8GB VRAM
                    height=480,
                    duration_seconds=ltx_duration,
                    fps=24
                )
                
                # Now composite with FFmpeg: add audio, subtitles, logo, music
                config.background_video = ltx_output
                config.width = 1080  # Scale up to final resolution
                config.height = 1920
                
                logger.info("Compositing LTX video with audio/subtitles/logo...")
                
            except Exception as e:
                logger.warning(f"LTX generation failed, falling back to FFmpeg: {e}")
                # Fall through to FFmpeg rendering
        
        # Build FFmpeg command
        cmd = self._build_ffmpeg_command(config)
        
        logger.info(f"Rendering video: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Render failed: {result.stderr}")
            
            # Verify output
            if not output_path.exists():
                raise Exception("Output file was not created")
            
            file_size = output_path.stat().st_size
            logger.info(f"Video rendered: {output_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("Render timed out")
            raise Exception("Render timed out after 10 minutes")
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        try:
            cmd = [
                settings.ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 5.0
    
    def _build_ffmpeg_command(self, config: RenderConfig) -> List[str]:
        """Build the FFmpeg command for rendering."""
        
        cmd = [self.ffmpeg, "-y"]  # -y to overwrite
        
        inputs = []
        filter_complex = []
        
        # Input 0: Background video or color
        if config.background_video and Path(config.background_video).exists():
            cmd.extend(["-stream_loop", "-1", "-i", str(config.background_video)])
            inputs.append("video")
            # Scale and crop background to fit
            filter_complex.append(
                f"[0:v]scale={config.width}:{config.height}:force_original_aspect_ratio=increase,"
                f"crop={config.width}:{config.height},setsar=1[bg]"
            )
        else:
            # Create solid color background
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c={config.background_color}:s={config.width}x{config.height}:r={config.fps}"
            ])
            inputs.append("color")
            filter_complex.append(f"[0:v]copy[bg]")
        
        # Input 1: Main audio (narration)
        audio_input_idx = len(inputs)
        if config.audio_path and Path(config.audio_path).exists():
            cmd.extend(["-i", str(config.audio_path)])
            inputs.append("audio")
        
        # Input 2: Background music (optional)
        music_input_idx = None
        if config.bg_music_path and Path(config.bg_music_path).exists():
            music_input_idx = len(inputs)
            cmd.extend(["-i", str(config.bg_music_path)])
            inputs.append("music")
        
        # Build video filter chain
        current_video = "[bg]"
        
        # Add logo watermark
        if config.logo_path and Path(config.logo_path).exists():
            logo_idx = len(inputs)
            cmd.extend(["-i", str(config.logo_path)])
            inputs.append("logo")
            
            # Calculate logo size and position
            logo_w = int(config.width * config.logo_scale)
            
            positions = {
                "top_left": f"x=20:y=20",
                "top_right": f"x=W-w-20:y=20",
                "bottom_left": f"x=20:y=H-h-20",
                "bottom_right": f"x=W-w-20:y=H-h-20",
            }
            pos = positions.get(config.logo_position, positions["top_right"])
            
            filter_complex.append(f"[{logo_idx}:v]scale={logo_w}:-1[logo_scaled]")
            filter_complex.append(f"{current_video}[logo_scaled]overlay={pos}[with_logo]")
            current_video = "[with_logo]"
        
        # Add subtitles
        if config.burn_subtitles and config.subtitle_path and Path(config.subtitle_path).exists():
            subtitle_path = str(config.subtitle_path).replace("\\", "/").replace(":", "\\:")
            
            # Check if ASS or SRT
            if str(config.subtitle_path).endswith(".ass"):
                filter_complex.append(f"{current_video}ass='{subtitle_path}'[with_subs]")
            else:
                filter_complex.append(
                    f"{current_video}subtitles='{subtitle_path}':force_style="
                    f"'FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
                    f"Alignment=2,MarginV=80'[with_subs]"
                )
            current_video = "[with_subs]"
        
        # Finalize video
        filter_complex.append(f"{current_video}fps={config.fps}[vout]")
        
        # Build audio filter chain
        if "audio" in inputs:
            audio_filters = []
            
            if music_input_idx is not None:
                # Mix narration with background music
                # Get duration from narration
                audio_filters.append(
                    f"[{audio_input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[narration];"
                    f"[{music_input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                    f"volume={config.bg_music_volume}[music_vol];"
                    f"[narration][music_vol]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
            else:
                audio_filters.append(f"[{audio_input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[aout]")
            
            filter_complex.extend(audio_filters)
        
        # Combine all filters
        full_filter = ";".join(filter_complex)
        cmd.extend(["-filter_complex", full_filter])
        
        # Map outputs
        cmd.extend(["-map", "[vout]"])
        if "audio" in inputs:
            cmd.extend(["-map", "[aout]"])
        
        # Output settings
        preset_map = {
            "ultrafast": "ultrafast",
            "fast": "fast",
            "medium": "medium",
            "slow": "slow"
        }
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", preset_map.get(config.quality_preset, "medium"),
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(config.output_path)
        ])
        
        return cmd
    
    def get_video_duration(self, video_path: Path) -> float:
        """Get duration of a video file."""
        cmd = [
            self.ffmpeg.replace("ffmpeg", "ffprobe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def get_video_info(self, video_path: Path) -> dict:
        """Get detailed video information."""
        cmd = [
            self.ffmpeg.replace("ffmpeg", "ffprobe"),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            import json
            return json.loads(result.stdout)
        except:
            return {}
    
    def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float = 1.0
    ) -> Path:
        """Generate a thumbnail from video."""
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg,
            "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Thumbnail generation failed: {result.stderr}")
            raise Exception(f"Thumbnail failed: {result.stderr}")
        
        return output_path


render_service = RenderService()
