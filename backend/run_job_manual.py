import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.getcwd())

from app.workers.job_worker import run_job_now

async def main():
    job_id = 2 # The ID we just created
    print(f"Starting Job {job_id}...")
    await run_job_now(job_id)
    print("Job processing trigger finished.")

if __name__ == "__main__":
    asyncio.run(main())
