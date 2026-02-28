"""
Studio Service - Local media generation orchestrator.
Handles scene asset generation (LTX or fallback) and final Remotion assembly.
"""
import gc
import json
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

import torch
from loguru import logger

from app.core.config import settings
from app.db import get_sync_session
from app.models import Job, JobStatus, Niche
from app.services.ltx_service import ltx_service
from app.services.remotion_service import remotion_service
from app.services.tts_service import tts_service
from app.services.visual_service import visual_service
from app.services.render_service import render_service, RenderConfig


class StudioService:
    """Production studio for audio, scene assets, and branded assembly."""

    def __init__(self):
        self.data_path = settings.data_path
        self.jobs_path = self.data_path / "jobs"

    def unload_gpu(self) -> None:
        """Aggressive VRAM cleanup."""
        logger.info("Cleaning up GPU VRAM...")
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            gc.collect()
            try:
                import requests

                # Hint Ollama to unload hot models between long GPU steps.
                requests.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_fast_model, "keep_alive": 0},
                    timeout=2.0,
                )
                requests.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_reasoning_model, "keep_alive": 0},
                    timeout=2.0,
                )
            except Exception as e:
                logger.warning(f"Could not unload Ollama from VRAM: {e}")
        except Exception as e:
            logger.warning(f"VRAM cleanup encountered a minor issue: {e}")

    async def generate_audio(self, job_id: int) -> Path:
        """Generate XTTS/ElevenLabs narration."""
        with get_sync_session() as session:
            job = session.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            logger.info(f"Generating audio for Job {job.id}...")
            job.status = JobStatus.GENERATING_AUDIO
            session.add(job)
            session.commit()

            job_dir = self.jobs_path / str(job.id)
            job_dir.mkdir(parents=True, exist_ok=True)
            audio_file = job_dir / "voiceover.wav"

            try:
                await tts_service.generate_audio(
                    text=job.full_script or job.topic,
                    output_path=audio_file,
                    provider="xtts",
                    speaker_wav=job.voice_id or settings.xtts_default_speaker_wav,
                )
                if not audio_file.exists() or audio_file.stat().st_size < 1000:
                    raise RuntimeError("Audio file missing or too small")

                job.audio_path = str(audio_file.relative_to(self.data_path))
                session.add(job)
                session.commit()
                self.unload_gpu()
                return audio_file
            except Exception as e:
                logger.error(f"Audio generation failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = f"Audio Gen Error: {e}"
                session.add(job)
                session.commit()
                raise

    def _create_fallback_clip(self, clip_path: Path, duration_seconds: int = 5) -> Path:
        """Create a deterministic fallback clip so pipeline never stalls on missing assets."""
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=#1f2937:s=854x480:d={max(1, duration_seconds)}",
            "-vf",
            "format=yuv420p",
            str(clip_path),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if not clip_path.exists():
            raise RuntimeError(f"Failed to create fallback clip at {clip_path}")
        return clip_path

    async def generate_video_assets(self, job_id: int) -> List[Path]:
        """Generate scene clips with LTX when available; otherwise use stock/fallback clips."""
        from app.core.websockets import manager

        with get_sync_session() as session:
            job = session.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            niche = session.get(Niche, job.niche_id)
            if not niche:
                raise ValueError(f"Niche not found for job {job_id}")

            logger.info(f"Generating video assets for Job {job.id}...")
            try:
                visual_prompts = json.loads(job.visual_cues) if job.visual_cues else []
                if isinstance(visual_prompts, str):
                    visual_prompts = json.loads(visual_prompts)
            except Exception:
                visual_prompts = []

            if not visual_prompts and job.full_script:
                visual_prompts = [line.strip() for line in job.full_script.split("\n") if len(line.strip()) > 20]
            if not visual_prompts:
                visual_prompts = [job.topic]

            scene_count = min(max(len(visual_prompts), 1), 7)
            prompts = visual_prompts[:scene_count]
            assets_dir = self.jobs_path / str(job.id) / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            video_clips: List[Path] = []
            logger.info(f"Planning {scene_count} scenes for asset generation")

            # If LTX is configured but not available, skip LTX attempts and use fallback immediately
            ltx_available = False
            if settings.video_gen_provider == "ltx":
                try:
                    ltx_available = await ltx_service.check_connection()
                except Exception as e:
                    logger.warning(f"LTX connection check failed, using fallback only: {e}")
            if settings.video_gen_provider == "ltx" and not ltx_available:
                logger.info("LTX not available (no models/ComfyUI); using stock/fallback clips for all scenes.")

            for i, prompt in enumerate(prompts):
                clip_path = assets_dir / f"scene_{i}.mp4"
                prompt_str = (prompt or job.topic or "scene") if hasattr(prompt, "strip") else str(prompt or "scene")
                try:
                    asyncio.create_task(
                        manager.broadcast(
                            {
                                "type": "scene_step",
                                "job_id": job_id,
                                "scene_index": i,
                                "total_scenes": scene_count,
                                "status": "started",
                                "prompt": prompt_str[:200] if prompt_str else "",
                            }
                        )
                    )
                except Exception:
                    pass

                if clip_path.exists() and clip_path.stat().st_size > 10_000:
                    video_clips.append(clip_path)
                    try:
                        asyncio.create_task(
                            manager.broadcast(
                                {"type": "scene_step", "job_id": job_id, "scene_index": i, "status": "completed", "progress": int(((i + 1) / scene_count) * 100)}
                            )
                        )
                    except Exception:
                        pass
                    continue

                try:
                    generated = False
                    if settings.video_gen_provider == "ltx" and ltx_available:
                        max_retries = 2
                        platform_format = getattr(job, "platform_format", None) or "9:16"
                        start_path = None
                        if getattr(job, "start_frame_path", None):
                            start_path = (Path(settings.data_path) / job.start_frame_path).resolve()
                            if not start_path.exists():
                                start_path = None
                        end_path = None
                        if getattr(job, "end_frame_path", None):
                            end_path = (Path(settings.data_path) / job.end_frame_path).resolve()
                            if not end_path.exists():
                                end_path = None
                        for attempt in range(max_retries + 1):
                            try:
                                logger.info(
                                    f"LTX scene {i + 1}/{scene_count} attempt {attempt + 1}: {(prompt_str or '')[:80]}"
                                )
                                await ltx_service.generate_video_from_text(
                                    text=prompt_str,
                                    output_path=clip_path,
                                    width=704,
                                    height=1216,
                                    duration_seconds=5,
                                    fps=25,
                                    model_name=getattr(job, "video_model", None),
                                    platform_format=platform_format,
                                    start_frame_path=start_path if attempt == 0 else None,
                                    end_frame_path=end_path if attempt == 0 else None,
                                )
                                if clip_path.exists() and clip_path.stat().st_size > 1000:
                                    generated = True
                                    break
                            except Exception as e:
                                logger.warning(f"LTX attempt {attempt + 1} failed on scene {i}: {e}")
                                self.unload_gpu()
                                if attempt == max_retries:
                                    logger.warning(f"LTX retries exhausted for scene {i}, using fallback.")

                    if not generated:
                        niche_key = (niche.slug or niche.name or "general").replace(" ", "_")
                        try:
                            keywords = visual_service._extract_keywords(prompt_str)
                        except Exception:
                            keywords = []
                        try:
                            stock = visual_service.get_stock_videos(
                                niche_name=niche_key,
                                tags=keywords,
                                count=1,
                            )
                        except Exception as e:
                            logger.warning(f"Stock video lookup failed for scene {i}: {e}")
                            stock = []
                        if stock:
                            video_clips.append(Path(stock[0]) if not isinstance(stock[0], Path) else stock[0])
                        else:
                            video_clips.append(self._create_fallback_clip(clip_path, duration_seconds=5))
                    else:
                        video_clips.append(clip_path)
                except Exception as e:
                    logger.error(f"Scene {i} asset generation failed: {e}", exc_info=True)
                    try:
                        video_clips.append(self._create_fallback_clip(clip_path, duration_seconds=5))
                    except Exception as fallback_err:
                        logger.error(f"Fallback clip failed for scene {i}: {fallback_err}")
                        # Ensure we have at least one clip so pipeline does not get empty list
                        fallback_path = assets_dir / f"scene_{i}_fallback.mp4"
                        try:
                            video_clips.append(self._create_fallback_clip(fallback_path, duration_seconds=5))
                        except Exception:
                            pass

                try:
                    asyncio.create_task(
                        manager.broadcast(
                            {
                                "type": "scene_step",
                                "job_id": job_id,
                                "scene_index": i,
                                "status": "completed",
                                "progress": int(((i + 1) / scene_count) * 100),
                            }
                        )
                    )
                except Exception:
                    pass
                if settings.video_gen_provider == "ltx" and ltx_available:
                    self.unload_gpu()

            # Guarantee non-empty: if something went wrong and we have no clips, create one fallback
            if not video_clips:
                logger.warning("No video clips produced; creating single fallback clip so pipeline can continue.")
                single_fallback = assets_dir / "scene_0_fallback.mp4"
                try:
                    video_clips.append(self._create_fallback_clip(single_fallback, duration_seconds=5))
                except Exception as e:
                    logger.error(f"Final fallback clip failed: {e}")
                    raise RuntimeError("Video asset generation failed: could not create any clips or fallback.") from e

            return video_clips

    async def assemble_video(self, job_id: int, assets: List[Path], audio_path: Path) -> Path:
        """Final assembly using Remotion with branding and audio."""
        from app.core.websockets import manager

        with get_sync_session() as session:
            job = session.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            niche = session.get(Niche, job.niche_id)
            if not niche:
                raise ValueError(f"Niche not found for job {job_id}")

            job.status = JobStatus.RENDERING
            session.add(job)
            session.commit()

            job_dir = self.jobs_path / str(job.id)
            output_file = job_dir / "final_vlog.mp4"

            if not assets:
                logger.warning("No scene assets were produced. Creating one fallback scene.")
                assets = [self._create_fallback_clip(job_dir / "assets" / "scene_fallback.mp4", 5)]

            logo_path = visual_service.get_logo(niche.slug or niche.name)

            asyncio.create_task(
                manager.broadcast(
                    {
                        "type": "job_update",
                        "job_id": job_id,
                        "status": "assembling",
                        "progress": 85,
                    }
                )
            )

            # First try high-end Remotion assembly. If that fails (npx/npm missing, render error, timeout),
            # fall back to pure FFmpeg multi-scene render so the job can still complete.
            try:
                final_path = await remotion_service.render_promo(
                    assets=[str(a) for a in assets],
                    audio_path=str(audio_path),
                    output_path=str(output_file),
                    logo_path=str(logo_path) if logo_path else None,
                )
                job.video_path = str(Path(final_path).relative_to(self.data_path))
                job.updated_at = datetime.utcnow()
                session.add(job)
                session.commit()
                return Path(final_path)
            except Exception as e:
                logger.error(f"Remotion assembly failed, falling back to FFmpeg renderer: {e}")

                try:
                    # Pass absolute paths for scene assets so FFmpeg can read them; only include existing files
                    resolved_assets = [Path(a).resolve() for a in assets]
                    existing = [a for a in resolved_assets if a.exists()]
                    if not existing:
                        logger.warning("No scene asset files found on disk; render will use fallback clips per scene.")
                    scenes = [{"asset_path": str(a)} for a in resolved_assets]
                    audio_resolved = Path(audio_path).resolve() if audio_path else None
                    if audio_resolved and not audio_resolved.exists():
                        logger.warning(f"Audio file not found at {audio_resolved}")
                    # Disable subtitles so the video shows only visuals + audio (no large text overlay)
                    config = RenderConfig(
                        width=settings.default_video_width,
                        height=settings.default_video_height,
                        fps=settings.default_video_fps,
                        audio_path=audio_resolved if (audio_resolved and audio_resolved.exists()) else audio_path,
                        subtitle_path=None,
                        burn_subtitles=False,
                        logo_path=logo_path,
                        output_path=output_file,
                        scenes=scenes,
                    )

                    ffmpeg_final = await render_service.render_video(config)
                    job.video_path = str(Path(ffmpeg_final).relative_to(self.data_path))
                    job.updated_at = datetime.utcnow()
                    session.add(job)
                    session.commit()
                    logger.info(f"FFmpeg fallback assembly complete: {ffmpeg_final}")
                    return Path(ffmpeg_final)
                except Exception as ff_err:
                    logger.error(f"FFmpeg assembly fallback failed: {ff_err}")
                    job.status = JobStatus.FAILED
                    job.error_message = f"Assembly Error: {e}; Fallback Error: {ff_err}"
                    session.add(job)
                    session.commit()
                    raise


studio_service = StudioService()
