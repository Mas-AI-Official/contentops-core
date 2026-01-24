"""
Niche Synchronization Service
Scans data/niches/*/config.json and syncs with database
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

from app.core.config import settings
from app.db import get_sync_session
from app.models import Niche


class NicheSyncService:
    """Service for synchronizing niches between disk and database."""

    @staticmethod
    def scan_niche_configs() -> List[Dict[str, Any]]:
        """Scan all niche config.json files and return their data."""
        niche_configs = []

        if not settings.niches_path.exists():
            logger.warning(f"Niches path does not exist: {settings.niches_path}")
            return niche_configs

        for niche_dir in settings.niches_path.iterdir():
            if not niche_dir.is_dir():
                continue

            config_file = niche_dir / "config.json"
            if not config_file.exists():
                logger.debug(f"No config.json found in {niche_dir}")
                continue

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Validate required fields
                if not all(key in config_data for key in ['name', 'slug']):
                    logger.warning(f"Invalid config in {config_file}: missing required fields")
                    continue

                config_data['_config_path'] = config_file
                config_data['_niche_dir'] = niche_dir
                niche_configs.append(config_data)

            except Exception as e:
                logger.error(f"Failed to read config from {config_file}: {e}")

        return niche_configs

    @staticmethod
    def sync_niches_to_db():
        """Sync niche configs from disk to database."""
        logger.info("Starting niche sync from disk to database...")

        niche_configs = NicheSyncService.scan_niche_configs()
        if not niche_configs:
            logger.info("No niche configs found on disk")
            return

        with get_sync_session() as session:
            synced_count = 0
            updated_count = 0

            # Fields to sync from config to DB
            fields_to_sync = [
                'description', 'style', 'platform', 'account_name', 
                'account_id', 'youtube_account_id', 'instagram_account_id', 'tiktok_account_id',
                'post_to_youtube', 'post_to_instagram', 'post_to_tiktok',
                'posts_per_day', 'auto_mode', 'posting_schedule',
                'prompt_hook', 'prompt_body', 'prompt_cta', 'hashtags',
                'min_duration_seconds', 'max_duration_seconds',
                'target_audience', 'content_type',
                'llm_model', 'llm_temperature', 'tts_provider',
                'voice_id', 'voice_name', 'whisper_model', 'whisper_device', 'style_preset'
            ]

            for config_data in niche_configs:
                try:
                    slug = config_data['slug']
                    name = config_data['name']

                    # Check if niche exists in DB
                    existing_niche = session.query(Niche).filter(Niche.slug == slug).first()

                    if existing_niche:
                        # Update existing niche with config data
                        update_data = {}
                        for field in fields_to_sync:
                            if field in config_data:
                                # Handle list/dict comparisons carefully if needed, but direct equality works for JSON types usually
                                if getattr(existing_niche, field) != config_data[field]:
                                    update_data[field] = config_data[field]

                        if update_data:
                            for key, value in update_data.items():
                                setattr(existing_niche, key, value)
                            session.commit()
                            updated_count += 1
                            logger.debug(f"Updated niche: {name}")

                    else:
                        # Create new niche from config
                        niche_data = {
                            'name': name,
                            'slug': slug,
                        }
                        
                        # Populate fields from config or defaults
                        for field in fields_to_sync:
                            if field in config_data:
                                niche_data[field] = config_data[field]
                        
                        # Ensure required defaults if missing in config
                        if 'style' not in niche_data: niche_data['style'] = 'narrator_broll'
                        if 'max_duration_seconds' not in niche_data: niche_data['max_duration_seconds'] = 60
                        if 'content_type' not in niche_data: niche_data['content_type'] = 'educational'

                        new_niche = Niche(**niche_data)
                        session.add(new_niche)
                        session.commit()
                        session.refresh(new_niche)

                        synced_count += 1
                        logger.info(f"Synced new niche from disk: {name}")

                except Exception as e:
                    logger.error(f"Failed to sync niche {config_data.get('name', 'unknown')}: {e}")
                    session.rollback()

            logger.info(f"Niche sync complete: {synced_count} new, {updated_count} updated")

    @staticmethod
    def sync_niche_to_disk(niche: Niche):
        """Sync a single niche from database to disk."""
        try:
            # Create niche directory
            niche_dir = settings.niches_path / niche.slug
            niche_dir.mkdir(parents=True, exist_ok=True)

            # Create/update config.json
            config_file = niche_dir / "config.json"
            config_data = {
                "name": niche.name,
                "slug": niche.slug,
                "description": niche.description or "",
                "style": niche.style,
                "platform": niche.platform,
                "account_name": niche.account_name,
                "account_id": niche.account_id,
                "youtube_account_id": niche.youtube_account_id,
                "instagram_account_id": niche.instagram_account_id,
                "tiktok_account_id": niche.tiktok_account_id,
                "post_to_youtube": niche.post_to_youtube,
                "post_to_instagram": niche.post_to_instagram,
                "post_to_tiktok": niche.post_to_tiktok,
                "posts_per_day": niche.posts_per_day,
                "auto_mode": niche.auto_mode,
                "posting_schedule": niche.posting_schedule,
                "prompt_hook": niche.prompt_hook,
                "prompt_body": niche.prompt_body,
                "prompt_cta": niche.prompt_cta,
                "hashtags": niche.hashtags or [],
                "min_duration_seconds": niche.min_duration_seconds,
                "max_duration_seconds": niche.max_duration_seconds,
                "target_audience": niche.target_audience or "",
                "content_type": niche.content_type or "educational",
                
                # AI Settings
                "llm_model": niche.llm_model,
                "llm_temperature": niche.llm_temperature,
                "tts_provider": niche.tts_provider,
                "voice_id": niche.voice_id,
                "voice_name": niche.voice_name,
                "whisper_model": niche.whisper_model,
                "whisper_device": niche.whisper_device,
                "style_preset": niche.style_preset,
                
                "created_at": niche.created_at.isoformat() if niche.created_at else None,
                "updated_at": niche.updated_at.isoformat() if niche.updated_at else None
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            # Ensure other required files exist
            topics_file = niche_dir / "topics.json"
            if not topics_file.exists():
                topics_data = {"topics": [], "used": [], "auto_sources": []}
                with open(topics_file, 'w', encoding='utf-8') as f:
                    json.dump(topics_data, f, indent=2, ensure_ascii=False)

            feeds_file = niche_dir / "feeds.json"
            if not feeds_file.exists():
                feeds_data = {"feeds": []}
                with open(feeds_file, 'w', encoding='utf-8') as f:
                    json.dump(feeds_data, f, indent=2, ensure_ascii=False)

            # Create assets subdirectory
            assets_dir = niche_dir / "assets"
            assets_dir.mkdir(exist_ok=True)

            logger.debug(f"Synced niche to disk: {niche.name}")

        except Exception as e:
            logger.error(f"Failed to sync niche {niche.name} to disk: {e}")

    @staticmethod
    def validate_niche_structure(niche_slug: str) -> Dict[str, bool]:
        """Validate that a niche has all required files and directories."""
        niche_dir = settings.niches_path / niche_slug
        validation = {
            'directory_exists': niche_dir.exists(),
            'config_exists': False,
            'topics_exists': False,
            'feeds_exists': False,
            'assets_exists': False
        }

        if validation['directory_exists']:
            validation.update({
                'config_exists': (niche_dir / "config.json").exists(),
                'topics_exists': (niche_dir / "topics.json").exists(),
                'feeds_exists': (niche_dir / "feeds.json").exists(),
                'assets_exists': (niche_dir / "assets").exists()
            })

        return validation


# Global instance
niche_sync_service = NicheSyncService()