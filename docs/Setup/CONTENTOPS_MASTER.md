# ContentOps — Autonomous AI Media Agency
**Version:** 1.0.0 | **Company:** MAS-AI Technologies Inc.
**Primary Tenant:** MAS-AI / Daena (AI Influencer)
**Status:** Phase 1 Build

---

## WHAT THIS IS

ContentOps is a fully autonomous, 24/7 AI media agency operating as a backend system behind **Daena**, MAS-AI's AI influencer. It runs the complete loop:

```
TREND DISCOVERY → VIRAL ANALYSIS → SCRIPT → AVATAR VIDEO → PUBLISH → MONITOR → OPTIMIZE
```

No human input required after initial setup. Masoud opens a dashboard, sees what's running, optionally drops an idea, and the agents handle everything to final post.

---

## SYSTEM COMPONENTS

### 1. VirAI Scout — Intelligence Gathering
Scrapes top 5+ influencers per niche. Downloads videos. Transcribes with Whisper. Reverse-engineers what made them viral. Stores patterns in Hook Vault.

### 2. Script Maestro — Content Generation
Takes viral patterns + current trends + niche context → generates coherent, story-driven scripts. Uses local Ollama models (Qwen/Gemma) for speed, Claude API for final refinement. Solves the "messy data → bad script" problem with a 4-stage pipeline.

### 3. Daena Avatar Engine — Digital Human Production
Animates Daena's avatar with lip sync using open-source local models (SadTalker → MuseTalk → LivePortrait). ElevenLabs for voice, Kokoro/Coqui TTS as free fallback.

### 4. Video Composer — Remotion Production
Programmatically renders final videos using React/Remotion. Platform-specific templates (9:16 for TikTok/Reels, 16:9 for YouTube, 1:1 for IG). Auto B-roll from Pexels. Auto caption burn. Auto music selection.

### 5. Distribution Engine — Multi-Platform Publishing
Schedules and posts to TikTok, Instagram, YouTube, LinkedIn, X. Platform-native formatting. Hashtag intelligence. Optimal timing per platform.

### 6. Analytics Hawk — Performance Intelligence
Collects engagement data. Tags each video with the method used (hook type, format, CTA style). Detects viral signals. Auto-escalates winning patterns to the top of production queue.

### 7. Method Optimizer — Self-Tuning Loop
Scores every method. Updates Hook Vault. Fires off new test videos to validate hypotheses. Keeps the system getting better every day automatically.

### 8. Tool Manager — Token Economy
Activates only the tools needed for the current pipeline stage. Shuts down unused services. Estimated 60–70% token reduction vs. always-on approach.

### 9. Multi-Tenant Core
Each client/tenant gets isolated brand lanes, separate credentials, dedicated content calendars. Tenant 1 = MAS-AI/Daena. System can sell agency services.

---

## TECH STACK

| Category | Primary | Fallback / Free |
|---|---|---|
| Orchestration | Claude Code Max | n8n self-hosted |
| Script LLM | Qwen2.5-7B (Ollama) + Gemma 4 31B | Claude API (complex only) |
| Code tasks | Claude Code + Codex CLI | Daena-coder |
| Research | Gemini CLI | Web search |
| Voice TTS | ElevenLabs API | Kokoro-82M / Coqui TTS |
| Lip Sync | MuseTalk (30fps real-time) | SadTalker / LivePortrait |
| Body / Pose | SadTalker full-body | ComfyUI AnimateDiff |
| Video Render | Remotion (React) | FFmpeg direct |
| B-Roll | Pexels API (free) | Pixabay API |
| Music | Free Music Archive | EpidemicSound |
| Scheduling | Custom agent | Buffer API |
| Analytics | Platform APIs | Internal SQLite DB |
| Scraping | yt-dlp + Playwright | Apify (cloud) |
| Transcription | Whisper local | Faster-Whisper |

---

## DIRECTORY STRUCTURE

```
D:\contentops\
├── CLAUDE.md                    ← Boot protocol (READ FIRST)
├── CONTENTOPS_MASTER.md         ← This file
├── ARCHITECTURE.md              ← Technical design
├── PIPELINE.md                  ← Step-by-step pipeline
├── AGENTS.md                    ← Agent team definitions
├── VIRAL_INTELLIGENCE.md        ← How to study viral videos
├── AVATAR_SYSTEM.md             ← Daena avatar engine
├── VIDEO_PRODUCTION.md          ← Remotion templates + compose
├── ANALYTICS_SYSTEM.md          ← Performance tracking
├── TOOL_MANAGEMENT.md           ← Token-efficient tool switching
├── MULTI_TENANT.md              ← Multi-client architecture
├── BUILD_SEQUENCE.md            ← Ordered build steps
│
├── src/
│   ├── agents/
│   │   ├── virai_scout.py       ← Scraper + analyzer
│   │   ├── script_maestro.py    ← Script generator
│   │   ├── avatar_engine.py     ← Daena lip sync
│   │   ├── video_composer.py    ← Remotion orchestrator
│   │   ├── distributor.py       ← Platform publisher
│   │   ├── analytics_hawk.py    ← Metrics collector
│   │   ├── method_optimizer.py  ← Self-tuning
│   │   └── tool_manager.py      ← Token economy
│   │
│   ├── video/
│   │   ├── remotion/            ← React video templates
│   │   │   ├── templates/
│   │   │   │   ├── TikTokShort.tsx
│   │   │   │   ├── YouTubeShort.tsx
│   │   │   │   ├── InstagramReel.tsx
│   │   │   │   └── LinkedInPost.tsx
│   │   │   └── components/
│   │   │       ├── AvatarOverlay.tsx
│   │   │       ├── CaptionBurner.tsx
│   │   │       ├── BRollLayer.tsx
│   │   │       └── HookText.tsx
│   │   └── ffmpeg_utils.py
│   │
│   ├── intelligence/
│   │   ├── hook_vault.json      ← Viral hook database
│   │   ├── method_scores.json   ← Performance per method
│   │   ├── influencer_db.json   ← Tracked influencers
│   │   └── trend_cache.json
│   │
│   ├── tenants/
│   │   └── mas-ai/
│   │       ├── brand.json
│   │       ├── calendar.json
│   │       └── posts/
│   │
│   ├── api/
│   │   └── dashboard.py         ← FastAPI dashboard backend
│   │
│   └── dashboard/               ← React frontend
│       ├── src/
│       └── package.json
│
├── scripts/
│   ├── setup.sh                 ← Full environment setup
│   ├── start_all.sh             ← Launch everything
│   └── reset_day.sh             ← Daily reset
│
└── data/
    ├── scraped/                 ← Downloaded influencer content
    ├── transcripts/             ← Whisper outputs
    ├── scripts/                 ← Generated scripts
    ├── audio/                   ← TTS outputs
    ├── videos/                  ← Rendered videos
    └── published/               ← Post log
```

---

## PRIORITIES

| Priority | Component | Why |
|---|---|---|
| P0 | Script Maestro coherence engine | Core problem — messy script → bad video |
| P0 | Tool Manager token system | Budget survival |
| P0 | ElevenLabs + SadTalker pipeline | First working video |
| P1 | Remotion composer templates | Scalable production |
| P1 | VirAI Scout + Hook Vault | Content intelligence |
| P1 | Analytics Hawk | Know what works |
| P2 | Dashboard | Visibility |
| P2 | Distribution Engine | Multi-platform |
| P2 | Method Optimizer | Self-tuning |
| P3 | Multi-tenant | Agency expansion |
| P3 | Full body Daena (ComfyUI) | Premium human-like avatar |
