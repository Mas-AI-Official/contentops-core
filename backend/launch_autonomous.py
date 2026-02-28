"""
Launch script for the 24/7 Autonomous Content Engine.
"""
import asyncio
import signal
import sys
from loguru import logger
from app.db import create_db_and_tables
from app.workers.job_worker import job_worker
from app.workers.trend_hunter_worker import main as run_trend_hunter

async def start_autonomous_engine():
    logger.info("Initializing Autonomous Content Engine...")
    create_db_and_tables()
    
    # Start the Job Worker (Process Queue)
    logger.info("Starting Job Worker...")
    job_worker.start()
    
    # Start the Trend Hunter (Queue Generator)
    logger.info("Starting Trend Hunter...")
    
    try:
        # Run both in the same event loop
        await asyncio.gather(
            run_trend_hunter(),
            # Wait forever or until interrupted
            asyncio.Event().wait() 
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down engine...")
        job_worker.stop()
    except Exception as e:
        logger.error(f"Engine crash: {e}")
        job_worker.stop()

if __name__ == "__main__":
    try:
        asyncio.run(start_autonomous_engine())
    except KeyboardInterrupt:
        sys.exit(0)
