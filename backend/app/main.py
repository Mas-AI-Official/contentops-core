"""
Content Factory - Main FastAPI Application

A local-first content generation system for creating and publishing
short-form vertical videos across multiple platforms.
"""
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys
from sqlmodel import select

from app.core.config import settings
from app.db import create_db_and_tables, get_sync_session
from app.models import Niche
from app.api import api_router
from app.api.compat import router as compat_router
from app.workers import job_worker
from app.services.scheduler_service import content_scheduler


async def seed_default_niches():
    """Seed default niches if database is empty."""
    from sqlmodel import select
    from app.models import Niche, NicheCreate

    with get_sync_session() as session:
        # Check if niches already exist
        existing_niches = session.exec(select(Niche)).all()
        if existing_niches:
            logger.info(f"Found {len(existing_niches)} existing niches, skipping seed")
            return

        logger.info("Database empty, seeding default niches...")

        # Default niches with their configurations - organized by platform
        default_niches = [
            # === YOUTUBE SHORTS (6 niches) ===
            {
                "name": "AIThatSavesYouMoney_CA",
                "slug": "ai-that-saves-you-money-ca",
                "description": "AI tools and apps that help Canadians save money on everyday expenses",
                "platform": "youtube",
                "account_name": "AISavingsCanada",
                "prompt_hook": "You are a Canadian financial expert specializing in AI-powered money-saving solutions. Hook viewers with a surprising statistic about AI saving money: 'Did you know AI can save Canadians an average of $500/month on bills?'",
                "prompt_body": "Explain 5 practical AI tools/apps that help Canadians save money. Focus on: grocery shopping, utility bills, banking fees, insurance, and subscriptions. Use Canadian examples and dollar amounts. Make it conversational and exciting.",
                "prompt_cta": "Download one AI app mentioned today and save $50 on your first bill. Comment below which app you're trying first!",
                "hashtags": ["AISavings", "CanadianMoneyTips", "AIFinancialTools", "SaveMoneyAI", "CanadianFinance"],
                "style": "narrator_broll",
                "max_duration_seconds": 60,
                "target_audience": "Canadians looking to save money with AI",
                "content_type": "educational",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["09:00", "19:00"]
            },
            {
                "name": "TechNewsYouCanUse",
                "slug": "tech-news-you-can-use",
                "description": "Tech news explained in practical terms with immediate applications",
                "platform": "youtube",
                "account_name": "TechNewsExplained",
                "prompt_hook": "Hook with breaking tech news: 'Google just released an AI feature that could save you 2 hours daily - but here's the catch'",
                "prompt_body": "Explain recent tech developments in plain language. Focus on 3-4 news items that have immediate practical applications. Include how-to steps and real-world examples.",
                "prompt_cta": "Try one of these tech tips today and comment how it changed your workflow!",
                "hashtags": ["TechNews", "PracticalTech", "TechTips", "Innovation", "FutureTech"],
                "style": "narrator_broll",
                "max_duration_seconds": 60,
                "target_audience": "Tech enthusiasts who want practical applications",
                "content_type": "news",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["10:00", "18:00"]
            },
            {
                "name": "LifeSystemsScripts",
                "slug": "life-systems-scripts",
                "description": "Scripts for implementing life-changing systems and habits",
                "platform": "youtube",
                "account_name": "LifeSystemsMaster",
                "prompt_hook": "Hook with transformation promise: 'One simple system changed my entire morning routine - and it can change yours too'",
                "prompt_body": "Present a complete system implementation script. Break it down into: why it works, step-by-step setup, common obstacles, and success tracking. Make it motivational and actionable.",
                "prompt_cta": "Implement one part of this system today and share your first win in the comments!",
                "hashtags": ["LifeSystems", "HabitBuilding", "Productivity", "LifeHacks", "PersonalDevelopment"],
                "style": "narrator_broll",
                "max_duration_seconds": 55,
                "target_audience": "People seeking life improvements",
                "content_type": "motivational",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["08:00", "20:00"]
            },
            {
                "name": "MicroMoneyMoves_CA",
                "slug": "micro-money-moves-ca",
                "description": "Small financial decisions that add up to big savings for Canadians",
                "platform": "youtube",
                "account_name": "CanadianMoneyHacks",
                "prompt_hook": "Hook with a shocking micro-saving statistic: 'Canadians waste $200/month on tiny expenses - here's how AI fixes it'",
                "prompt_body": "Break down 6 micro-money moves: rounding up purchases, optimizing subscriptions, finding better rates, avoiding fees, smart shopping, and automated savings. Use Canadian pricing and relatable examples.",
                "prompt_cta": "Pick one micro-move from this video and implement it this week. Tag a friend who needs to see this!",
                "hashtags": ["MicroSavings", "CanadianFinance", "MoneyTipsCanada", "FinancialFreedom", "SmartMoney"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Budget-conscious Canadians",
                "content_type": "how-to",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["11:00", "17:00"]
            },
            {
                "name": "HealthTipsDaily",
                "slug": "health-tips-daily",
                "description": "Daily health tips in the 'I'm ginger, if you eat me...' format",
                "platform": "youtube",
                "account_name": "DailyHealthTips",
                "prompt_hook": "I'm ginger. If you eat me every day, this happens to your body.",
                "prompt_body": "Explain 5-6 surprising health benefits of the featured food/supplement. Include scientific backing, dosage recommendations, and practical ways to incorporate it daily.",
                "prompt_cta": "Try this health tip today and share your experience in the comments!",
                "hashtags": ["HealthTips", "NaturalHealth", "DailyHealth", "Wellness", "HealthyLiving"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Health-conscious individuals",
                "content_type": "health_tips",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["07:00", "16:00"]
            },
            {
                "name": "CookingHacksPro",
                "slug": "cooking-hacks-pro",
                "description": "Professional cooking hacks and techniques",
                "platform": "youtube",
                "account_name": "CookingHacksPro",
                "prompt_hook": "This kitchen hack will change how you cook forever - chefs hate it!",
                "prompt_body": "Demonstrate 5-6 cooking hacks with clear before/after examples. Include the science behind why it works and time-saving benefits.",
                "prompt_cta": "Try this hack in your next meal and tag me in your results!",
                "hashtags": ["CookingHacks", "KitchenTips", "CookingTips", "ChefSecrets", "HomeCooking"],
                "style": "narrator_broll",
                "max_duration_seconds": 60,
                "target_audience": "Home cooks and food enthusiasts",
                "content_type": "how-to",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["12:00", "21:00"]
            },

            # === INSTAGRAM REELS (5 niches) ===
            {
                "name": "BeautyTrendsNow",
                "slug": "beauty-trends-now",
                "description": "Latest beauty trends and viral makeup tutorials",
                "platform": "instagram",
                "account_name": "BeautyTrendsDaily",
                "prompt_hook": "This beauty hack went viral for a reason - watch till the end!",
                "prompt_body": "Show 4-5 trending beauty techniques with quick cuts and text overlays. Focus on affordable products and easy-to-follow steps.",
                "prompt_cta": "Try this trend and tag me in your results! 💄✨",
                "hashtags": ["BeautyTrends", "MakeupTutorial", "BeautyHacks", "ViralBeauty", "Skincare"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Beauty enthusiasts and trend followers",
                "content_type": "beauty",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["09:00", "18:00"]
            },
            {
                "name": "FashionFindsDaily",
                "slug": "fashion-finds-daily",
                "description": "Daily fashion discoveries and styling tips",
                "platform": "instagram",
                "account_name": "FashionFindsDaily",
                "prompt_hook": "This outfit hack costs $5 and looks expensive - you need this!",
                "prompt_body": "Show 6 styling tips using affordable items. Include outfit transformations and where to shop.",
                "prompt_cta": "Recreate this look and tag me! 👗✨",
                "hashtags": ["FashionTips", "StyleHacks", "OutfitIdeas", "Thrifting", "FashionFinds"],
                "style": "narrator_broll",
                "max_duration_seconds": 40,
                "target_audience": "Fashion lovers on a budget",
                "content_type": "fashion",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["10:00", "19:00"]
            },
            {
                "name": "HomeDecorHacks",
                "slug": "home-decor-hacks",
                "description": "Creative home decoration ideas on a budget",
                "platform": "instagram",
                "account_name": "HomeDecorMagic",
                "prompt_hook": "Transform your space with this $10 hack - DIY magic!",
                "prompt_body": "Show 5 budget-friendly decor transformations with before/after shots and step-by-step instructions.",
                "prompt_cta": "Try this in your home and share the results! 🏠✨",
                "hashtags": ["HomeDecor", "DIYTutorial", "BudgetDecor", "HomeMakeover", "InteriorDesign"],
                "style": "narrator_broll",
                "max_duration_seconds": 50,
                "target_audience": "Homeowners and renters",
                "content_type": "diy",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["11:00", "17:00"]
            },
            {
                "name": "PetCareTips",
                "slug": "pet-care-tips",
                "description": "Essential pet care advice and training tips",
                "platform": "instagram",
                "account_name": "PetCareGuru",
                "prompt_hook": "This training trick works on ANY dog - watch your pup transform!",
                "prompt_body": "Demonstrate 5 pet care tips with cute animal footage. Include health, training, and bonding activities.",
                "prompt_cta": "Try this with your pet and show me the results! 🐾❤️",
                "hashtags": ["PetCare", "DogTraining", "PetTips", "AnimalCare", "PetLovers"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Pet owners and animal lovers",
                "content_type": "pet_care",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["08:00", "20:00"]
            },
            {
                "name": "QuickRecipes",
                "slug": "quick-recipes",
                "description": "5-minute recipes for busy people",
                "platform": "instagram",
                "account_name": "QuickRecipesNow",
                "prompt_hook": "Restaurant-quality meal in 5 minutes - no one believes this works!",
                "prompt_body": "Show 3-4 super fast recipes with quick cuts, text overlays, and minimal ingredients.",
                "prompt_cta": "Make this tonight and tag me! 🍝✨",
                "hashtags": ["QuickRecipes", "5MinMeals", "EasyCooking", "FastFood", "HomeCooking"],
                "style": "narrator_broll",
                "max_duration_seconds": 35,
                "target_audience": "Busy parents and working professionals",
                "content_type": "recipes",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["12:00", "18:30"]
            },

            # === TIKTOK (5 niches) ===
            {
                "name": "DanceChallenges",
                "slug": "dance-challenges",
                "description": "Trending dance challenges and tutorials",
                "platform": "tiktok",
                "account_name": "DanceChallengeKing",
                "prompt_hook": "This dance went viral overnight - learn it in 60 seconds!",
                "prompt_body": "Break down a trending dance in slow motion with step-by-step instructions and music beats.",
                "prompt_cta": "Learn it, film it, and tag me! 💃🕺",
                "hashtags": ["DanceChallenge", "ViralDance", "DanceTutorial", "TrendingDance", "DanceTok"],
                "style": "narrator_broll",
                "max_duration_seconds": 60,
                "target_audience": "Dance enthusiasts and trend followers",
                "content_type": "dance",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["14:00", "21:00"]
            },
            {
                "name": "ComedySketches",
                "slug": "comedy-sketches",
                "description": "Funny skits and comedy content",
                "platform": "tiktok",
                "account_name": "ComedySketchDaily",
                "prompt_hook": "You won't believe what happened when I tried this... 🤣",
                "prompt_body": "Create short comedic skits with relatable situations, punchy dialogue, and quick cuts.",
                "prompt_cta": "What's the funniest thing that happened to you this week? 😂",
                "hashtags": ["Comedy", "FunnyVideos", "SketchComedy", "ViralComedy", "LaughOutLoud"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Comedy fans and entertainment seekers",
                "content_type": "comedy",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["13:00", "20:00"]
            },
            {
                "name": "LifeHacksDaily",
                "slug": "life-hacks-daily",
                "description": "Daily life hacks and clever solutions",
                "platform": "tiktok",
                "account_name": "LifeHacksMaster",
                "prompt_hook": "This life hack saves me 30 minutes daily - mind blown! 🤯",
                "prompt_body": "Demonstrate 3-4 clever life hacks with quick cuts, text overlays, and immediate payoff.",
                "prompt_cta": "Try this hack and tell me how much time you saved! ⏰",
                "hashtags": ["LifeHacks", "HackTok", "SmartLife", "TimeSaver", "GeniusHacks"],
                "style": "narrator_broll",
                "max_duration_seconds": 40,
                "target_audience": "Problem solvers and efficiency enthusiasts",
                "content_type": "life_hacks",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["15:00", "19:00"]
            },
            {
                "name": "ASMRRelaxation",
                "slug": "asmr-relaxation",
                "description": "ASMR content for relaxation and sleep",
                "platform": "tiktok",
                "account_name": "ASMRSleepStories",
                "prompt_hook": "Fall asleep in 3 minutes with this ASMR technique ✨",
                "prompt_body": "Create calming ASMR content with soft sounds, gentle movements, and relaxing narration.",
                "prompt_cta": "Sweet dreams! Comment if this helped you sleep 💤",
                "hashtags": ["ASMR", "SleepASMR", "Relaxation", "SleepAid", "CalmingSounds"],
                "style": "narrator_broll",
                "max_duration_seconds": 180,
                "target_audience": "People seeking relaxation and better sleep",
                "content_type": "asmr",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["22:00", "02:00"]
            },
            {
                "name": "MagicTricks",
                "slug": "magic-tricks",
                "description": "Easy magic tricks you can learn at home",
                "platform": "tiktok",
                "account_name": "MagicTricksEasy",
                "prompt_hook": "This card trick fools everyone - learn it in 30 seconds! 🎴",
                "prompt_body": "Teach simple magic tricks with clear instructions, multiple angles, and reveal at the end.",
                "prompt_cta": "Show your friends and tag me! 🎩✨",
                "hashtags": ["MagicTricks", "CardTricks", "LearnMagic", "EasyMagic", "MagicTutorial"],
                "style": "narrator_broll",
                "max_duration_seconds": 45,
                "target_audience": "Magic enthusiasts and party hosts",
                "content_type": "magic",
                "auto_mode": False,
                "posts_per_day": 2,
                "posting_schedule": ["16:00", "22:30"]
            }
        ]

        # Create niches in database
        created_count = 0
        for niche_data in default_niches:
            try:
                # Create niche with basic data first
                basic_data = {k: v for k, v in niche_data.items()
                            if k not in ['auto_mode', 'posts_per_day', 'posting_schedule']}
                niche = Niche.model_validate(basic_data)

                # Set additional fields if provided
                if 'auto_mode' in niche_data:
                    niche.auto_mode = niche_data['auto_mode']
                if 'posts_per_day' in niche_data:
                    niche.posts_per_day = niche_data['posts_per_day']
                if 'posting_schedule' in niche_data:
                    niche.posting_schedule = niche_data['posting_schedule']

                session.add(niche)
                session.commit()
                session.refresh(niche)

                # Create niche directory and files
                niche_dir = settings.niches_path / niche.slug
                niche_dir.mkdir(parents=True, exist_ok=True)

                # Create config.json
                config_file = niche_dir / "config.json"
                config_data = {
                    "name": niche.name,
                    "slug": niche.slug,
                    "description": niche.description,
                    "target_audience": niche.target_audience,
                    "content_type": niche.content_type,
                    "hashtags": niche.hashtags,
                    "platform": niche.platform,
                    "account_name": niche.account_name,
                    "auto_mode": niche.auto_mode,
                    "posts_per_day": niche.posts_per_day,
                    "posting_schedule": niche.posting_schedule,
                    "created_at": niche.created_at.isoformat() if niche.created_at else None
                }
                import json
                config_file.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Create topics.json
                topics_file = niche_dir / "topics.json"
                topics_data = {"topics": [], "used": [], "auto_sources": []}
                topics_file.write_text(json.dumps(topics_data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Create feeds.json
                feeds_file = niche_dir / "feeds.json"
                feeds_data = {"feeds": []}
                feeds_file.write_text(json.dumps(feeds_data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Create assets subdirectory
                assets_dir = niche_dir / "assets"
                assets_dir.mkdir(exist_ok=True)

                # Create templates subdirectory and copy default templates
                templates_dir = niche_dir / "templates"
                templates_dir.mkdir(exist_ok=True)

                # Copy relevant templates based on niche type
                _copy_niche_templates(niche, templates_dir)

                created_count += 1
                logger.info(f"Created niche: {niche.name} (slug: {niche.slug})")

            except Exception as e:
                logger.error(f"Failed to create niche {niche_data['name']}: {e}")
                session.rollback()
        logger.info(f"Successfully seeded {created_count} default niches")

def _copy_niche_templates(niche: Niche, templates_dir: Path):
    """Copy appropriate templates for the niche."""
    import shutil

    # Map niche content types to templates
    template_mapping = {
        "educational": ["health_tips.json"],
        "how-to": ["health_tips.json"],
        "motivational": ["health_tips.json"],
        "debate": ["debate_format.json"],
        "news": ["news_summary.json"]
    }

    content_type = niche.content_type or "educational"
    template_files = template_mapping.get(content_type, ["health_tips.json"])

    # Source templates directory
    source_templates = Path(settings.base_path) / "data" / "assets" / "templates"

    for template_file in template_files:
        src = source_templates / template_file
        dst = templates_dir / template_file
        if src.exists():
            shutil.copy2(src, dst)
            logger.info(f"Copied template {template_file} to {niche.name}")
        else:
            logger.warning(f"Template {template_file} not found at {src}")


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
    from app.db.migrations import run_migrations
    run_migrations()
    
    create_db_and_tables()
    logger.info("Database initialized")

    # Seed default niches if database is empty
    await seed_default_niches()
    logger.info("Default niches verified")

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

    # Sync niches between disk and database
    from app.services.niche_sync_service import niche_sync_service
    niche_sync_service.sync_niches_to_db()

    # Ensure all niches have proper disk structure
    with get_sync_session() as session:
        niches = session.exec(select(Niche)).all()
        for niche in niches:
            niche_sync_service.sync_niche_to_disk(niche)
    
    # Start worker if enabled
    if settings.worker_enabled:
        job_worker.start()
        logger.info("Job worker started")

    # Start content scheduler
    try:
        content_scheduler.initialize()
        content_scheduler.start()
        logger.info("Content scheduler started")
    except Exception as e:
        logger.error(f"Failed to start content scheduler: {e}")
        # Continue startup even if scheduler fails
    
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
app.include_router(compat_router)

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


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """Lightweight websocket endpoint for external dashboards."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "heartbeat"})
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
