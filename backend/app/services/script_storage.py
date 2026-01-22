"""
Script storage service - saves generated scripts organized by date/niche.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings


class ScriptStorageService:
    """Service for storing and retrieving generated scripts."""
    
    def __init__(self):
        self.base_path = settings.data_path / "scripts"
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_script(
        self,
        job_id: int,
        niche_name: str,
        topic: str,
        script_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save a generated script with metadata.
        
        Directory structure:
        scripts/
          {niche_name}/
            {YYYY-MM-DD}/
              {HH-MM-SS}_{job_id}_{topic_slug}/
                script.json
                script.txt
                metadata.json
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        
        # Create safe topic slug
        topic_slug = self._slugify(topic)[:50]
        
        # Create directory structure
        script_dir = self.base_path / niche_name / date_str / f"{time_str}_{job_id}_{topic_slug}"
        script_dir.mkdir(parents=True, exist_ok=True)
        
        # Save script as JSON
        script_json_path = script_dir / "script.json"
        with open(script_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "job_id": job_id,
                "niche": niche_name,
                "topic": topic,
                "created_at": now.isoformat(),
                "hook": script_data.get("hook", ""),
                "body": script_data.get("body", ""),
                "cta": script_data.get("cta", ""),
                "full_script": script_data.get("full_script", ""),
                "estimated_duration": script_data.get("estimated_duration", 0),
            }, f, indent=2, ensure_ascii=False)
        
        # Save script as plain text (for easy reading)
        script_txt_path = script_dir / "script.txt"
        with open(script_txt_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n")
            f.write(f"# Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Niche: {niche_name}\n")
            f.write(f"# Job ID: {job_id}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("## HOOK\n")
            f.write(script_data.get("hook", "") + "\n\n")
            
            f.write("## BODY\n")
            f.write(script_data.get("body", "") + "\n\n")
            
            f.write("## CALL TO ACTION\n")
            f.write(script_data.get("cta", "") + "\n\n")
            
            f.write("=" * 50 + "\n")
            f.write("## FULL SCRIPT\n\n")
            f.write(script_data.get("full_script", "") + "\n")
        
        # Save metadata
        if metadata:
            metadata_path = script_dir / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump({
                    **metadata,
                    "saved_at": now.isoformat()
                }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Script saved: {script_dir}")
        return script_dir
    
    def _slugify(self, text: str) -> str:
        """Convert text to a safe filename slug."""
        import re
        # Remove special characters
        text = re.sub(r'[^\w\s-]', '', text.lower())
        # Replace spaces with underscores
        text = re.sub(r'[\s]+', '_', text)
        return text
    
    def get_scripts_by_date(self, niche_name: Optional[str] = None, date_str: Optional[str] = None) -> list:
        """Get list of scripts, optionally filtered by niche and date."""
        scripts = []
        
        search_path = self.base_path
        if niche_name:
            search_path = search_path / niche_name
        
        if not search_path.exists():
            return scripts
        
        # Find all script.json files
        for script_json in search_path.rglob("script.json"):
            try:
                with open(script_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Filter by date if specified
                if date_str:
                    script_date = data.get("created_at", "")[:10]
                    if script_date != date_str:
                        continue
                
                scripts.append({
                    "path": str(script_json.parent),
                    "job_id": data.get("job_id"),
                    "niche": data.get("niche"),
                    "topic": data.get("topic"),
                    "created_at": data.get("created_at"),
                    "estimated_duration": data.get("estimated_duration")
                })
            except Exception as e:
                logger.warning(f"Failed to read script: {script_json}: {e}")
        
        # Sort by creation date, newest first
        scripts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return scripts
    
    def get_script(self, script_path: str) -> Optional[Dict]:
        """Get a specific script by path."""
        script_json = Path(script_path) / "script.json"
        
        if not script_json.exists():
            return None
        
        try:
            with open(script_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read script: {e}")
            return None
    
    def get_recent_scripts(self, limit: int = 20, niche_name: Optional[str] = None) -> list:
        """Get most recent scripts."""
        scripts = self.get_scripts_by_date(niche_name=niche_name)
        return scripts[:limit]
    
    def get_scripts_stats(self) -> Dict:
        """Get statistics about stored scripts."""
        stats = {
            "total": 0,
            "by_niche": {},
            "by_date": {}
        }
        
        if not self.base_path.exists():
            return stats
        
        for niche_dir in self.base_path.iterdir():
            if not niche_dir.is_dir():
                continue
            
            niche_name = niche_dir.name
            niche_count = 0
            
            for date_dir in niche_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                date_str = date_dir.name
                script_count = len(list(date_dir.glob("*/script.json")))
                niche_count += script_count
                
                if date_str not in stats["by_date"]:
                    stats["by_date"][date_str] = 0
                stats["by_date"][date_str] += script_count
            
            stats["by_niche"][niche_name] = niche_count
            stats["total"] += niche_count
        
        return stats


script_storage = ScriptStorageService()
