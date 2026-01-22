"""
Script to seed default niches into the database.
Run: python scripts/seed_niches.py
"""
import sys
sys.path.insert(0, '.')

from app.db import create_db_and_tables, get_sync_session
from app.models import Niche, VideoStyle


DEFAULT_NICHES = [
    {
        "name": "ai_tech",
        "description": "AI, tech news, and futuristic content",
        "style": VideoStyle.NARRATOR_BROLL,
        "posts_per_day": 2,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": True,
        "hashtags": ["ai", "tech", "future", "technology", "innovation", "chatgpt", "artificialintelligence"],
        "prompt_hook": "Create a shocking or surprising hook about {topic} that makes viewers stop scrolling. Use a bold claim or counterintuitive statement. Keep it under 15 words.",
        "prompt_body": "Write an informative and engaging script about {topic}. Include 3-4 key points. Use simple language that anyone can understand. Make it conversational, not robotic. Target length: 45 seconds of speech.",
        "prompt_cta": "Write a call-to-action asking viewers to follow for more AI/tech content. Make it natural, not salesy. Under 10 words.",
        "min_duration_seconds": 30,
        "max_duration_seconds": 60,
    },
    {
        "name": "finance_tax",
        "description": "Personal finance, tax tips, and money advice",
        "style": VideoStyle.NARRATOR_BROLL,
        "posts_per_day": 1,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": True,
        "hashtags": ["money", "finance", "taxes", "investing", "savings", "wealth", "financialfreedom", "moneytips"],
        "prompt_hook": "Create an attention-grabbing hook about {topic} that appeals to people's desire to save or make money. Use urgency or reveal a secret. Under 15 words.",
        "prompt_body": "Write a clear, actionable script about {topic}. Include specific tips or steps people can take today. Avoid jargon - explain concepts simply. Target: 50 seconds of speech.",
        "prompt_cta": "Write a CTA encouraging viewers to follow for more money tips. Mention the value they'll get. Under 10 words.",
        "min_duration_seconds": 30,
        "max_duration_seconds": 60,
    },
    {
        "name": "health",
        "description": "Health tips, wellness, and fitness motivation",
        "style": VideoStyle.NARRATOR_BROLL,
        "posts_per_day": 1,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": True,
        "hashtags": ["health", "wellness", "fitness", "healthy", "workout", "nutrition", "selfcare", "healthylifestyle"],
        "prompt_hook": "Create a hook about {topic} that makes health advice feel exciting and achievable. Challenge a common belief or promise a transformation. Under 15 words.",
        "prompt_body": "Write an encouraging, science-backed script about {topic}. Include practical tips anyone can start today. Be motivating without being preachy. Target: 50 seconds.",
        "prompt_cta": "Write a supportive CTA encouraging viewers to follow their health journey with you. Warm and encouraging. Under 10 words.",
        "min_duration_seconds": 30,
        "max_duration_seconds": 60,
    },
    {
        "name": "travel",
        "description": "Travel tips, destinations, and adventure content",
        "style": VideoStyle.SLIDESHOW,
        "posts_per_day": 1,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": True,
        "hashtags": ["travel", "wanderlust", "adventure", "explore", "vacation", "traveltips", "bucketlist", "travelgram"],
        "prompt_hook": "Create a wanderlust-inducing hook about {topic} that makes viewers dream of traveling. Use vivid imagery or surprising facts. Under 15 words.",
        "prompt_body": "Write an exciting, practical script about {topic}. Include insider tips that feel like secrets. Make viewers feel like they're getting valuable travel intel. Target: 50 seconds.",
        "prompt_cta": "Write a CTA inviting viewers to follow for more travel inspiration and tips. Create FOMO. Under 10 words.",
        "min_duration_seconds": 30,
        "max_duration_seconds": 60,
    },
    {
        "name": "comedy_stick_caption",
        "description": "Funny observations and relatable humor with stick figures",
        "style": VideoStyle.STICK_CAPTION,
        "posts_per_day": 2,
        "post_to_youtube": True,
        "post_to_instagram": True,
        "post_to_tiktok": True,
        "hashtags": ["funny", "comedy", "relatable", "humor", "lol", "memes", "jokes", "viral"],
        "prompt_hook": "Write a relatable or funny opening line for a video about {topic}. Make it feel like an inside joke everyone gets. Conversational tone. Under 15 words.",
        "prompt_body": "Write a funny script about {topic} with comedic timing. Include 2-3 relatable scenarios or observations. Use pauses and punchlines effectively. Keep it clean and universally funny. Target: 30 seconds.",
        "prompt_cta": "Write a casual CTA that fits the comedy vibe. Something like asking to follow for more laughs. Under 10 words.",
        "min_duration_seconds": 20,
        "max_duration_seconds": 45,
    },
]


def seed_niches():
    """Seed default niches into database."""
    create_db_and_tables()
    
    with get_sync_session() as session:
        for niche_data in DEFAULT_NICHES:
            # Check if niche already exists
            from sqlmodel import select
            existing = session.exec(
                select(Niche).where(Niche.name == niche_data["name"])
            ).first()
            
            if existing:
                print(f"Niche '{niche_data['name']}' already exists, skipping")
                continue
            
            niche = Niche(**niche_data)
            session.add(niche)
            print(f"Created niche: {niche_data['name']}")
        
        session.commit()
    
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed_niches()
