"""
Content Factory - Main FastAPI Application

A local-first content generation system for creating and publishing
short-form vertical videos across multiple platforms.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys

from app.core.config import settings
from app.db import create_db_and_tables
from app.api import api_router
from app.workers import job_worker


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    settings.logs_path / "content_factory.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Content Factory...")
    
    # Create database tables
    create_db_and_tables()
    logger.info("Database initialized")
    
    # Ensure directories exist
    for path in [
        settings.data_path,
        settings.assets_path,
        settings.niches_path,
        settings.outputs_path,
        settings.logs_path,
        settings.uploads_path,
        settings.assets_path / "music",
        settings.assets_path / "logos",
        settings.assets_path / "fonts",
        settings.assets_path / "stock",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    logger.info("Directory structure verified")
    
    # Start worker if enabled
    if settings.worker_enabled:
        job_worker.start()
        logger.info("Job worker started")
    
    logger.info(f"Content Factory ready at http://{settings.api_host}:{settings.api_port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Content Factory...")
    if settings.worker_enabled:
        job_worker.stop()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Content Factory",
    description="Local-first content generation system for short-form video",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Mount static files for outputs (video previews)
if settings.outputs_path.exists():
    app.mount("/outputs", StaticFiles(directory=str(settings.outputs_path)), name="outputs")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Content Factory",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "api": "/api"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "worker_running": job_worker.running,
        "current_job": job_worker.current_job_id
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
