#!/usr/bin/env python3
"""
Database migration script for Content Factory.
Adds new fields to existing tables.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.db.database import engine
from sqlalchemy import text

def migrate_database():
    """Apply database migrations."""

    print("Starting database migration...")

    # Migration 1: Add auto_mode and posts_per_day to niches table
    migrations = [
        """
        ALTER TABLE niches ADD COLUMN auto_mode BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE niches ADD COLUMN posts_per_day INTEGER DEFAULT 2;
        """
    ]

    with engine.connect() as conn:
        for i, migration in enumerate(migrations, 1):
            try:
                print(f"Applying migration {i}: {migration.strip()[:50]}...")
                conn.execute(text(migration))
                conn.commit()
                print(f"Migration {i} applied successfully")
            except Exception as e:
                error_msg = str(e)
                if "duplicate column name" in error_msg.lower():
                    print(f"Migration {i} skipped (column already exists)")
                else:
                    print(f"Migration {i} failed: {error_msg}")
                    # Continue with other migrations

    print("Database migration completed!")

if __name__ == "__main__":
    migrate_database()