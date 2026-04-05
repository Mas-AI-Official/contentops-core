# Niche System Design — ContentOps as General-Purpose Content Agency

## Core Principle
ContentOps is NOT an avatar tool. It's an autonomous content agency.
Each niche runs its own full pipeline: research → script → video → distribute.
No human in the loop. Fully autonomous.

## Two Content Modes

### Mode 1: AVATAR (MAS-AI / Daena only)
- Daena avatar overlay on B-roll
- AI/tech/startup topics
- Personal brand energy
- Used for: @daena_ai (TikTok, IG, X), @masoud_masoori (X, LinkedIn)

### Mode 2: PURE VIDEO (any niche)
- No avatar — just visuals + voiceover + captions
- Research-driven content (VirAI Scout finds topics)
- Stock footage (Pexels) + AI-generated images (local Flux/SD) + Ken Burns
- Professional voiceover (Kokoro free, ElevenLabs prod)
- Used for: documentary, science, history, finance, travel, any niche

## Niche Configuration

Each niche is a self-contained content operation:

```json
{
  "niche_id": "space_documentary",
  "name": "Space & Astronomy",
  "content_mode": "pure_video",
  "research_sources": ["youtube", "arxiv", "wikipedia", "reddit"],
  "script_style": "documentary_narrator",
  "voice": {
    "provider": "kokoro",
    "voice_id": "af_heart",
    "tone": "calm, authoritative, wonder-inspiring"
  },
  "video_style": {
    "broll_sources": ["pexels", "nasa_archive"],
    "transitions": "smooth_crossfade",
    "captions": true,
    "caption_style": "documentary",
    "music": "ambient_cinematic",
    "aspect_ratios": ["9:16", "16:9"]
  },
  "accounts": ["space_tiktok", "space_youtube", "space_instagram"],
  "posting_schedule": {
    "posts_per_week": 5,
    "optimal_times": ["07:00", "12:00", "19:00"]
  },
  "hashtags": ["#space", "#astronomy", "#universe", "#science"],
  "target_audience": "Space enthusiasts, science lovers, curious minds"
}
```

## Pipeline Flow (Pure Video Mode)

```
1. DISCOVER (VirAI Scout)
   └── Scan trending topics in niche subreddits, YouTube, news
   └── Score by virality potential + content gap analysis
   └── Pick top topic

2. RESEARCH (Auto)
   └── Pull 3-5 sources (articles, papers, videos)
   └── Extract key facts, data points, narratives
   └── Build research brief

3. SCRIPT (ScriptMaestro)
   └── Generate documentary-style script from research
   └── 5-act structure adapted for niche:
       - Hook: fascinating fact or question
       - Build: context and setup
       - Core: deep insight with data
       - Peak: surprising twist or revelation
       - Close: thought-provoking conclusion + CTA
   └── QA score >= 7.0

4. VOICE (Avatar Engine — voice only, no avatar)
   └── Kokoro TTS for testing
   └── ElevenLabs for production
   └── Match voice to niche tone (calm for docs, energetic for tech)

5. VISUALS (Video Composer — pure_video mode)
   └── Search Pexels for relevant B-roll clips
   └── Ken Burns effect on stock photos
   └── AI-generate images for concepts that need illustration
   └── Layer: background video → dark overlay → captions → progress bar
   └── NO avatar layer

6. COMPOSE (Remotion)
   └── Render to platform-specific aspect ratios
   └── 9:16 for TikTok/IG/YouTube Shorts
   └── 16:9 for YouTube/LinkedIn/X

7. DISTRIBUTE (Multi-Account Distributor)
   └── Post to niche-specific accounts only
   └── Dedup check before posting
   └── Cross-influence CTAs between niche channels
   └── Record in content tracker

8. MONITOR (Analytics Hawk)
   └── Scrape engagement metrics
   └── Detect viral signals
   └── Feed back to VirAI Scout for topic optimization
```

## How to Add a New Niche

1. Create niche config in `config/niches/{niche_id}.json`
2. Create platform accounts for the niche
3. Add account credentials to `.env`
4. Add accounts to `config/accounts.json`
5. Run: `POST /api/niche/create` with niche config
6. Pipeline auto-starts on schedule

## Example Niches (Future)

| Niche | Content Mode | Accounts | Style |
|-------|-------------|----------|-------|
| AI/Tech (MAS-AI) | avatar | 11 accounts | Daena personality |
| Space Documentary | pure_video | TikTok + YT + IG | Calm narrator |
| True Crime | pure_video | TikTok + YT | Suspenseful |
| Finance/Investing | pure_video | TikTok + YT + X | Data-driven |
| History | pure_video | TikTok + YT | Storytelling |
| Science Explained | pure_video | TikTok + YT + IG | Educational |
| Travel | pure_video | TikTok + IG | Visual + voiceover |
| Cooking/Food | pure_video | TikTok + IG + YT | Step-by-step |

## What ContentOps Does That Focal Cannot

1. Fully autonomous (no human prompt needed)
2. Auto-discovers trending topics per niche
3. Multi-platform distribution (11+ channels)
4. Content deduplication (never posts same thing twice)
5. Cross-influence CTAs between channels
6. Analytics collection + viral detection
7. Niche isolation (content never bleeds across niches)
8. FREE local pipeline (Ollama + Kokoro + FFmpeg + Pexels)
9. Avatar mode for branded content
10. Self-optimizing (method scores feed back to script generation)
