"""
Visual service - selects or generates visuals for videos.
"""
import os
import random
import json
from pathlib import Path
from typing import List, Optional, Dict
from loguru import logger

from app.core.config import settings


class VisualService:
    """Service for selecting and managing video visuals."""
    
    def __init__(self):
        self.stock_path = settings.assets_path / "stock"
    
    def get_stock_videos(
        self,
        niche_name: str,
        tags: Optional[List[str]] = None,
        count: int = 5,
        min_duration: float = 3.0
    ) -> List[Path]:
        """Get stock videos matching niche and tags."""
        
        videos = []
        niche_stock_path = self.stock_path / niche_name
        
        # Check niche-specific folder
        if niche_stock_path.exists():
            videos.extend(self._scan_folder(niche_stock_path, tags))
        
        # Check general stock folder
        general_path = self.stock_path / "general"
        if general_path.exists():
            videos.extend(self._scan_folder(general_path, tags))
        
        # Also check root stock folder
        videos.extend(self._scan_folder(self.stock_path, tags, recursive=False))
        
        # Remove duplicates
        videos = list(set(videos))
        
        # Shuffle and return requested count
        random.shuffle(videos)
        
        logger.info(f"Found {len(videos)} stock videos for niche '{niche_name}'")
        return videos[:count]
    
    def _scan_folder(
        self,
        folder: Path,
        tags: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Path]:
        """Scan folder for video files, optionally filtering by tags."""
        
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        videos = []
        
        if not folder.exists():
            return videos
        
        # Get all video files
        if recursive:
            files = folder.rglob("*")
        else:
            files = folder.glob("*")
        
        for file in files:
            if file.suffix.lower() in video_extensions:
                # If tags specified, check if filename or parent folder matches
                if tags:
                    file_lower = file.stem.lower()
                    parent_lower = file.parent.name.lower()
                    if any(tag.lower() in file_lower or tag.lower() in parent_lower for tag in tags):
                        videos.append(file)
                else:
                    videos.append(file)
        
        return videos
    
    def get_stock_images(
        self,
        niche_name: str,
        tags: Optional[List[str]] = None,
        count: int = 10
    ) -> List[Path]:
        """Get stock images matching niche and tags."""
        
        images = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        
        niche_stock_path = self.stock_path / niche_name
        
        for path in [niche_stock_path, self.stock_path / "general", self.stock_path]:
            if not path.exists():
                continue
            
            for file in path.rglob("*"):
                if file.suffix.lower() in image_extensions:
                    if tags:
                        file_lower = file.stem.lower()
                        if any(tag.lower() in file_lower for tag in tags):
                            images.append(file)
                    else:
                        images.append(file)
        
        random.shuffle(images)
        return list(set(images))[:count]
    
    def get_background_music(self, niche_name: str, mood: str = "neutral") -> Optional[Path]:
        """Get background music track."""
        
        music_path = settings.assets_path / "music"
        
        if not music_path.exists():
            return None
        
        # Check for niche-specific music
        niche_music = music_path / niche_name
        if niche_music.exists():
            tracks = list(niche_music.glob("*.mp3")) + list(niche_music.glob("*.wav"))
            if tracks:
                return random.choice(tracks)
        
        # Check for mood-based music
        mood_music = music_path / mood
        if mood_music.exists():
            tracks = list(mood_music.glob("*.mp3")) + list(mood_music.glob("*.wav"))
            if tracks:
                return random.choice(tracks)
        
        # Fall back to general music
        tracks = list(music_path.glob("*.mp3")) + list(music_path.glob("*.wav"))
        if tracks:
            return random.choice(tracks)
        
        return None
    
    def get_logo(self, niche_name: Optional[str] = None) -> Optional[Path]:
        """Get logo for watermarking."""
        
        logos_path = settings.assets_path / "logos"
        
        if not logos_path.exists():
            return None
        
        # Check for niche-specific logo
        if niche_name:
            niche_logo = logos_path / f"{niche_name}.png"
            if niche_logo.exists():
                return niche_logo
        
        # Fall back to default logo
        default_logo = logos_path / "default.png"
        if default_logo.exists():
            return default_logo
        
        # Try any logo
        logos = list(logos_path.glob("*.png"))
        if logos:
            return logos[0]
        
        return None
    
    def get_font(self, font_name: Optional[str] = None) -> Optional[Path]:
        """Get font file for subtitles."""
        
        fonts_path = settings.assets_path / "fonts"
        
        if not fonts_path.exists():
            return None
        
        if font_name:
            font_file = fonts_path / f"{font_name}.ttf"
            if font_file.exists():
                return font_file
        
        # Fall back to any font
        fonts = list(fonts_path.glob("*.ttf")) + list(fonts_path.glob("*.otf"))
        if fonts:
            return fonts[0]
        
        return None
    
    def create_asset_manifest(self, niche_name: str) -> Dict:
        """Create a manifest of available assets for a niche."""
        
        manifest = {
            "niche": niche_name,
            "stock_videos": len(self.get_stock_videos(niche_name, count=1000)),
            "stock_images": len(self.get_stock_images(niche_name, count=1000)),
            "has_music": self.get_background_music(niche_name) is not None,
            "has_logo": self.get_logo(niche_name) is not None,
            "has_font": self.get_font() is not None,
        }
        
        return manifest


# Placeholder for Stable Diffusion integration
class ImageGenerationService:
    """Placeholder for AI image generation (Stable Diffusion)."""
    
    def __init__(self):
        self.enabled = False  # Set to True when SD is configured
        self.sd_api_url = "http://localhost:7860"  # A1111 API
    
    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1080,
        height: int = 1920
    ) -> Optional[Path]:
        """Generate image using Stable Diffusion."""
        
        if not self.enabled:
            logger.warning("Image generation not enabled")
            return None
        
        # TODO: Implement actual SD API call
        # This is a placeholder for when user configures SD
        
        logger.info(f"Would generate image: {prompt}")
        return None


visual_service = VisualService()
image_generation_service = ImageGenerationService()
