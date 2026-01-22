"""
Database setup and session management using SQLModel.
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.config import settings


# Sync engine for simple operations
sync_engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False}
)

# Async engine for FastAPI
async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(
    async_database_url,
    echo=settings.debug
)

# Session factories
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(sync_engine)


@contextmanager
def get_sync_session():
    """Get a synchronous database session."""
    session = Session(sync_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_session() -> AsyncSession:
    """Dependency for async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
