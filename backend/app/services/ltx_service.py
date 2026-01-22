"""
LTX Video Generation Service - generates video using LTX (Lightricks) model.
Supports local ComfyUI-LTXVideo API.
"""
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings


class LTXService:
    """Service for generating video using LTX model via ComfyUI API."""
    
    def __init__(self):
        self.api_url = settings.ltx_api_url or "http://127.0.0.1:8188"
        self.enabled = settings.video_gen_provider == "ltx"
    
    async def check_connection(self) -> bool:
        """Check if LTX API is available."""
        if not self.enabled:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/system_stats")
                return response.status_code < 400
        except Exception as e:
            logger.warning(f"LTX API not available: {e}")
            return False
    
    async def generate_video_from_text(
        self,
        text: str,
        prompt: Optional[str] = None,
        output_path: Path,
        width: int = 854,
        height: int = 480,
        duration_seconds: int = 5,
        fps: int = 24
    ) -> Path:
        """
        Generate video from text using LTX.
        
        Args:
            text: Script text to visualize
            prompt: Optional visual prompt (if None, uses text)
            output_path: Where to save the video
            width: Video width (480p recommended for 8GB VRAM)
            height: Video height
            duration_seconds: Clip duration (3-5s recommended for 8GB VRAM)
            fps: Frames per second
        """
        if not self.enabled:
            raise ValueError("LTX provider is not enabled")
        
        if not await self.check_connection():
            raise ConnectionError("LTX API is not available")
        
        # Create a simple ComfyUI workflow for LTX text-to-video
        workflow = self._create_ltx_workflow(
            prompt=prompt or text,
            width=width,
            height=height,
            duration_frames=duration_seconds * fps,
            fps=fps
        )
        
        # Submit workflow to ComfyUI
        prompt_id = await self._queue_prompt(workflow)
        
        # Wait for completion and download
        output_path = await self._wait_and_download(prompt_id, output_path)
        
        return output_path
    
    def _create_ltx_workflow(
        self,
        prompt: str,
        width: int,
        height: int,
        duration_frames: int,
        fps: int
    ) -> Dict[str, Any]:
        """Create a ComfyUI workflow JSON for LTX text-to-video."""
        
        # Basic LTX workflow structure
        # This is a simplified version - actual ComfyUI-LTXVideo nodes may vary
        workflow = {
            "1": {
                "inputs": {
                    "text": prompt,
                    "width": width,
                    "height": height,
                    "num_frames": duration_frames,
                    "fps": fps
                },
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
        prompt: Optional[str] = None,
        output_path: Path,
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
