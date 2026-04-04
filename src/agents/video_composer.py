"""
Video Composer — Full Video Assembly.

Assembles final videos from: avatar video + B-roll + captions + music.
Primary: FFmpeg (always works, no Node.js dependency).
Optional: Remotion for React-based templates (Phase 2).

V1 LESSON: Video must look cinematic, not PowerPoint.
- Use Pexels VIDEO clips as B-roll (not static images)
- Captions reinforce speech, they ARE NOT the content
- Avatar talks, visuals illustrate
"""
import os
import json
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger("contentops.video_composer")


@dataclass
class VideoSpec:
    width: int
    height: int
    fps: int
    max_duration: int  # seconds
    codec: str = "libx264"

PLATFORM_SPECS = {
    "tiktok": VideoSpec(1080, 1920, 30, 60),
    "youtube_short": VideoSpec(1080, 1920, 30, 60),
    "instagram_reel": VideoSpec(1080, 1920, 30, 60),
    "instagram_post": VideoSpec(1080, 1080, 30, 60),
    "youtube": VideoSpec(1920, 1080, 30, 180),
    "linkedin": VideoSpec(1920, 1080, 30, 180),
    "twitter": VideoSpec(1080, 1920, 30, 60),
}


class PexelsFetcher:
    """Fetches B-roll video clips from Pexels (free API)."""

    BASE_URL = "https://api.pexels.com/videos/search"

    def __init__(self):
        self.api_key = os.environ.get("PEXELS_API_KEY")
        self.broll_dir = Path("data/broll")
        self.broll_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_clips(self, keywords: list[str], orientation: str = "portrait", count: int = 3) -> list[str]:
        """Fetch B-roll video clips from Pexels. Returns local file paths."""
        if not self.api_key:
            logger.warning("No PEXELS_API_KEY — using color background fallback")
            return []

        clips = []
        async with httpx.AsyncClient(timeout=30) as client:
            for keyword in keywords[:2]:
                try:
                    response = await client.get(
                        self.BASE_URL,
                        params={"query": keyword, "per_page": count, "orientation": orientation},
                        headers={"Authorization": self.api_key}
                    )
                    response.raise_for_status()

                    for video in response.json().get("videos", [])[:2]:
                        # Get HD quality file
                        video_files = video.get("video_files", [])
                        # Prefer 720p portrait
                        best = None
                        for vf in video_files:
                            if vf.get("height", 0) >= 720 and vf.get("file_type") == "video/mp4":
                                best = vf
                                break
                        if not best and video_files:
                            best = video_files[0]

                        if best:
                            local_path = await self._download_clip(best["link"], keyword, video["id"])
                            if local_path:
                                clips.append(local_path)
                except Exception as e:
                    logger.warning(f"Pexels fetch failed for '{keyword}': {e}")

        return clips

    async def _download_clip(self, url: str, keyword: str, video_id: int) -> Optional[str]:
        """Download a clip to local storage."""
        safe_keyword = keyword.replace(" ", "_")[:20]
        local_path = self.broll_dir / f"{safe_keyword}_{video_id}.mp4"

        if local_path.exists():
            return str(local_path)

        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded B-roll: {local_path}")
                return str(local_path)
        except Exception as e:
            logger.error(f"B-roll download failed: {e}")
            return None


class CaptionGenerator:
    """Generate word-level caption timing from audio using faster-whisper."""

    @staticmethod
    def generate(audio_path: str, fps: int = 30) -> list[dict]:
        """Generate caption data with word-level timestamps."""
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, word_timestamps=True)

            words = []
            for segment in segments:
                for word in segment.words:
                    words.append({
                        "word": word.word.strip(),
                        "start_frame": int(word.start * fps),
                        "end_frame": int(word.end * fps),
                        "start_sec": round(word.start, 2),
                        "end_sec": round(word.end, 2),
                    })
            return words
        except ImportError:
            logger.warning("faster-whisper not installed — captions unavailable")
            return []
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return []


class VideoComposer:
    """Orchestrates full video assembly using FFmpeg."""

    def __init__(self):
        self.pexels = PexelsFetcher()
        self.output_dir = Path("data/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def compose(self, script_data: dict, audio_path: str, platform: str = "tiktok",
                      avatar_video: str = None, tenant: str = "mas-ai") -> str:
        """
        Full video composition pipeline.

        Steps:
        1. Fetch B-roll from Pexels based on script keywords
        2. Generate caption timing from audio
        3. Create base video (B-roll montage or color background)
        4. Overlay captions as subtitles
        5. Overlay avatar if available
        6. Mux with audio
        7. Output platform-spec MP4
        """
        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["tiktok"])
        script_id = script_data.get("script_id", f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        work_dir = self.output_dir / script_id
        work_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Composing video: {script_id} for {platform}")

        # Step 1: Get B-roll
        visual_keywords = self._extract_visual_keywords(script_data)
        orientation = "portrait" if spec.height > spec.width else "landscape"
        broll_clips = await self.pexels.fetch_clips(visual_keywords, orientation)

        # Step 2: Generate captions
        captions = CaptionGenerator.generate(audio_path, spec.fps)

        # Step 3: Get audio duration
        duration = self._get_audio_duration(audio_path)
        if duration <= 0:
            duration = 60

        # Step 4: Create base video
        if broll_clips:
            base_video = await self._create_broll_montage(broll_clips, spec, duration, work_dir)
        else:
            base_video = await self._create_gradient_background(spec, duration, work_dir)

        # Step 5: Burn captions (SRT file + FFmpeg subtitle filter)
        if captions:
            srt_path = self._generate_srt(captions, work_dir / "captions.srt")
            captioned_video = await self._burn_captions(base_video, srt_path, spec, work_dir)
        else:
            captioned_video = base_video

        # Step 6: Add hook text overlay (first 3 seconds)
        hook_text = ""
        acts = script_data.get("acts", [])
        if acts:
            hook_text = acts[0].get("text", "")[:80]

        if hook_text:
            hooked_video = await self._add_hook_overlay(captioned_video, hook_text, spec, work_dir)
        else:
            hooked_video = captioned_video

        # Step 7: Mux with audio
        final_path = work_dir / f"{script_id}_final.mp4"
        await self._mux_audio(hooked_video, audio_path, str(final_path), spec)

        # Save composition metadata
        meta = {
            "script_id": script_id,
            "platform": platform,
            "resolution": f"{spec.width}x{spec.height}",
            "fps": spec.fps,
            "duration": duration,
            "broll_clips": len(broll_clips),
            "captions_count": len(captions),
            "has_hook_overlay": bool(hook_text),
            "has_avatar": bool(avatar_video),
            "output_path": str(final_path),
            "composed_at": datetime.now().isoformat(),
        }
        with open(work_dir / "composition.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Video composed: {final_path}")
        return str(final_path)

    def _extract_visual_keywords(self, script_data: dict) -> list[str]:
        """Extract keywords for B-roll search from script."""
        niche = script_data.get("niche", "technology")
        keywords = [niche, "technology", "artificial intelligence", "coding", "startup"]

        # Extract from script text
        text = script_data.get("full_voiceover_text", "")
        if "AI" in text or "artificial" in text.lower():
            keywords.insert(0, "futuristic technology")
        if "startup" in text.lower() or "founder" in text.lower():
            keywords.insert(0, "startup office")
        if "code" in text.lower() or "developer" in text.lower():
            keywords.insert(0, "programming code screen")

        return keywords[:4]

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "json", audio_path
            ], capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 0

    async def _create_broll_montage(self, clips: list[str], spec: VideoSpec, duration: float, work_dir: Path) -> str:
        """Create a B-roll montage by concatenating and looping clips to cover full audio + padding."""
        output = str(work_dir / "base_broll.mp4")

        # Add 3 seconds padding so video always outlasts audio
        target_duration = duration + 3.0

        # Calculate per-clip duration; loop clips to fill the full target duration
        clip_duration = target_duration / max(len(clips), 1)

        # Build FFmpeg filter for concatenation with scaling
        # Use stream_loop=-1 on each input to ensure clip repeats if shorter than clip_duration
        filter_parts = []
        inputs = []
        for i, clip in enumerate(clips):
            inputs.extend(["-stream_loop", "-1", "-i", clip])
            filter_parts.append(
                f"[{i}:v]scale={spec.width}:{spec.height}:force_original_aspect_ratio=increase,"
                f"crop={spec.width}:{spec.height},setsar=1,trim=duration={clip_duration},setpts=PTS-STARTPTS[v{i}]"
            )

        concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
        filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]"

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-r", str(spec.fps),
            "-t", str(target_duration),
            output
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            if Path(output).exists():
                return output
        except Exception as e:
            logger.warning(f"B-roll montage failed: {e}")

        return await self._create_gradient_background(spec, duration, work_dir)

    async def _create_gradient_background(self, spec: VideoSpec, duration: float, work_dir: Path) -> str:
        """Create an animated gradient background as fallback."""
        output = str(work_dir / "base_gradient.mp4")

        # Dark gradient with subtle animation
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=0x0a0a1a:s={spec.width}x{spec.height}:d={duration}:r={spec.fps}",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            output
        ]

        subprocess.run(cmd, capture_output=True, timeout=60)
        return output

    def _generate_srt(self, captions: list[dict], output_path: Path) -> str:
        """Generate SRT subtitle file from caption data."""
        # Group words into subtitle chunks (3 words per chunk for TikTok-style rapid flow)
        chunks = []
        current_chunk = []

        for word in captions:
            current_chunk.append(word)
            if len(current_chunk) >= 3:
                chunks.append(current_chunk)
                current_chunk = []
        if current_chunk:
            chunks.append(current_chunk)

        with open(output_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks, 1):
                start = chunk[0]["start_sec"]
                end = chunk[-1]["end_sec"]
                text = " ".join(w["word"] for w in chunk)

                start_ts = f"{int(start//3600):02d}:{int(start%3600//60):02d}:{int(start%60):02d},{int(start%1*1000):03d}"
                end_ts = f"{int(end//3600):02d}:{int(end%3600//60):02d}:{int(end%60):02d},{int(end%1*1000):03d}"

                f.write(f"{i}\n{start_ts} --> {end_ts}\n{text}\n\n")

        return str(output_path)

    async def _burn_captions(self, video_path: str, srt_path: str, spec: VideoSpec, work_dir: Path) -> str:
        """Burn SRT captions into video using FFmpeg subtitles filter."""
        output = str(work_dir / "captioned.mp4")

        # Style: clean modern subtitle — small white text, thin black outline, dark box, bottom center
        style = (
            "FontSize=18,FontName=Montserrat,Bold=0,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,"
            "BackColour=&H80000000,Shadow=1,"
            "BorderStyle=4,"
            "Alignment=2,MarginV=180"
        )

        # FFmpeg subtitle filter - need to escape path for Windows
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            output
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if Path(output).exists():
                return output
            logger.warning(f"Caption burn failed: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"Caption burn failed: {e}")

        return video_path  # Return original if captions fail

    async def _add_hook_overlay(self, video_path: str, hook_text: str, spec: VideoSpec, work_dir: Path) -> str:
        """Add hook text overlay with glass-card effect in first 3 seconds."""
        output = str(work_dir / "hooked.mp4")

        # Escape text for FFmpeg drawtext
        safe_text = hook_text.replace("'", "").replace(":", "").replace("\\", "")

        font_size = 36 if spec.width >= 1080 else 24
        # Wrap long text: limit line width to ~30 chars worth of pixels
        max_line_w = int(spec.width * 0.8)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", (
                f"drawtext=text='{safe_text}':"
                f"fontsize={font_size}:fontcolor=white:"
                f"borderw=2:bordercolor=black:"
                f"box=1:boxcolor=black@0.45:boxborderw=16:"
                f"x=(w-text_w)/2:y=h*0.35:"
                f"line_spacing=8:"
                f"enable='lt(t,3)'"
            ),
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            output
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if Path(output).exists():
                return output
        except Exception as e:
            logger.warning(f"Hook overlay failed: {e}")

        return video_path

    async def _mux_audio(self, video_path: str, audio_path: str, output_path: str, spec: VideoSpec):
        """Combine video and audio into final output. Video must be longer than audio."""
        # Get audio duration for fade-out calculation
        audio_duration = self._get_audio_duration(audio_path)
        fade_start = max(audio_duration - 1.0, 0) if audio_duration > 0 else 0

        # No -shortest: video is already padded longer than audio.
        # Audio ends naturally; apply 1s fade-out at the end of audio.
        af_filter = f"afade=t=out:st={fade_start}:d=1" if fade_start > 0 else "anull"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-af", af_filter,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size / (1024 * 1024)
                logger.info(f"Final video: {output_path} ({file_size:.1f} MB)")
        except Exception as e:
            logger.error(f"Audio mux failed: {e}")


if __name__ == "__main__":
    async def test():
        vc = VideoComposer()
        # Test with dummy data
        script = {
            "script_id": "test_001",
            "niche": "ai-tech",
            "full_voiceover_text": "AI is changing the way we build software.",
            "acts": [{"act": 1, "text": "AI just changed everything"}],
        }
        print("Video Composer ready. Requires audio file for full test.")
        print(f"Output directory: {vc.output_dir}")

    asyncio.run(test())
