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
            
    logger.info("Database migrations completed")
