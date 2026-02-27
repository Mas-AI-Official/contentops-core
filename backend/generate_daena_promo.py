import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.getcwd())

from sqlmodel import Session, select
from app.db import get_sync_session
from app.models import Job, JobType, JobStatus, Niche, VideoStyle

DAENA_GUARD_SCRIPT = """
[Scene 1: Cyberpunk landscape, Deep Space Blue sky, slow drone shot]
The digital world is evolving, but so are the threats.

[Scene 2: Glowing shield icon over a server rack, Neon Green pulse]
Meet Daena Guard. The first autonomous security layer for the Web3 era.

[Scene 3: Fast cuts of code being scanned, green lines of text]
Real-time monitoring. Instant threat detection. Zero human intervention.

[Scene 4: A glassmorphism dashboard showing "THREAT BLOCKED"]
By leveraging local AI models, Daena Guard watches over your assets 24/7.

[Scene 5: 3D render of a futuristic vault closing]
Decentralized, unhackable, and private.

[Scene 6: Close up of a logo glowing in Neon Cyber-Green]
Your data belongs to you. We just make sure it stays that way.

[Scene 7: Call to Action - Daena.ai URL on screen]
Join the guard. Protect your future today.
"""

VISUAL_CUES = """[
    "Cyberpunk future city at night, deep space blue lighting, cinematic drone view",
    "Digital servers with glowing neon green energy shields, cybernetic aesthetic",
    "Futuristic data stream, holographic code scanning in neon green",
    "Glassmorphism UI overlay on top of server data, showing security status",
    "Futuristic vault door with mechanical locks, blue and green lighting",
    "Glowing neon green shield logo on a dark glass textured background",
    "Call to action text 'JOIND DAENA' on a high-tech interface background"
]"""

async def create_daena_promo():
    print("Infecting Daena Guard Promo Job...")
    with get_sync_session() as session:
        # Find or create a niche
        niche = session.exec(select(Niche).where(Niche.slug == "daena-ai")).first()
        if not niche:
            print("Creating Daena AI Niche...")
            niche = Niche(
                name="Daena AI",
                slug="daena-ai",
                description="Web3 Security and Autonomous AI",
                hashtags=["Web3", "CyberSecurity", "AI", "Daena"],
                style=VideoStyle.NARRATOR_BROLL
            )
            session.add(niche)
            session.commit()
            session.refresh(niche)

        # Create the Job
        job = Job(
            niche_id=niche.id,
            job_type=JobType.GENERATE_ONLY,
            topic="Daena Guard Promotional Video",
            full_script=DAENA_GUARD_SCRIPT,
            visual_cues=VISUAL_CUES,
            status=JobStatus.PENDING,
            video_model="ltx-2-distilled-fp8.safetensors"
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        
        print(f"SUCCESS: Created Job ID {job.id}")
        return job.id

if __name__ == "__main__":
    asyncio.run(create_daena_promo())
