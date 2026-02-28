"""
LTX Video Generation Service - generates video using LTX-2 (Lightricks) model.
Supports direct Python API (preferred) and ComfyUI API (fallback).

Phase 2: Mathematical constraints to reduce glitches:
- Dimensions are multiples of 32 (9:16 → 704x1216, 16:9 → 1216x704, 1:1 → 768x768).
- Frame count fixed to 129 (8n+1, ~5s at 25fps).
- steps=25, cfg_scale=3.5 (or 3.0 when using start frame), sampler=euler.
"""
import json
import os
import httpx
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from loguru import logger

from app.core.config import settings

# Phase 2: LTX mathematical boundaries (multiples of 32)
PLATFORM_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    "9:16": (704, 1216),   # TikTok / Shorts
    "16:9": (1216, 704),   # YouTube
    "1:1": (768, 768),     # Instagram
}
LTX_NUM_FRAMES = 129  # 8n+1 for ~5s; MUST be 8n+1
LTX_STEPS = 25
LTX_CFG_SCALE = 3.5
LTX_CFG_SCALE_WITH_START_FRAME = 3.0  # Lower to preserve character consistency
LTX_SAMPLER = "euler"

# Try to import LTX-2 Python package
try:
    from ltx_pipelines import DistilledPipeline, TI2VidOneStagePipeline
    from ltx_core import LTXModel
    LTX_DIRECT_AVAILABLE = True
except ImportError:
    LTX_DIRECT_AVAILABLE = False
    DistilledPipeline = None
    TI2VidOneStagePipeline = None
    LTXModel = None


class LTXService:
    """Service for generating video using LTX-2 model (direct Python or ComfyUI API)."""
    
    def __init__(self):
        self.api_url = settings.ltx_api_url or "http://127.0.0.1:8188"
        self.enabled = settings.video_gen_provider == "ltx"
        self.use_direct = LTX_DIRECT_AVAILABLE
        # Resolve model path: LTX_MODEL_PATH > MODELS_ROOT/ltx > settings.models_path/ltx
        if settings.ltx_model_path:
            self.model_path = Path(settings.ltx_model_path)
        elif os.environ.get("MODELS_ROOT"):
            self.model_path = Path(os.environ["MODELS_ROOT"]) / "ltx"
        else:
            self.model_path = settings.models_path / "ltx"
        self.repo_path = Path(settings.ltx_repo_path) if settings.ltx_repo_path else settings.base_path / "LTX-2"
        self.use_fp8 = settings.ltx_use_fp8
    
    async def check_connection(self) -> bool:
        """Check if LTX is available (direct Python or ComfyUI API)."""
        # When enabled=False (provider=ffmpeg), we still check so UI-selected model can use LTX
        # Check direct Python package first
        if self.use_direct:
            try:
                # Check if model files exist
                model_files = list(self.model_path.glob("*.safetensors"))
                if model_files:
                    logger.info(f"LTX-2 direct mode available with {len(model_files)} model files")
                    return True
                else:
                    logger.warning("LTX-2 package available but no model files found")
            except Exception as e:
                logger.warning(f"LTX-2 direct mode check failed: {e}")
        
        # Fallback to ComfyUI API check
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/system_stats")
                if response.status_code < 400:
                    logger.info("LTX ComfyUI API mode available")
                    return True
        except Exception as e:
            logger.warning(f"LTX ComfyUI API not available: {e}")
        
        return False
    
    def _resolve_dimensions_and_cfg(
        self,
        platform_format: Optional[str],
        width: int,
        height: int,
        start_frame_path: Optional[Path],
    ) -> Tuple[int, int, float]:
        """Resolve (width, height) to LTX-safe multiples of 32 and cfg_scale."""
        if platform_format and platform_format in PLATFORM_DIMENSIONS:
            w, h = PLATFORM_DIMENSIONS[platform_format]
            width, height = w, h
        cfg = LTX_CFG_SCALE_WITH_START_FRAME if (start_frame_path and start_frame_path.exists()) else LTX_CFG_SCALE
        return width, height, cfg

    async def generate_video_from_text(
        self,
        text: str,
        output_path: Path,
        prompt: Optional[str] = None,
        width: int = 854,
        height: int = 480,
        duration_seconds: int = 5,
        fps: int = 24,
        model_name: Optional[str] = None,
        platform_format: Optional[str] = None,
        start_frame_path: Optional[Path] = None,
        end_frame_path: Optional[Path] = None,
    ) -> Path:
        """
        Generate video from text (or image-to-video when start_frame_path is set).
        Phase 2: Enforces LTX dimensions (multiples of 32), num_frames=129, steps=25, cfg_scale, sampler.
        """
        # Allow when provider=ltx OR user selected a model in Generator (so script+model makes real video)
        if not self.enabled and not model_name:
            raise ValueError(
                "LTX provider is not enabled. Set VIDEO_GEN_PROVIDER=ltx in .env, or select a Video Model in Generator."
            )
        if not await self.check_connection():
            raise ConnectionError(
                "LTX is not available. Ensure model files exist in LTX_MODEL_PATH or MODELS_ROOT/ltx, or ComfyUI is running."
            )

        width, height, cfg_scale = self._resolve_dimensions_and_cfg(platform_format, width, height, start_frame_path)
        num_frames = LTX_NUM_FRAMES
        steps = LTX_STEPS
        sampler = LTX_SAMPLER

        if self.use_direct and LTX_DIRECT_AVAILABLE:
            return await self._generate_direct(
                text, prompt, output_path, width, height, duration_seconds, fps,
                model_name=model_name, start_frame_path=start_frame_path, end_frame_path=end_frame_path,
                num_frames=num_frames, steps=steps, cfg_scale=cfg_scale, sampler=sampler,
            )
        return await self._generate_via_comfyui(
            text, prompt, output_path, width, height, duration_seconds, fps,
            num_frames=num_frames, steps=steps, cfg_scale=cfg_scale, sampler=sampler,
        )
    
    async def _generate_direct(
        self,
        text: str,
        prompt: Optional[str],
        output_path: Path,
        width: int,
        height: int,
        duration_seconds: int,
        fps: int,
        model_name: Optional[str] = None,
        start_frame_path: Optional[Path] = None,
        end_frame_path: Optional[Path] = None,
        num_frames: int = LTX_NUM_FRAMES,
        steps: int = LTX_STEPS,
        cfg_scale: float = LTX_CFG_SCALE,
        sampler: str = LTX_SAMPLER,
    ) -> Path:
        """Generate video using LTX-2 Python package directly. Phase 2: fixed num_frames, steps, cfg, sampler."""
        import torch

        logger.info("Using LTX-2 direct Python API...")
        checkpoint_path = None
        model_type = "ltx2"

        if model_name:
            # Use the specified model
            specified_path = self.model_path / model_name
            if specified_path.exists() and specified_path.suffix == ".safetensors":
                checkpoint_path = specified_path
                logger.info(f"Using specified LTX-2 model: {checkpoint_path.name}")
            else:
                # Try to find by partial name match
                matching_files = list(self.model_path.glob(f"*{model_name}*.safetensors"))
                if matching_files:
                    checkpoint_path = matching_files[0]
                    logger.info(f"Using matched LTX-2 model: {checkpoint_path.name}")
                else:
                    logger.warning(f"Specified model '{model_name}' not found, falling back to auto-select")
        
        if not checkpoint_path:
            # Auto-select: prefer LTX-2, then legacy LTX
            # Priority: LTX-2 distilled FP8 > LTX-2 distilled > LTX-2 full > legacy LTX
            
            # Check for LTX-2 models first (recommended)
            ltx2_files = {
                "distilled_fp8": list(self.model_path.glob("ltx-2*distilled*fp8*.safetensors")),
                "distilled": list(self.model_path.glob("ltx-2*distilled*.safetensors")),
                "full": list(self.model_path.glob("ltx-2*.safetensors"))
            }
            
            for key in ["distilled_fp8", "distilled", "full"]:
                if ltx2_files[key]:
                    checkpoint_path = ltx2_files[key][0]
                    logger.info(f"Auto-selected LTX-2 model: {checkpoint_path.name}")
                    model_type = "ltx2"
                    break
        
        # Fallback to legacy LTX models if LTX-2 not found
        if not checkpoint_path:
            legacy_files = {
                "distilled": list(self.model_path.glob("*ltx-video-distilled*.safetensors")),
                "legacy_dir": list((self.model_path / "legacy").glob("*.safetensors")) if (self.model_path / "legacy").exists() else []
            }
            
            if legacy_files["distilled"]:
                checkpoint_path = legacy_files["distilled"][0]
                logger.warning(f"Using legacy LTX model: {checkpoint_path.name} (LTX-2 recommended)")
                model_type = "legacy"
            elif legacy_files["legacy_dir"]:
                checkpoint_path = legacy_files["legacy_dir"][0]
                logger.warning(f"Using legacy LTX model from legacy/ folder: {checkpoint_path.name}")
                model_type = "legacy"
        
        if not checkpoint_path:
            raise FileNotFoundError(
                f"No LTX model found in {self.model_path}\n"
                f"Download LTX-2 models from: https://huggingface.co/Lightricks/ltx-2\n"
                f"Or legacy models from: https://huggingface.co/spaces/Lightricks/ltx-video-distilled"
            )
        
        # Determine pipeline type based on model
        use_distilled = "distilled" in checkpoint_path.name.lower()
        is_ltx2 = model_type == "ltx2"
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._run_ltx_inference,
            checkpoint_path,
            prompt or text,
            output_path,
            width,
            height,
            num_frames,
            fps,
            use_distilled,
            is_ltx2,
            start_frame_path,
            steps,
            cfg_scale,
            sampler,
        )
        return result

    def _run_ltx_inference(
        self,
        checkpoint_path: Path,
        prompt: str,
        output_path: Path,
        width: int,
        height: int,
        num_frames: int,
        fps: int,
        use_distilled: bool,
        is_ltx2: bool = True,
        start_frame_path: Optional[Path] = None,
        steps: int = LTX_STEPS,
        cfg_scale: float = LTX_CFG_SCALE,
        sampler: str = LTX_SAMPLER,
    ) -> Path:
        """Run LTX inference synchronously. Phase 2: num_frames=129, steps=25, cfg_scale, sampler."""
        import torch

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if is_ltx2:
                logger.info(f"Loading LTX-2 model on {device}...")
                
                # Use DistilledPipeline for speed (8GB VRAM) - LTX-2 only
                if use_distilled and DistilledPipeline:
                    pipeline = DistilledPipeline.from_pretrained(
                        str(checkpoint_path.parent),
                        checkpoint_name=checkpoint_path.name,
                        device=device,
                        enable_fp8=self.use_fp8  # FP8 for 8GB VRAM
                    )
                else:
                    # Fallback to one-stage pipeline
                    pipeline = TI2VidOneStagePipeline.from_pretrained(
                        str(checkpoint_path.parent),
                        checkpoint_name=checkpoint_path.name,
                        device=device,
                        enable_fp8=self.use_fp8
                    )
            else:
                # Legacy LTX model (older format, may need different loading)
                logger.warning(f"Loading legacy LTX model on {device}...")
                logger.warning("Legacy LTX has limited features. Consider upgrading to LTX-2.")
                
                # Legacy models may need ComfyUI API instead
                # For now, try to use one-stage pipeline if available
                if TI2VidOneStagePipeline:
                    try:
                        pipeline = TI2VidOneStagePipeline.from_pretrained(
                            str(checkpoint_path.parent),
                            checkpoint_name=checkpoint_path.name,
                            device=device
                        )
                    except Exception as e:
                        logger.error(f"Legacy LTX model incompatible with LTX-2 pipeline: {e}")
                        raise ValueError(
                            "Legacy LTX models require ComfyUI API. "
                            "Set LTX_API_URL in backend/.env and use ComfyUI mode."
                        )
                else:
                    raise ValueError("LTX-2 package not installed. Legacy models require ComfyUI API.")
            
            logger.info(f"Generating {num_frames} frames (steps={steps}, cfg_scale={cfg_scale}, sampler={sampler})...")
            call_kw: Dict[str, Any] = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_frames": num_frames,
                "fps": fps,
                "enable_fp8": True,
            }
            try:
                for key, val in [("steps", steps), ("cfg_scale", cfg_scale), ("sampler", sampler)]:
                    call_kw[key] = val
                output = pipeline(**call_kw)
            except TypeError:
                call_kw.pop("steps", None)
                call_kw.pop("cfg_scale", None)
                call_kw.pop("sampler", None)
                output = pipeline(**call_kw)
            
            # Save video
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # LTX-2 pipeline outputs vary by pipeline type
            # DistilledPipeline and TI2VidOneStagePipeline typically return video tensors
            # Convert to video file
            try:
                # Try pipeline's built-in save method
                if hasattr(output, 'save'):
                    output.save(str(output_path))
                elif hasattr(pipeline, 'save_video'):
                    pipeline.save_video(output, str(output_path), fps=fps)
                else:
                    # Manual conversion: tensor/array to video
                    import torch
                    import numpy as np
                    from PIL import Image
                    import imageio
                    
                    # Convert tensor to numpy if needed
                    if isinstance(output, torch.Tensor):
                        frames = output.cpu().numpy()
                    elif isinstance(output, np.ndarray):
                        frames = output
                    else:
                        frames = [output] if not isinstance(output, list) else output
                    
                    # Normalize to 0-255 uint8
                    if frames.dtype != np.uint8:
                        frames = (frames * 255).astype(np.uint8)
                    
                    # Save as video
                    imageio.mimwrite(str(output_path), frames, fps=fps, codec='libx264')
                    
            except Exception as save_error:
                logger.error(f"Failed to save LTX-2 video: {save_error}")
                raise
            
            logger.info(f"LTX-2 video generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"LTX-2 direct inference failed: {e}")
            raise
    
    async def _generate_via_comfyui(
        self,
        text: str,
        prompt: Optional[str],
        output_path: Path,
        width: int,
        height: int,
        duration_seconds: int,
        fps: int,
        num_frames: int = LTX_NUM_FRAMES,
        steps: int = LTX_STEPS,
        cfg_scale: float = LTX_CFG_SCALE,
        sampler: str = LTX_SAMPLER,
    ) -> Path:
        """Generate video via ComfyUI API (fallback). Phase 2: use num_frames=129."""
        logger.info("Using LTX ComfyUI API mode...")
        workflow = self._create_ltx_workflow(
            prompt=prompt or text,
            width=width,
            height=height,
            duration_frames=num_frames,
            fps=fps,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler=sampler,
        )
        
        prompt_id = await self._queue_prompt(workflow)
        output_path = await self._wait_and_download(prompt_id, output_path)
        
        return output_path
    
    def _create_ltx_workflow(
        self,
        prompt: str,
        width: int,
        height: int,
        duration_frames: int,
        fps: int,
        steps: int = LTX_STEPS,
        cfg_scale: float = LTX_CFG_SCALE,
        sampler: str = LTX_SAMPLER,
    ) -> Dict[str, Any]:
        """Create a ComfyUI workflow JSON for LTX text-to-video. Phase 2: steps=25, cfg_scale, sampler=euler."""
        inputs: Dict[str, Any] = {
            "text": prompt,
            "width": width,
            "height": height,
            "num_frames": duration_frames,
            "fps": fps,
        }
        if steps is not None:
            inputs["steps"] = steps
        if cfg_scale is not None:
            inputs["cfg_scale"] = cfg_scale
        if sampler:
            inputs["sampler"] = sampler
        workflow = {
            "1": {
                "inputs": inputs,
                "class_type": "LTXTextToVideo",
                "_meta": {"title": "LTX Text to Video"}
            },
            "2": {
                "inputs": {
                    "filename_prefix": "ltx_output",
                    "images": ["1", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Video"}
            }
        }
        
        return workflow
    
    async def _queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Queue a prompt in ComfyUI and return prompt_id."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/prompt",
                    json={"prompt": workflow}
                )
                response.raise_for_status()
                data = response.json()
                prompt_id = data.get("prompt_id")
                
                if not prompt_id:
                    raise ValueError("No prompt_id returned from ComfyUI")
                
                logger.info(f"LTX workflow queued: {prompt_id}")
                return prompt_id
                
        except Exception as e:
            logger.error(f"Failed to queue LTX prompt: {e}")
            raise
    
    async def _wait_and_download(self, prompt_id: str, output_path: Path) -> Path:
        """Wait for workflow completion and download the result."""
        import asyncio
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Poll for completion
        max_wait = 600  # 10 minutes
        check_interval = 5  # seconds
        elapsed = 0
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while elapsed < max_wait:
                    # Check queue status
                    queue_response = await client.get(f"{self.api_url}/queue")
                    queue_data = queue_response.json()
                    
                    # Check if completed
                    history_response = await client.get(f"{self.api_url}/history/{prompt_id}")
                    if history_response.status_code == 200:
                        history_data = history_response.json()
                        
                        # Find output images/videos
                        if prompt_id in history_data:
                            outputs = history_data[prompt_id].get("outputs", {})
                            
                            # Download the video file
                            for node_id, node_output in outputs.items():
                                if "videos" in node_output:
                                    video_url = node_output["videos"][0]
                                    file_url = f"{self.api_url}/view?filename={video_url}"
                                    
                                    # Download
                                    file_response = await client.get(file_url)
                                    file_response.raise_for_status()
                                    
                                    with open(output_path, "wb") as f:
                                        f.write(file_response.content)
                                    
                                    logger.info(f"LTX video downloaded: {output_path}")
                                    return output_path
                    
                    await asyncio.sleep(check_interval)
                    elapsed += check_interval
                
                raise TimeoutError("LTX generation timed out")
                
        except Exception as e:
            logger.error(f"Failed to download LTX video: {e}")
            raise
    
    async def generate_video_from_image(
        self,
        image_path: Path,
        output_path: Path,
        prompt: Optional[str] = None,
        width: int = 854,
        height: int = 480,
        duration_seconds: int = 5
    ) -> Path:
        """Generate video from an image using LTX image-to-video."""
        if not self.enabled:
            raise ValueError("LTX provider is not enabled")
        
        if not await self.check_connection():
            raise ConnectionError("LTX API is not available")
        
        # Upload image first
        image_url = await self._upload_image(image_path)
        
        # Create image-to-video workflow
        workflow = self._create_ltx_img2vid_workflow(
            image_url=image_url,
            prompt=prompt,
            width=width,
            height=height,
            duration_frames=duration_seconds * 24
        )
        
        prompt_id = await self._queue_prompt(workflow)
        output_path = await self._wait_and_download(prompt_id, output_path)
        
        return output_path
    
    async def _upload_image(self, image_path: Path) -> str:
        """Upload image to ComfyUI and return URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(image_path, "rb") as f:
                    files = {"image": f}
                    response = await client.post(
                        f"{self.api_url}/upload/image",
                        files=files
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("name") or image_path.name
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise
    
    def _create_ltx_img2vid_workflow(
        self,
        image_url: str,
        prompt: Optional[str],
        width: int,
        height: int,
        duration_frames: int
    ) -> Dict[str, Any]:
        """Create ComfyUI workflow for LTX image-to-video."""
        workflow = {
            "1": {
                "inputs": {
                    "image": image_url,
                    "text": prompt or "",
                    "width": width,
                    "height": height,
                    "num_frames": duration_frames
                },
                "class_type": "LTXImageToVideo",
                "_meta": {"title": "LTX Image to Video"}
            },
            "2": {
                "inputs": {
                    "filename_prefix": "ltx_img2vid",
                    "images": ["1", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Video"}
            }
        }
        return workflow


ltx_service = LTXService()
