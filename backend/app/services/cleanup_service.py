"""
Cleanup Service - Automated retention management for outputs and temp files.

Features:
- Configurable retention periods
- Automatic deletion of old outputs
- Preserves scripts and metadata longer (small size)
- Safe deletion with confirmation option
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from app.core.config import settings


class CleanupService:
    """Service for managing file retention and cleanup."""
    
    def __init__(self):
        self.retention_config = {
            "outputs": {
                "final_videos": 1,      # days to keep final video files
                "render_temp": 0.5,     # days to keep temp render files (12 hours)
                "audio_temp": 0.5,      # days to keep temp audio files
                "scripts": 7,           # days to keep script JSON files
                "metadata": 30,         # days to keep metadata
            },
            "uploads": 1,               # days to keep uploaded files
            "logs": 7,                  # days to keep log files
            "browser_profiles": 30,     # days to keep unused browser profiles
        }
        self._config_file = settings.data_path / "cleanup_config.json"
        self._load_config()
    
    def _load_config(self):
        """Load retention config from disk if exists."""
        if self._config_file.exists():
            try:
                import json
                with open(self._config_file, "r") as f:
                    saved_config = json.load(f)
                # Merge with defaults
                for key, value in saved_config.items():
                    if isinstance(value, dict) and key in self.retention_config:
                        self.retention_config[key].update(value)
                    else:
                        self.retention_config[key] = value
                logger.info("Loaded cleanup config")
            except Exception as e:
                logger.warning(f"Failed to load cleanup config: {e}")
    
    def save_config(self):
        """Save current config to disk."""
        try:
            import json
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w") as f:
                json.dump(self.retention_config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cleanup config: {e}")
    
    def update_retention(self, category: str, days: float):
        """Update retention period for a category."""
        if isinstance(self.retention_config.get(category), dict):
            # For nested configs like "outputs"
            logger.warning(f"Category {category} has sub-categories. Use update_retention_sub() instead.")
            return
        self.retention_config[category] = days
        self.save_config()
    
    def update_retention_sub(self, category: str, sub_category: str, days: float):
        """Update retention period for a sub-category."""
        if category not in self.retention_config:
            self.retention_config[category] = {}
        if isinstance(self.retention_config[category], dict):
            self.retention_config[category][sub_category] = days
            self.save_config()
    
    def _is_expired(self, path: Path, max_age_days: float) -> bool:
        """Check if a file/directory is older than max age."""
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            cutoff = datetime.now() - timedelta(days=max_age_days)
            return mtime < cutoff
        except Exception:
            return False
    
    def _get_size_mb(self, path: Path) -> float:
        """Get size of file or directory in MB."""
        if path.is_file():
            return path.stat().st_size / (1024 * 1024)
        elif path.is_dir():
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            return total / (1024 * 1024)
        return 0
    
    def cleanup_outputs(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up old output files.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Summary of cleanup actions
        """
        outputs_path = settings.outputs_path
        deleted = []
        space_freed_mb = 0
        errors = []
        
        if not outputs_path.exists():
            return {"deleted": 0, "space_freed_mb": 0, "errors": []}
        
        config = self.retention_config.get("outputs", {})
        video_retention = config.get("final_videos", 1)
        temp_retention = config.get("render_temp", 0.5)
        script_retention = config.get("scripts", 7)
        
        for niche_dir in outputs_path.iterdir():
            if not niche_dir.is_dir():
                continue
            
            for date_dir in niche_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                # Check each file type
                for file_path in date_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    
                    try:
                        # Determine retention based on file type
                        ext = file_path.suffix.lower()
                        
                        if ext in [".mp4", ".webm", ".mov"]:
                            max_age = video_retention
                        elif ext in [".wav", ".mp3", ".ogg"]:
                            max_age = temp_retention
                        elif ext == ".json" and "script" in file_path.name.lower():
                            max_age = script_retention
                        elif "temp" in file_path.name.lower() or "_tmp" in file_path.name.lower():
                            max_age = temp_retention
                        else:
                            max_age = video_retention  # Default
                        
                        if self._is_expired(file_path, max_age):
                            size = self._get_size_mb(file_path)
                            
                            if not dry_run:
                                file_path.unlink()
                                logger.info(f"Deleted: {file_path} ({size:.2f} MB)")
                            
                            deleted.append({
                                "path": str(file_path),
                                "size_mb": size,
                                "age_days": (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days if file_path.exists() else "?"
                            })
                            space_freed_mb += size
                            
                    except Exception as e:
                        errors.append({"path": str(file_path), "error": str(e)})
                
                # Clean up empty date directories
                if date_dir.exists() and not any(date_dir.iterdir()):
                    if not dry_run:
                        date_dir.rmdir()
                        logger.info(f"Removed empty directory: {date_dir}")
        
        return {
            "deleted": len(deleted),
            "deleted_files": deleted if dry_run else None,
            "space_freed_mb": round(space_freed_mb, 2),
            "errors": errors,
            "dry_run": dry_run
        }
    
    def cleanup_uploads(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old uploads."""
        uploads_path = settings.uploads_path
        deleted = []
        space_freed_mb = 0
        
        if not uploads_path.exists():
            return {"deleted": 0, "space_freed_mb": 0}
        
        max_age = self.retention_config.get("uploads", 1)
        
        for file_path in uploads_path.iterdir():
            if file_path.is_file() and self._is_expired(file_path, max_age):
                size = self._get_size_mb(file_path)
                
                if not dry_run:
                    file_path.unlink()
                
                deleted.append(str(file_path))
                space_freed_mb += size
        
        return {
            "deleted": len(deleted),
            "space_freed_mb": round(space_freed_mb, 2),
            "dry_run": dry_run
        }
    
    def cleanup_logs(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old log files."""
        logs_path = settings.logs_path
        deleted = []
        space_freed_mb = 0
        
        if not logs_path.exists():
            return {"deleted": 0, "space_freed_mb": 0}
        
        max_age = self.retention_config.get("logs", 7)
        
        for file_path in logs_path.rglob("*.log*"):
            if file_path.is_file() and self._is_expired(file_path, max_age):
                size = self._get_size_mb(file_path)
                
                if not dry_run:
                    file_path.unlink()
                
                deleted.append(str(file_path))
                space_freed_mb += size
        
        return {
            "deleted": len(deleted),
            "space_freed_mb": round(space_freed_mb, 2),
            "dry_run": dry_run
        }
    
    def run_full_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run cleanup on all categories."""
        results = {
            "outputs": self.cleanup_outputs(dry_run),
            "uploads": self.cleanup_uploads(dry_run),
            "logs": self.cleanup_logs(dry_run),
            "total_space_freed_mb": 0,
            "total_files_deleted": 0,
            "run_at": datetime.now().isoformat(),
            "dry_run": dry_run
        }
        
        results["total_space_freed_mb"] = sum(
            r.get("space_freed_mb", 0) for r in [results["outputs"], results["uploads"], results["logs"]]
        )
        results["total_files_deleted"] = sum(
            r.get("deleted", 0) for r in [results["outputs"], results["uploads"], results["logs"]]
        )
        
        if not dry_run:
            logger.info(f"Cleanup complete: {results['total_files_deleted']} files, {results['total_space_freed_mb']} MB freed")
        
        return results
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get current storage usage statistics."""
        stats = {
            "outputs_mb": 0,
            "uploads_mb": 0,
            "logs_mb": 0,
            "niches_mb": 0,
            "total_mb": 0
        }
        
        if settings.outputs_path.exists():
            stats["outputs_mb"] = round(self._get_size_mb(settings.outputs_path), 2)
        
        if settings.uploads_path.exists():
            stats["uploads_mb"] = round(self._get_size_mb(settings.uploads_path), 2)
        
        if settings.logs_path.exists():
            stats["logs_mb"] = round(self._get_size_mb(settings.logs_path), 2)
        
        if settings.niches_path.exists():
            stats["niches_mb"] = round(self._get_size_mb(settings.niches_path), 2)
        
        stats["total_mb"] = sum([
            stats["outputs_mb"],
            stats["uploads_mb"],
            stats["logs_mb"],
            stats["niches_mb"]
        ])
        
        stats["retention_config"] = self.retention_config
        
        return stats


# Global instance
cleanup_service = CleanupService()
