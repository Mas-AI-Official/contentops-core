import os
import sys
from pathlib import Path
from sqlmodel import Session, select
import httpx
import asyncio

sys.path.append(str(Path("d:/Ideas/contentops-core/backend")))
from app.db import sync_engine
from app.models import Niche

async def main():
    # 1. Find the right Niche ID
    topic = "DAENA GAO: The Autonomous Social Media Video Engine"
    custom_script = """
Meet Daena GAO: Governed Agent Operations. 
We've just upgraded our entire content pipeline to a 24/7 autonomous social media video engine.
The system autonomously scrapes trends, writes high-converting scripts, and generates breathtaking visuals and audio locally.
With integrated LTX-2 distillation and XTTS networking, Daena GAO watermarks and publishes branded content completely hands-free.
Social medi accounts are gracefully rotated, and the PM2 ecosystem preserves 100% resilience.
Phase 5 is complete. The future of autonomous video production is here.
    """.strip()
    
    with Session(sync_engine) as session:
        niches = session.exec(select(Niche)).all()
        # Find one named "Daena" or default to the first one
        daena_niche = next((n for n in niches if "daena" in n.name.lower()), None)
        niche_id = daena_niche.id if daena_niche else niches[0].id
        print(f"Using Niche: {daena_niche.name if daena_niche else niches[0].name} (ID: {niche_id})")

    # 2. Trigger the job via the local API
    url = "http://localhost:8100/api/generator/video"
    payload = {
        "niche_id": niche_id,
        "topic": topic,
        "custom_script": custom_script,
        "topic_source": "manual"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            print(f"Success! Job Response: {data}")
    except Exception as e:
        print(f"Failed to trigger API: {e}")

if __name__ == "__main__":
    asyncio.run(main())
