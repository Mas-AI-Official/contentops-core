"""
Database migrations utility for SQLite.
Handles automatic schema updates without losing data.
"""
from sqlalchemy import text
from loguru import logger
from app.db import get_sync_session

def run_migrations():
    """Run automatic database migrations."""
    logger.info("Checking for pending database migrations...")
    
    with get_sync_session() as session:
        # 1. Check for 'auto_mode' in 'niches' table
        try:
            result = session.execute(text("PRAGMA table_info(niches)")).fetchall()
            columns = [row[1] for row in result]
            
            if "auto_mode" not in columns:
                logger.info("Migrating: Adding 'auto_mode' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN auto_mode BOOLEAN DEFAULT 0"))
                session.commit()
                
            if "account_id" not in columns:
                logger.info("Migrating: Adding 'account_id' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN account_id INTEGER REFERENCES accounts(id)"))
                session.commit()
                
            if "youtube_account_id" not in columns:
                logger.info("Migrating: Adding 'youtube_account_id' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN youtube_account_id INTEGER REFERENCES accounts(id)"))
                session.commit()

            if "instagram_account_id" not in columns:
                logger.info("Migrating: Adding 'instagram_account_id' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN instagram_account_id INTEGER REFERENCES accounts(id)"))
                session.commit()

            if "tiktok_account_id" not in columns:
                logger.info("Migrating: Adding 'tiktok_account_id' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN tiktok_account_id INTEGER REFERENCES accounts(id)"))
                session.commit()
                
        except Exception as e:
            logger.error(f"Migration failed for 'niches' table: {e}")
            
        # 2. Check for 'credentials_json' in 'accounts' table
        try:
            result = session.execute(text("PRAGMA table_info(accounts)")).fetchall()
            columns = [row[1] for row in result]
            
            if "credentials_json" not in columns:
                logger.info("Migrating: Adding 'credentials_json' column to 'accounts' table")
                session.execute(text("ALTER TABLE accounts ADD COLUMN credentials_json JSON"))
                session.commit()
        except Exception as e:
            logger.error(f"Migration failed for 'accounts' table: {e}")

        # 3. Check for missing columns in 'jobs' table (platform_format, character_description, etc.)
        try:
            result = session.execute(text("PRAGMA table_info(jobs)")).fetchall()
            columns = [row[1] for row in result]
            jobs_additions = [
                ("voice_id", "TEXT"),
                ("voice_name", "TEXT"),
                ("platform_format", "TEXT"),
                ("character_description", "TEXT"),
                ("start_frame_path", "TEXT"),
                ("end_frame_path", "TEXT"),
                ("visual_cues", "TEXT"),
                ("video_model", "TEXT"),
                ("target_duration_seconds", "INTEGER"),
                ("caption", "TEXT"),
            ]
            for col_name, col_type in jobs_additions:
                if col_name not in columns:
                    logger.info("Migrating: Adding '%s' column to 'jobs' table", col_name)
                    session.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}"))
                    session.commit()
        except Exception as e:
            logger.error(f"Migration failed for 'jobs' table: {e}")

        # 4. generation_mode on niches (review_first | auto_publish)
        try:
            result = session.execute(text("PRAGMA table_info(niches)")).fetchall()
            columns = [row[1] for row in result]
            if "generation_mode" not in columns:
                logger.info("Migrating: Adding 'generation_mode' column to 'niches' table")
                session.execute(text("ALTER TABLE niches ADD COLUMN generation_mode TEXT DEFAULT 'review_first'"))
                session.commit()
        except Exception as e:
            logger.error(f"Migration failed for 'niches' generation_mode: {e}")

    logger.info("Database migrations completed")
