"""
Autonomous Trend Hunter Worker.
Runs every 4 hours to identified trends and queue new jobs.
"""
import asyncio
import time
from loguru import logger
from app.services.trend_hunter_service import trend_hunter_service
from app.core.config import settings

async def main():
    logger.info("Trend Hunter Worker starting...")
    
    interval = 4 * 3600 # 4 hours
    
    while True:
        try:
            logger.info("Cycle start: Hunting for fresh trends...")
            await trend_hunter_service.run_hunter_cycle()
            logger.info(f"Cycle complete. Sleeping for {interval / 3600} hours.")
        except Exception as e:
            logger.error(f"Trend Hunter loop error: {e}")
            
        await asyncio.sleep(interval)

if __name__ == "__main__":
    asyncio.run(main())
