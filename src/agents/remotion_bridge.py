"""
Remotion Bridge — Connects Python pipeline to Remotion React video rendering.

Handles:
1. Generating input props (JSON) for Remotion compositions
2. Triggering Remotion CLI render
3. Managing lifestyle scene timing based on 5-act structure
4. Selecting the right Daena images per mood/act

Daena's lifestyle appearances follow a "less is more" philosophy:
- She appears BRIEFLY (2-3 seconds per appearance)
- She enters with natural motion (slide in, scale up)
- She exits gracefully (fade out, slide down)
- Her lifestyle B-roll (penthouse, boardroom) plays WITHOUT her avatar
  to establish context, then she steps in to deliver a key point
"""
import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("contentops.remotion_bridge")


@dataclass
class DaenaAppearance:
    """A single moment when Daena appears in the video."""
    start_sec: float          # When she enters
    duration_sec: float       # How long she's visible
    image: str                # Which PNG to use
    size: str                 # "large" (55%), "medium" (40%), "small" (30%)
    position: str             # "center", "right", "left"
    entrance: str             # "slide_right", "fade_in", "scale_up"
    exit_anim: str            # "fade_out", "slide_down", "scale_down"
    speech_text: str = ""     # What she's "saying" during this appearance
    mood: str = "confident"   # Matches image selection


@dataclass
class LifestyleScene:
    """A lifestyle B-roll scene (penthouse, boardroom, etc)."""
    image: str                # Source PNG
    start_sec: float
    duration_sec: float
    ken_burns: str = "zoom_in"  # "zoom_in", "zoom_out", "pan_left", "pan_right"
    parallax_depth: float = 1.15  # Zoom factor for 3D parallax
    overlay_opacity: float = 0.3  # Dark overlay strength


@dataclass
class RemotionProps:
    """Full props object passed to Remotion composition."""
    composition_id: str = "ContentVideo"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    duration_sec: float = 60
    audio_src: str = ""
    script_id: str = ""
    platform: str = "tiktok"

    # Content layers
    lifestyle_scenes: list = field(default_factory=list)
    daena_appearances: list = field(default_factory=list)
    captions: list = field(default_factory=list)
    hook_text: str = ""
    cta_text: str = ""

    # Style
    brand_primary: str = "#00c8ff"
    brand_accent: str = "#D4A843"
    brand_teal: str = "#2DD4BF"
    subtitle_font: str = "Arial"
    subtitle_size: int = 13
    progress_bar: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class RemotionBridge:
    """Orchestrates Remotion rendering with act-timed Daena appearances."""

    # Daena lifestyle image catalog — organized by mood/setting
    LIFESTYLE_CATALOG = {
        "confident": [
            "data/assets/daena/casual/penthouse_standing_confident.png",
            "data/assets/daena/casual/penthouse_standing_front_smile.png",
            "data/assets/daena/casual/penthouse_standing_hand_pocket.png",
        ],
        "thoughtful": [
            "data/assets/daena/casual/penthouse_sitting_window.png",
            "data/assets/daena/casual/penthouse_standing_back.png",
            "data/assets/daena/casual/penthouse_back_livingroom.png",
        ],
        "professional": [
            "data/assets/daena/tech/tech_standing_blazer.png",
            "data/assets/daena/tech/tech_sitting_thoughtful.png",
        ],
        "establishing": [
            "data/assets/daena/casual/penthouse_back_full_room.png",
            "data/assets/daena/casual/penthouse_back_livingroom.png",
        ],
    }

    def __init__(self, remotion_dir: str = "src/video/remotion"):
        self.remotion_dir = Path(remotion_dir)
        self.props_dir = Path("data/remotion_props")
        self.props_dir.mkdir(parents=True, exist_ok=True)

    def plan_appearances(self, script_data: dict, duration: float) -> list[DaenaAppearance]:
        """Plan when Daena appears based on the 5-act structure.

        She appears briefly and purposefully — like a real person who
        walks into frame, makes a point, and steps back.

        Act 1 (HOOK):      She enters confidently — "grab attention" moment
        Act 2 (CURIOSITY):  She stays small in corner, lets topic build
        Act 3 (VALUE):      She DISAPPEARS — B-roll delivers the proof
        Act 4 (PEAK):       She returns LARGE — emotional connection moment
        Act 5 (CTA):        She's centered, looking at camera, CTA delivery
        """
        acts = script_data.get("acts", [])

        # Default timing if acts don't have explicit times
        act_boundaries = [0, 3, 15, duration * 0.75, duration * 0.92, duration]
        if len(acts) >= 5 and all("duration_estimate" in a for a in acts):
            # Try to parse act durations
            pass  # Use defaults for now

        appearances = []
        available_images = self._get_available_images()

        if not available_images:
            return appearances

        # Act 1: HOOK — Daena enters confidently (2s appearance)
        hook_img = self._select_image("confident", available_images)
        if hook_img:
            appearances.append(DaenaAppearance(
                start_sec=0.5,
                duration_sec=2.5,
                image=hook_img,
                size="large",
                position="center",
                entrance="scale_up",
                exit_anim="fade_out",
                speech_text=acts[0].get("text", "")[:50] if acts else "",
                mood="confident",
            ))

        # Act 2: CURIOSITY — Small presence (3s, then exits)
        curiosity_img = self._select_image("thoughtful", available_images)
        if curiosity_img:
            appearances.append(DaenaAppearance(
                start_sec=5.0,
                duration_sec=3.0,
                image=curiosity_img,
                size="small",
                position="right",
                entrance="slide_right",
                exit_anim="slide_down",
                mood="thoughtful",
            ))

        # Act 3: VALUE — NO Daena. B-roll is the star.

        # Act 4: EMOTIONAL PEAK — Daena returns LARGE
        peak_start = act_boundaries[3]
        peak_img = self._select_image("confident", available_images)
        if peak_img:
            appearances.append(DaenaAppearance(
                start_sec=peak_start,
                duration_sec=4.0,
                image=peak_img,
                size="large",
                position="center",
                entrance="fade_in",
                exit_anim="fade_out",
                speech_text=acts[3].get("text", "")[:50] if len(acts) > 3 else "",
                mood="confident",
            ))

        # Act 5: CTA — Daena centered, direct to camera
        cta_start = act_boundaries[4]
        cta_img = self._select_image("confident", available_images)
        if cta_img:
            appearances.append(DaenaAppearance(
                start_sec=cta_start,
                duration_sec=duration - cta_start,
                image=cta_img,
                size="medium",
                position="center",
                entrance="scale_up",
                exit_anim="fade_out",
                mood="confident",
            ))

        return appearances

    def plan_lifestyle_scenes(self, duration: float) -> list[LifestyleScene]:
        """Plan lifestyle B-roll scenes throughout the video.

        These are Daena's penthouse/office environments that play as
        background even when she's not "on screen" as an avatar.
        """
        available = self._get_available_images()
        establishing = [p for p in available if "back" in p or "room" in p or "window" in p]
        if not establishing:
            establishing = available[:2]

        scenes = []
        # Opening: establishing shot of penthouse (first 6 seconds)
        if establishing:
            scenes.append(LifestyleScene(
                image=establishing[0],
                start_sec=0,
                duration_sec=6,
                ken_burns="zoom_in",
                parallax_depth=1.12,
                overlay_opacity=0.25,
            ))

        # Mid-video: different angle (between Acts 2-3)
        if len(establishing) > 1:
            scenes.append(LifestyleScene(
                image=establishing[1],
                start_sec=12,
                duration_sec=5,
                ken_burns="pan_left",
                parallax_depth=1.08,
                overlay_opacity=0.3,
            ))

        return scenes

    def generate_props(self, script_data: dict, audio_path: str,
                       duration: float, platform: str = "tiktok") -> str:
        """Generate Remotion input props JSON for a content video."""
        acts = script_data.get("acts", [])

        # Plan all appearances and scenes
        appearances = self.plan_appearances(script_data, duration)
        scenes = self.plan_lifestyle_scenes(duration)

        # Build captions (simplified — full captions come from faster-whisper)
        hook_text = ""
        cta_text = ""
        if acts:
            import re
            raw_hook = acts[0].get("text", "") if isinstance(acts[0], dict) else str(acts[0])
            hook_text = re.sub(r'\([^)]*\)\s*', '', raw_hook).strip()[:80]
        if len(acts) >= 5:
            raw_cta = acts[-1].get("text", "") if isinstance(acts[-1], dict) else str(acts[-1])
            cta_text = raw_cta[:80]

        # Determine spec from platform
        specs = {
            "tiktok": (1080, 1920),
            "instagram_reel": (1080, 1920),
            "youtube_short": (1080, 1920),
            "youtube": (1920, 1080),
            "linkedin": (1920, 1080),
        }
        w, h = specs.get(platform, (1080, 1920))

        props = RemotionProps(
            width=w,
            height=h,
            duration_sec=duration,
            audio_src=audio_path,
            script_id=script_data.get("script_id", ""),
            platform=platform,
            lifestyle_scenes=[asdict(s) for s in scenes],
            daena_appearances=[asdict(a) for a in appearances],
            hook_text=hook_text,
            cta_text=cta_text,
        )

        # Save props file
        props_path = self.props_dir / f"{props.script_id}_props.json"
        with open(props_path, "w") as f:
            f.write(props.to_json())

        logger.info(f"Remotion props generated: {props_path}")
        logger.info(f"  Appearances: {len(appearances)}, Scenes: {len(scenes)}")
        return str(props_path)

    def render(self, props_path: str, output_path: str) -> Optional[str]:
        """Render video using Remotion CLI.

        Falls back to FFmpeg pipeline if Remotion is not installed or fails.
        """
        if not self._is_remotion_available():
            logger.warning("Remotion not available — using FFmpeg fallback")
            return None

        try:
            cmd = [
                "npx", "remotion", "render",
                str(self.remotion_dir / "src" / "index.tsx"),
                "ContentVideo",
                output_path,
                "--props", props_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if Path(output_path).exists():
                logger.info(f"Remotion render complete: {output_path}")
                return output_path
            logger.warning(f"Remotion render failed: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"Remotion render error: {e}")

        return None

    def _is_remotion_available(self) -> bool:
        """Check if Remotion CLI is installed and the project is set up."""
        try:
            result = subprocess.run(
                ["npx", "remotion", "--version"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_available_images(self) -> list[str]:
        """Get all available Daena lifestyle images."""
        images = []
        for mood, paths in self.LIFESTYLE_CATALOG.items():
            for p in paths:
                if Path(p).exists():
                    images.append(p)
        return images

    def _select_image(self, mood: str, available: list[str]) -> Optional[str]:
        """Select a Daena image matching the requested mood."""
        mood_images = self.LIFESTYLE_CATALOG.get(mood, [])
        for img in mood_images:
            if img in available:
                return img
        # Fallback: any available image
        return available[0] if available else None
