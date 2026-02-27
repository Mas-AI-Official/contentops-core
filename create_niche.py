import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.db import get_sync_session
from app.models import Niche
from app.models.niche import VideoStyle
from sqlmodel import select

def create_niche():
    with get_sync_session() as session:
        # Check if exists
        existing = session.exec(select(Niche).where(Niche.name == 'Nature Deep Truths')).first()
        if existing:
            print("Niche already exists")
            return

        niche = Niche(
            name='Nature Deep Truths', 
            slug='nature-deep-truths',
            description='Deep truths about nature and animals, focusing on transformation, survival, and ancient wisdom. Example: The eagle rebirth story.', 
            keywords='nature, animals, wisdom, transformation, eagle rebirth, survival', 
            style=VideoStyle.NARRATOR_BROLL, 
            prompt_hook='Start with a shocking or profound truth about an animal that mirrors human life.', 
            prompt_body='Explain the deep biological or behavioral truth in detail, using a storytelling tone. If appropriate, use a dialogue between a curious student and a wise mentor.', 
            prompt_cta='Follow for more deep truths about the natural world.', 
            hashtags=['nature', 'wisdom', 'animals', 'transformation', 'deepfacts']
        )
        session.add(niche)
        print('Niche created successfully')

if __name__ == "__main__":
    create_niche()
