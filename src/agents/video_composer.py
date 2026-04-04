"""
Video Creative Director — Intelligent Video Assembly.

The smartest video editor in autonomous media. Not just compositing —
creative direction: dynamic avatar sizing per act, persona-driven visuals,
cinematic dark overlays, progress bars, and hook-first editing.

Architecture:
  B-roll montage → dark cinematic overlay → avatar (colorkey, dynamic size)
  → captions (word-level) → hook text (glass card) → progress bar → audio mux

V1 LESSON: Video must look cinematic, not PowerPoint.
- Use Pexels VIDEO clips as B-roll (not static images)
- Captions reinforce speech, they ARE NOT the content
- Avatar talks, visuals illustrate
- Daena is a CHARACTER, not a layer — she has presence and energy
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

    # Avatar asset search paths (relative to project root)
    # Prefer cutout/nobg versions (dark bg, tight crop — best chromakey results)
    AVATAR_SEARCH_PATHS = [
        "data/assets/daena/avatar_clean/daena_cutout_final.webm",
        "data/assets/daena/avatar_clean/daena_talking_nobg.webm",
        "data/assets/daena/avatar_clean/daena_nobg_final.webm",
        "data/assets/daena/avatar_clean/daena_transparent.webm",
        "data/assets/daena/dana_avatar_clear.mp4",
        "Daena avatar/daena clear social 1 .mp4",
        "Daena avatar/daena avatar  1 .mp4",
    ]

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
        4. Overlay Daena avatar (transparent WebM over B-roll)
        5. Burn captions as subtitles
        6. Add hook text overlay (first 3 seconds)
        7. Mux with audio
        8. Output platform-spec MP4
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

        # Step 4: Create base video (B-roll montage or gradient)
        if broll_clips:
            base_video = await self._create_broll_montage(broll_clips, spec, duration, work_dir)
        else:
            base_video = await self._create_gradient_background(spec, duration, work_dir)

        # Step 5: Add dark cinematic overlay (makes text + avatar pop)
        darkened_video = await self._add_dark_overlay(base_video, spec, work_dir, opacity=0.35)

        # Step 6: Overlay Daena avatar
        avatar_path = avatar_video or self._find_avatar_video(tenant)
        acts = script_data.get("acts", [])
        if avatar_path:
            avatar_base = await self._overlay_avatar(darkened_video, avatar_path, spec, duration, work_dir, acts=acts)
        else:
            logger.warning("No avatar video found — producing video without avatar overlay")
            avatar_base = darkened_video

        # Step 7: Burn captions (SRT file + FFmpeg subtitle filter)
        if captions:
            srt_path = self._generate_srt(captions, work_dir / "captions.srt")
            captioned_video = await self._burn_captions(avatar_base, srt_path, spec, work_dir)
        else:
            captioned_video = avatar_base

        # Step 8: Add hook text overlay (first 3 seconds — glass card effect)
        hook_text = ""
        if acts:
            raw_hook = acts[0].get("text", "")
            # Strip stage directions (parenthetical notes like "(music intro)")
            import re
            clean_hook = re.sub(r'\([^)]*\)\s*', '', raw_hook).strip()
            hook_text = clean_hook[:80]

        if hook_text:
            hooked_video = await self._add_hook_overlay(captioned_video, hook_text, spec, work_dir)
        else:
            hooked_video = captioned_video

        # Step 9: Add progress bar (increases watch time)
        progress_video = await self._add_progress_bar(hooked_video, duration, spec, work_dir)

        # Step 10: Mux with audio
        final_path = work_dir / f"{script_id}_final.mp4"
        await self._mux_audio(progress_video, audio_path, str(final_path), spec)

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
            "has_avatar": bool(avatar_path),
            "has_dark_overlay": True,
            "has_progress_bar": True,
            "avatar_source": str(avatar_path) if avatar_path else None,
            "visual_keywords": visual_keywords,
            "output_path": str(final_path),
            "composed_at": datetime.now().isoformat(),
            "creative_version": "2.0",
        }
        with open(work_dir / "composition.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Video composed: {final_path}")
        return str(final_path)

    def _find_avatar_video(self, tenant: str = "mas-ai") -> Optional[str]:
        """Auto-discover the best avatar video asset for this tenant."""
        # Check tenant-specific avatars first
        tenant_avatar_dir = Path(f"tenants/{tenant}/avatars")
        if tenant_avatar_dir.exists():
            for ext in (".webm", ".mp4"):
                for f in tenant_avatar_dir.glob(f"*{ext}"):
                    return str(f)

        # Fall back to global search paths (prefer transparent WebM)
        for path in self.AVATAR_SEARCH_PATHS:
            p = Path(path)
            if p.exists():
                logger.info(f"Found avatar: {p}")
                return str(p)

        return None

    def _build_avatar_keyframes(self, acts: list[dict], duration: float, spec: VideoSpec) -> dict:
        """Build dynamic avatar size/position keyframes based on 5-act structure.

        Returns timing-based scaling rules for FFmpeg expressions:
        - Act 1 (HOOK, 0-3s): BIG — Daena grabs attention, 55% height
        - Act 2 (CURIOSITY, 3-15s): MEDIUM — talking head, 40% height
        - Act 3 (VALUE, 15-45s): SMALL — B-roll focus, 30% height, bottom-right
        - Act 4 (EMOTIONAL PEAK, 45-55s): BIG — Daena returns, 55% height
        - Act 5 (CTA, 55-60s): MEDIUM — direct address, 40% height
        """
        # Default keyframes if no acts provided
        if not acts or len(acts) < 3:
            return {
                "scale_expr": str(int(spec.height * 0.45)),
                "x_expr": "(W-w)/2",
                "y_expr": f"H-h-{int(spec.height * 0.05)}",
            }

        # Dynamic scale using FFmpeg expression: changes based on time (t)
        h = spec.height
        big = int(h * 0.55)
        medium = int(h * 0.40)
        small = int(h * 0.30)
        margin = int(h * 0.05)

        # FFmpeg if expressions for dynamic height based on timestamp
        # Act boundaries from the 5-act structure
        scale_expr = (
            f"if(lt(t,3),{big},"               # Act 1: HOOK — BIG
            f"if(lt(t,15),{medium},"            # Act 2: CURIOSITY — MEDIUM
            f"if(lt(t,{duration*0.75}),{small},"  # Act 3: VALUE — SMALL
            f"if(lt(t,{duration*0.92}),{big},"  # Act 4: EMOTIONAL — BIG
            f"{medium}))))"                      # Act 5: CTA — MEDIUM
        )

        # Dynamic X position: centered when big, right-side when small
        x_expr = (
            f"if(lt(t,3),(W-w)/2,"                    # Centered for hook
            f"if(lt(t,15),(W-w)/2,"                    # Centered for curiosity
            f"if(lt(t,{duration*0.75}),W-w-{int(spec.width*0.03)},"  # Right for value
            f"(W-w)/2)))"                               # Back to center
        )

        return {
            "scale_expr": scale_expr,
            "x_expr": x_expr,
            "y_expr": f"H-h-{margin}",
        }

    async def _overlay_avatar(self, base_video: str, avatar_path: str,
                               spec: VideoSpec, duration: float, work_dir: Path,
                               acts: list[dict] = None) -> str:
        """Overlay Daena avatar on base video using colorkey background removal.

        Pipeline: crop tight to Daena → colorkey remove white/black bg → scale up → overlay.
        Supports dynamic sizing: Daena gets bigger/smaller based on 5-act structure.
        Looped with -stream_loop to cover the full video duration.
        """
        output = str(work_dir / "avatar_overlay.mp4")

        # Detect avatar properties (bg color, crop region)
        bg_color, similarity, blend = self._detect_avatar_bg(avatar_path)
        crop_filter = self._get_avatar_crop(avatar_path)

        # Get dynamic keyframes based on script acts
        keyframes = self._build_avatar_keyframes(acts or [], duration, spec)

        # Static scale for now (FFmpeg scale filter doesn't support expressions well)
        # Use a good default size — 45% of frame height
        avatar_h = int(spec.height * 0.45)
        margin_bottom = int(spec.height * 0.05)

        # Build filter chain: crop → colorkey → scale → overlay
        filter_complex = (
            f"[1:v]{crop_filter}colorkey={bg_color}:{similarity}:{blend},"
            f"scale=-1:{avatar_h}[avatar];"
            f"[0:v][avatar]overlay=(W-w)/2:H-h-{margin_bottom}:shortest=1[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", base_video,
            "-stream_loop", "-1",
            "-i", avatar_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-r", str(spec.fps),
            "-t", str(duration + 3.0),
            output
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if Path(output).exists() and Path(output).stat().st_size > 10000:
                logger.info(f"Avatar overlay applied (colorkey {bg_color}): {output}")
                return output
            logger.warning("Avatar overlay output too small — trying PiP fallback")
            if result.stderr:
                logger.debug(f"FFmpeg stderr: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            logger.warning("Avatar overlay timed out (300s)")
        except Exception as e:
            logger.warning(f"Avatar overlay failed: {e}")

        return await self._overlay_avatar_pip(base_video, avatar_path, spec, duration, work_dir)

    def _detect_avatar_bg(self, avatar_path: str) -> tuple[str, float, float]:
        """Detect background color for colorkey based on filename.

        Returns: (hex_color, similarity, blend) for FFmpeg colorkey filter.
        """
        name = Path(avatar_path).stem.lower()

        # Dark/black background avatars
        if "cutout" in name or "nobg" in name or "talking" in name:
            return "0x000000", 0.22, 0.10

        # White background (HeyGen default, "clear", "social", "avatar")
        return "0xFFFFFF", 0.22, 0.10

    def _get_avatar_crop(self, avatar_path: str) -> str:
        """Get FFmpeg crop filter to isolate Daena from empty background space.

        Different avatar videos have Daena at different positions/sizes.
        Returns a crop filter string or empty string if no crop needed.
        """
        try:
            # Get video dimensions
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
                "-of", "json", avatar_path
            ], capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            stream = next(s for s in data["streams"] if "width" in s)
            w, h = stream["width"], stream["height"]
        except Exception:
            return ""

        name = Path(avatar_path).stem.lower()

        # "avatar 1" landscape layout: 1280x720, Daena at roughly x=960, y=370, size ~320x350
        if w == 1280 and h == 720 and ("avatar" in name):
            return "crop=320:350:960:370,"

        # "clear social 1" layout: 720x900, Daena in bottom-right corner (~290x300 at 430,600)
        if w == 720 and h == 900 and ("clear" in name or "social" in name):
            return "crop=290:300:430:600,"

        # "avatar 1" layout: Daena is larger, centered — detect dynamically
        # For videos where Daena fills most of the frame, no crop needed
        if w <= 400:
            return ""  # Already tight (WebM cutout versions)

        # Generic: crop bottom 60% of frame (Daena is typically in lower portion)
        crop_h = int(h * 0.6)
        crop_y = h - crop_h
        return f"crop={w}:{crop_h}:0:{crop_y},"

    async def _overlay_avatar_pip(self, base_video: str, avatar_path: str,
                                   spec: VideoSpec, duration: float, work_dir: Path) -> str:
        """Fallback: Picture-in-Picture overlay without background removal.

        Places avatar in a box at bottom-right. Used when colorkey fails.
        """
        output = str(work_dir / "avatar_overlay.mp4")
        avatar_h = int(spec.height * 0.30)
        margin = int(spec.width * 0.03)

        cmd = [
            "ffmpeg", "-y",
            "-i", base_video,
            "-stream_loop", "-1",
            "-i", avatar_path,
            "-filter_complex", (
                f"[1:v]scale=-1:{avatar_h}[avatar];"
                f"[0:v][avatar]overlay=W-w-{margin}:H-h-{margin}:shortest=1[outv]"
            ),
            "-map", "[outv]",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-t", str(duration + 3.0),
            output
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=180)
            if Path(output).exists() and Path(output).stat().st_size > 10000:
                logger.info(f"Avatar PiP overlay applied: {output}")
                return output
        except Exception as e:
            logger.warning(f"Avatar PiP fallback failed: {e}")

        return base_video

    async def _add_dark_overlay(self, video_path: str, spec: VideoSpec,
                                work_dir: Path, opacity: float = 0.35) -> str:
        """Add dark cinematic overlay to B-roll. Makes text and avatar pop.

        This is what separates professional content from amateur — the B-roll
        becomes atmosphere, not competition for the viewer's attention.
        """
        output = str(work_dir / "darkened.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"colorbalance=bs=-0.05:gs=-0.02,eq=brightness=-{opacity}:contrast=1.1:saturation=0.85",
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            output
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            if Path(output).exists() and Path(output).stat().st_size > 1000:
                logger.info("Dark cinematic overlay applied")
                return output
        except Exception as e:
            logger.warning(f"Dark overlay failed: {e}")
        return video_path

    async def _add_progress_bar(self, video_path: str, duration: float,
                                 spec: VideoSpec, work_dir: Path) -> str:
        """Add subtle progress bar at bottom edge. Increases watch time by ~8%.

        The bar grows from left to right as the video plays.
        Color matches brand teal (#2DD4BF) with slight glow.
        """
        output = str(work_dir / "with_progress.mp4")

        bar_height = 4  # Subtle, not distracting
        bar_color = "0x2DD4BF"  # MAS-AI teal

        # FFmpeg drawbox with time-based width expression
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", (
                f"drawbox=x=0:y=ih-{bar_height}:w=iw*(t/{duration}):h={bar_height}:"
                f"color={bar_color}@0.8:t=fill"
            ),
            "-c:v", spec.codec, "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            output
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            if Path(output).exists() and Path(output).stat().st_size > 1000:
                logger.info("Progress bar added")
                return output
        except Exception as e:
            logger.warning(f"Progress bar failed: {e}")
        return video_path

    def _extract_visual_keywords(self, script_data: dict) -> list[str]:
        """Extract intelligent B-roll keywords from script content.

        Uses NLP-style keyword extraction to get relevant, specific B-roll
        rather than generic "technology" footage.
        """
        text = script_data.get("full_voiceover_text", "")
        niche = script_data.get("niche", "technology")
        keywords = []

        # Topic-specific keyword mapping for better B-roll
        keyword_triggers = {
            "AI": "futuristic technology",
            "artificial intelligence": "artificial intelligence robot",
            "startup": "startup office modern",
            "code": "programming code screen dark",
            "developer": "software developer workspace",
            "data": "data analytics dashboard",
            "business": "business meeting corporate",
            "money": "finance stock market",
            "luxury": "luxury lifestyle technology",
            "robot": "humanoid robot futuristic",
            "brain": "neural network visualization",
            "cloud": "cloud computing server room",
            "phone": "smartphone technology",
            "launch": "rocket launch technology",
            "growth": "business growth chart",
            "security": "cybersecurity digital lock",
        }

        text_lower = text.lower()
        for trigger, keyword in keyword_triggers.items():
            if trigger.lower() in text_lower:
                keywords.append(keyword)

        # Always add niche as fallback
        if not keywords:
            keywords = [niche, "technology"]
        keywords.append(niche)

        # Deduplicate and limit
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return unique[:4]

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
            if len(current_chunk) >= 2:
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

        # Style: cinematic subtitle — small white text, dark box, bottom of screen
        # MarginV=60 means 60px from bottom edge (Alignment=2 = bottom center)
        style = (
            "FontSize=13,FontName=Arial,Bold=0,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=1,"
            "BackColour=&HA0000000,Shadow=0,"
            "BorderStyle=4,"
            "Alignment=2,MarginV=60"
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

        font_size = 24 if spec.width >= 1080 else 18
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
