# Root Cause Diagnosis

## Issue: Backend Startup Failure
**Symptom**: `sqlite3.OperationalError: no such column: niches.auto_mode`

## Root Cause
The SQLite database schema was outdated compared to the SQLModel definitions in the code.
The `Niche` model in `backend/app/models/niche.py` has fields like `auto_mode`, `platform`, `account_name`, `posting_schedule` which were missing in the existing `data/content_factory.db` file.

This happens when the code evolves (adding new features/columns) but the database is not migrated. SQLModel's `create_all` only creates *new* tables; it does not modify existing ones.

## Fix Implemented
1.  **Migration System**: Created `backend/app/db/migrations.py` to handle lightweight schema migrations on startup.
2.  **Startup Hook**: Updated `backend/app/db/database.py` to call `run_migrations()` after table creation.
3.  **Logic**: The migration script inspects the `niches` table and adds missing columns (`auto_mode`, `platform`, etc.) if they don't exist.

## Verification
- The backend should now start successfully even with the old database file.
- The "Select Niche" dropdown in the frontend will now populate correctly because the API will no longer fail on database queries.
