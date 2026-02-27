# Content OPS Core – Full Codebase Audit & Report

**Date:** 2026-02-26  
**Scope:** Full structure, purpose, workflow, what we are building, backend, frontend, pipelines

---

## 1. What This Is About

**Content OPS AI (Content OPS Core)** is a **local-first, end-to-end content generation system** for creating and publishing **short-form vertical video** (e.g. 60s, 1080×1920) across **multiple niches** and **multiple platforms**: YouTube Shorts, Instagram Reels, TikTok.

### Core idea
- One dashboard to manage **niches** (e.g. Tech News, Health Tips, Life Hacks), each with its own prompts, voice, and platform targets.
- **AI pipeline**: topic → script (LLM) → voice (TTS) → subtitles (Whisper) → video (LTX-2 or FFmpeg).
- **Automation**: scheduled generation and publishing, trend hunting, RSS topics, 70/30 growth engine.
- **Compliance**: official platform APIs only; **manual review required** before any publish.

### Goals
- **Multi-niche**: Many content verticals (AI/Tech, Finance, Health, Travel, Comedy, etc.) with per-niche prompts and models.
- **AI-powered**: Script (Ollama / HF Router / MCP), TTS (XTTS / ElevenLabs), subtitles (Whisper), optional LTX-2 video, FFmpeg compositing.
- **Automation**: 2–3 posts/day per niche, RSS topic discovery, auto publishing, analytics and learning.
- **Local-first**: Run LLM, TTS, Whisper (and optionally LTX) locally; cloud optional via MCP/HF Router.

---

## 2. What We Are Building (Current vs Planned)

### 2.1 Already in place
- **Backend**: FastAPI app, SQLModel (SQLite), all API routes, job worker, content scheduler, trend hunter.
- **Frontend**: Vite + React dashboard (Overview, Niches, Accounts, Generator, Queue, Library, Scripts, Analytics, Models, Doctor, Settings, Scrape, Viral Lab, Platforms).
- **Content pipeline**: Topic (RSS/list/LLM) → Script → TTS → Subtitles → Video (LTX or FFmpeg) → Review → Publish → Analytics.
- **Automation**: APScheduler for pending/scheduled jobs; trend hunter (MCP → scraper → LLM fallback) and autonomous job creation (Ollama).
- **Integrations**: Ollama, HF Router, MCP, XTTS, ElevenLabs, Whisper, LTX-Video, Remotion, YouTube/Instagram/TikTok APIs.
- **Extras**: Prompt packs, memory, signals, patterns, governance, prompt intelligence, diagnostics (Pipeline Doctor), export/optimize per platform.

### 2.2 What we are going to build / update
- **Stability & robustness**: Fix edge cases (e.g. LLM missing `visual_prompts`, YouTube trending scraper), improve error handling and fallbacks.
- **Automation**: Harden trend hunter and scheduler; optional MCP connectors for trends (xpoz, youtube_data) when available.
- **Quality**: Per-niche model tuning, 70/30 growth engine refinement, template weighting from analytics.
- **Platform**: Platform-specific export (encoding, aspect ratio), compliance checks before publish.
- **LTX-2**: Optional local AI video (LTX-2) with FP8/distilled for 8GB VRAM; ComfyUI or direct API.
- **Ops**: Optional Docker/CI for backend and workers; keep LTX-Video’s existing Ruff/Black CI.
- **Dashboard**: More pages and controls as needed (e.g. autopilot, retention, diagnostics).

---

## 3. Full Directory Structure

```
D:\Ideas\contentops-core\
├── backend\                    # FastAPI backend
│   ├── app\
│   │   ├── api\                # API routes (see §4.3)
│   │   ├── core\               # config.py, websockets.py, platforms.py
│   │   ├── db\                 # database.py, migrations.py
│   │   ├── models\             # SQLModel schemas (see §4.4)
│   │   ├── services\           # Business logic (see §4.5)
│   │   ├── templates\          # JSON prompt templates (e.g. health_tips.json)
│   │   ├── utils\              # helpers
│   │   ├── workers\            # job_worker, trend_hunter_worker
│   │   └── main.py             # FastAPI app entry
│   ├── LTX-2\                  # LTX-2 monorepo (ltx-core, ltx-pipelines, ltx-trainer)
│   ├── LTX-Video\              # LTX-Video package (pipelines, models, tests)
│   ├── remotion\               # Remotion-based rendering
│   ├── scripts\                # seed_niches, etc.
│   ├── tests\                  # Backend tests
│   ├── launch_autonomous.py    # Job worker + trend hunter loop
│   ├── run_job_manual.py       # run_job_now(job_id)
│   └── requirements.txt
├── frontend\                   # Vite + React
│   ├── public\
│   ├── src\
│   │   ├── components\         # Layout, Card, Button, Modal, VideoPlayer, MobilePreview, StatusBadge, ActiveJobsBar
│   │   ├── pages\              # Overview, Platforms, Niches, Accounts, Generator, Scrape, ViralLab, Queue, Library, Scripts, Analytics, Models, PipelineDoctor, Settings
│   │   ├── api.js              # Axios API client
│   │   ├── App.jsx             # Routes
│   │   ├── main.jsx
│   │   └── index.css
│   └── package.json
├── data\                       # Runtime data (created at run)
│   ├── assets\                 # music, logos, fonts, stock, templates, voices
│   ├── jobs\                   # Per-job assets (e.g. 17, 18, 19)
│   ├── logs\
│   ├── niches\                 # Per-niche: config, feeds, topics, assets, templates
│   ├── outputs\                # Generated videos by niche/job (e.g. outputs/daena-ai/2)
│   ├── scripts\                # Saved scripts by niche/date/job
│   └── uploads\
├── docs\                       # Documentation
│   └── 2026-02-26\             # This report
├── models\                     # Local AI model cache (ollama, whisper, xtts, torch, etc.)
├── ops\                        # Operations scripts (optional)
├── original fronend\           # Legacy frontend (reference)
├── public\                     # Static assets (if used at root)
├── venv\                       # Python virtual environment
├── install.bat                 # One-click install
├── run.bat                     # Start backend + frontend
├── launch.bat                  # Full stack + XTTS + autonomous engine
├── setup_models.bat
├── setup_env.bat
├── setup_ffmpeg.bat
├── start_ollama.bat
├── start_xtts.bat
├── kill_all.bat
├── run_daena_job.py            # POST /api/generator/video for a niche
├── check_job.py
├── check_jobs.py
├── reset_job.py
├── fix_perms.py
├── create_niche.py
├── setup_all_models.py
├── download_models.py
├── README.md
├── PIPELINE.md
└── package.json                # Root: auto_loop (optional node cron)
```

---

## 4. Backend – Full Structure & Report

### 4.1 Entry & run
- **Entry:** `backend/app/main.py` (FastAPI).
- **Run:** From `backend/`: `python -m app.main` or `uvicorn app.main:app --reload`.
- **Port:** From config (default 8100). API docs: `/docs`, health: `/health`.
- **Lifespan:** Run migrations → create tables → seed default niches → niche sync → start job worker (if enabled) → start content scheduler → ensure model dirs.

### 4.2 Config (`backend/app/core/config.py`)
- Pydantic `Settings` from `backend/.env`.
- **Paths:** `base_path`, `data_path`, `models_path`, `assets_path`, `niches_path`, `outputs_path`, `logs_path`, `uploads_path`, `scripts_path`, plus model caches: `ollama_models_path`, `whisper_cache_path`, `xtts_cache_path`, `torch_cache_path`, `image_models_path`.
- **App:** `app_name`, `debug`, `api_host`, `api_port` (8100).
- **Services:** LLM (ollama/hf_router/mcp), TTS (xtts/elevenlabs), Whisper (model, device), video (ffmpeg/ltx), worker (enabled, interval), scheduler, MCP connectors.

### 4.3 API routes (all under `/api`)
| Prefix | File | Purpose |
|--------|------|--------|
| `/niches` | niches.py | CRUD, generate-topics, toggle-auto-mode, automate, bulk-automate, smart-schedule, trigger-generation, platforms/stats, config by slug |
| `/accounts` | accounts.py | CRUD, status, verify, link/unlink niche, map |
| `/jobs` | jobs.py | CRUD, today, run, retry, cancel, approve, logs |
| `/videos` | videos.py | List, get, stream, thumbnail, publishes, metadata, delete |
| `/analytics` | analytics.py | summary, trends, top-videos, underperformers, by-niche, by-platform, refresh, video/{id} |
| `/generator` | generator.py | topic, script, video, status/{job_id}, preview, approve, assets |
| `/settings` | settings.py | get, paths, paths/check, model-paths, services/status, env-template, autopilot, voices |
| `/models` | models.py | list, available, pull, pull status, delete, ltx, current, test, ltx/install |
| `/scripts` | scripts.py | list, stats, by-path, download, dates, niches |
| `/export` | export.py | platforms, validate, optimize, downloads |
| `/mcp` | mcp.py | status, connectors, forward |
| `/scraper` | scraper.py | ingest, analyze, items, viral-dna, run, scrape, topics, pick-topic, feeds CRUD, seed-feeds |
| `/publisher` | publisher.py | publish/{video_id}, status/{job_id} |
| `/cleanup` | cleanup.py | run, stats |
| `/trends` | trends.py | list, create, analyze, fetch |
| `/promptpack` | promptpack.py | list, create, get, optimize |
| `/memory` | memory.py | create, search, recent |
| `/signals` | signals.py | list, create, score |
| `/patterns` | patterns.py | list, create, analyze |
| `/governance` | governance.py | check |
| `/prompt-intelligence` | prompt_intelligence.py | build/{job_id}, bundle/{job_id} |
| `/diagnostics` | diagnostics.py | pipeline, fix, health |
| `/voice` | voice.py | synthesize, voices |

**Compat:** `compat_router` at `/api/v1` (brain/status, agents, voice/status, tasks/stats, system/status, projects, council, chat-history).

**Other:** `GET /`, `GET /health`, `WebSocket /ws/events`, static mount `/outputs`.

### 4.4 Database models (`backend/app/models/`)
| File | Main entities |
|------|----------------|
| niche.py | Niche, NicheCreate, NicheUpdate, NicheRead, VideoStyle, TTSProvider, WhisperDevice |
| account.py | Account, AccountCreate, AccountUpdate, AccountRead, Platform, AccountStatus |
| job.py | Job, JobCreate, JobUpdate, JobRead, JobLog, JobStatus, JobType |
| video.py | Video, VideoCreate, VideoRead, VideoPublish |
| analytics.py | VideoMetrics, DailyNicheStats, VideoScore, AnalyticsSummary |
| niche_target.py | NicheTarget |
| trend.py | Trend, TrendCreate, TrendRead, TrendAnalysis |
| prompt.py | PromptPack, PromptPackCreate, PromptPackRead, PromptsLog |
| prompt_intelligence.py | PromptBundle (ScriptPrompt, StoryboardScene, Storyboard, VisualPrompts, VoiceSpec, EditRecipe) |
| memory.py | MemoryItem, MemoryItemCreate, MemoryItemRead, MemorySearchRequest |
| signal.py | Signal, SignalCreate, SignalRead |
| pattern.py | Pattern, PatternCreate, PatternRead |
| governance.py | Policy, AuditLog, ComplianceCheck |
| music_trend.py | MusicTrend, MusicTrendCreate, MusicTrendRead |
| scraping.py | ScrapedItem, ViralDNA, GeneratedAsset |
| niche_account_map.py | NicheAccountMap |

### 4.5 Services (`backend/app/services/`)
| Service | Role |
|---------|------|
| topic_service | Topic from RSS, topic list, or LLM generation |
| script_service | LLM script (hook, body, CTA) with niche prompts |
| script_storage | Save scripts under data/scripts/{niche}/{date}/{time}_{job_id}_{topic}/ |
| tts_service | XTTS (local) or ElevenLabs |
| subtitle_service | Whisper / faster-whisper, SRT/ASS |
| visual_service | Stock B-roll, music, logos, fonts |
| render_service | FFmpeg compositing (audio, subtitles, logo, music → 1080×1920) |
| ltx_service | LTX-2 video generation (direct API or ComfyUI) |
| remotion_service | Remotion-based rendering (optional) |
| studio_service | Script → visual cues → scenes (e.g. for Remotion) |
| publish_service | YouTube, Instagram, TikTok official APIs |
| analytics_service | Performance metrics, top/underperforming videos |
| scheduler_service | Content scheduler (APScheduler) for generation/publish by niche |
| niche_sync_service | Sync niches DB ↔ disk (data/niches, config, feeds, topics) |
| scraper_service | Scrape trends (ytsearch), articles (trafilatura, etc.) |
| trend_hunter_service | MCP get_trending_topics → scraper → LLM fallback; generate_autonomous_job (Ollama JSON) |
| trend_service | Trend CRUD and analysis |
| cleanup_service | Storage cleanup, retention |
| deduplication_service | Content deduplication |
| growth_engine_service | 70/30 growth (templates vs experiments) |
| prompt_intelligence_service | Prompt bundles, storyboard from job |
| governance_service | Compliance checks |
| pattern_service, signal_service, memory_service | Patterns, signals, memory |
| mcp_service, mcp_publisher | MCP tool calls and publishing |

### 4.6 Workers
- **job_worker.py:** AsyncIOScheduler; `_process_pending_jobs` (PENDING, no scheduled_at) and `_process_scheduled_jobs` (PENDING, scheduled_at ≤ now). Calls `run_job_now(job_id)` → topic → script → TTS → subtitles → render → save video; updates status and WebSocket.
- **trend_hunter_worker.py:** Used by `launch_autonomous.py`; runs trend hunt per niche and `generate_autonomous_job` (Ollama → Job with topic, script, visual_prompts).

### 4.7 Backend files (app only, excluding LTX-2/LTX-Video)
- **api:** 25 router modules (niches, accounts, jobs, videos, analytics, generator, settings, models, scripts, export, mcp, scraper, publisher, cleanup, trends, promptpack, memory, signals, patterns, governance, prompt_intelligence, diagnostics, voice, compat).
- **core:** config.py, websockets.py, platforms.py.
- **db:** database.py, migrations.py.
- **models:** 16+ model modules (see §4.4).
- **services:** 27 service modules (see §4.5).
- **workers:** job_worker.py, trend_hunter_worker.py.
- **templates:** JSON prompt templates.
- **utils:** helpers.

---

## 5. Frontend – Full Structure & Report

### 5.1 Stack
- **Build:** Vite.
- **UI:** React 18, React Router, Tailwind CSS, Lucide React, Recharts, axios, date-fns.
- **Entry:** `frontend/src/main.jsx` (BrowserRouter → App). API: `src/api.js` (axios, baseURL `/api`).

### 5.2 Routes (`frontend/src/App.jsx`)
| Path | Page component | Purpose |
|------|----------------|--------|
| `/` | Overview | Today’s jobs, success/fail stats, scheduled runs |
| `/platforms` | Platforms | Platform-level view |
| `/niches` | Niches | Create/edit niches, AI settings |
| `/accounts` | Accounts | Platform connections |
| `/generator` | Generator | Generate topic/script/video, preview, approve |
| `/scrape` | Scrape | Scraping, topic ingestion |
| `/viral-lab` | ViralLab | Viral/trend experiments |
| `/queue` | Queue | Job list, retry, logs |
| `/library` | Library | Video outputs, metadata, preview |
| `/scripts` | Scripts | Scripts by date/niche |
| `/analytics` | Analytics | Metrics, trends, top/underperforming |
| `/models` | Models | Ollama model download/management |
| `/doctor` | PipelineDoctor | Pipeline health, diagnostics, fix |
| `/settings` | Settings | Paths, models, services status |

### 5.3 Components
- **Layout** – Shell + nav.
- **Card, Button, Modal** – UI primitives.
- **VideoPlayer, MobilePreview** – Video preview.
- **StatusBadge** – Job/video status.
- **ActiveJobsBar** – Active jobs indicator.

### 5.4 Frontend file list (src)
- **pages:** Overview, Platforms, Niches, Accounts, Generator, Scrape, ViralLab, Queue, Library, Scripts, Analytics, Models, PipelineDoctor, Settings (14 pages).
- **components:** Layout, Card, Button, Modal, VideoPlayer, MobilePreview, StatusBadge, ActiveJobsBar (8).
- **Root:** main.jsx, App.jsx, index.css, api.js.

---

## 6. Workflow – End-to-End

### 6.1 Content pipeline (per job)
1. **Topic** – From RSS (data/niches/{niche}/feeds.json), topic list (topics.json), or LLM.
2. **Script** – LLM (Ollama/HF Router/MCP) with niche prompt_hook, prompt_body, prompt_cta → full script; saved under data/scripts/{niche}/{date}/{time}_{job_id}_{topic}/.
3. **TTS** – XTTS or ElevenLabs → narration.wav.
4. **Subtitles** – Whisper/faster-whisper → SRT/ASS.
5. **Video** – LTX-2 (optional) or FFmpeg (stock B-roll + audio + subtitles + logo + music) → 1080×1920.
6. **Review** – User previews in dashboard; approve or reject.
7. **Publish** – YouTube / Instagram / TikTok via official APIs.
8. **Analytics** – Views, engagement, tracked in DB.

### 6.2 Automation flow
- **Scheduler:** Content scheduler (APScheduler) creates/schedules jobs per niche (posts_per_day, posting_schedule).
- **Job worker:** Polls pending/scheduled jobs; runs `run_job_now` → pipeline steps; sets status READY_FOR_REVIEW or FAILED.
- **Trend hunter:** For each active niche, fetches trends (MCP → scraper → LLM); creates one autonomous job per cycle via Ollama (topic, script, visual_prompts).
- **Manual:** User must approve before publish; optional topic/script override.

### 6.3 Data flow (summary)
```
User or Scheduler → Create Job (topic optional)
  → Job Worker: Topic → Script → TTS → Subtitles → Video → Save to Library
  → Status: READY_FOR_REVIEW
  → User reviews in Dashboard
  → User approves → Publish (YouTube/Instagram/TikTok)
  → Status: PUBLISHED → Analytics
```

---

## 7. Pipelines (CI/CD, Docker, Scripts)

### 7.1 Application pipeline
- The “content pipeline” is the 8-step flow in §6.1; see PIPELINE.md for diagrams.

### 7.2 CI/CD
- **Repo root:** No GitHub Actions or Jenkins.
- **LTX-Video:** `backend/LTX-Video/.github/workflows/pylint.yml` – on push: Ruff + Black (Python 3.10).

### 7.3 Docker
- No project-level Dockerfile or docker-compose.

### 7.4 Local / ops scripts
- **launch.bat** – Stop processes on ports, venv, install backend + Crawl4AI + Playwright, frontend + Remotion; start backend, frontend, XTTS, `launch_autonomous.py`; open browser.
- **install.bat, run.bat, setup_models.bat, setup_env.bat, setup_ffmpeg.bat, start_ollama.bat, start_xtts.bat, kill_all.bat**
- **run_daena_job.py** – Pick niche, POST /api/generator/video.
- **backend/run_job_manual.py** – run_job_now(job_id).
- **backend/launch_autonomous.py** – Job worker + trend hunter loop.
- **check_job.py, check_jobs.py, reset_job.py, fix_perms.py, create_niche.py, setup_all_models.py, download_models.py**

---

## 8. Summary Tables

### Tech stack
| Layer | Backend | Frontend |
|-------|---------|----------|
| Runtime | Python 3.11 | Node 18+ |
| Framework | FastAPI | Vite, React 18 |
| State/DB | SQLModel, SQLite | — |
| Config | Pydantic Settings, .env | — |
| Scheduler | APScheduler | — |
| HTTP | httpx | axios |
| Logging | loguru | — |
| UI | — | Tailwind, Lucide, Recharts |

### AI / external
| Component | Options |
|-----------|--------|
| LLM | Ollama (local), HF Router, MCP |
| TTS | XTTS (local), ElevenLabs |
| STT | faster-whisper |
| Video gen | LTX-2 (local/ComfyUI), FFmpeg compositing |
| Publish | YouTube Data API, Instagram Graph API, TikTok Content Posting API |

---

## 9. Quick Start / How to Run

| Goal | Command / action |
|------|-------------------|
| **Install** | Run `install.bat` (venv, backend deps, frontend deps, .env). |
| **Models** | Run `setup_models.bat` (Ollama, pull default models, seed niches). |
| **Backend only** | `cd backend` → `python -m app.main` (or `uvicorn app.main:app --reload`). Default: http://127.0.0.1:8100 |
| **Frontend only** | `cd frontend` → `npm run dev`. Proxy `/api` to backend (e.g. 8100). |
| **Full stack (simple)** | `run.bat` (backend + frontend, opens dashboard). |
| **Full stack + automation** | `launch.bat` (backend, frontend, XTTS, `launch_autonomous.py`). |
| **One manual job** | `cd backend` → `python run_job_manual.py <job_id>`. |
| **Trigger generator** | `python run_daena_job.py` (picks niche, POSTs `/api/generator/video`). |
| **API docs** | http://127.0.0.1:8100/docs (when backend is running). |
| **Dashboard** | http://localhost:3000 or port shown by Vite (when frontend is running). |

**Required:** Python 3.11, Node 18+, FFmpeg. Optional: Ollama, XTTS server, MCP servers for trends.

---

## 10. Next Steps & Roadmap

### Done (recent)
- **Trend hunter:** Safe parsing of LLM response (strip markdown, default `topic`/`script`/`visual_prompts` so missing keys don’t crash).
- **YouTube trends:** Scraper now uses `ytsearch` (niche query) instead of unsupported `/feed/trending`; fallback works when MCP is down.
- **MCP trend calls:** Retries with backoff (3 attempts, 2s delay) for xpoz and youtube_data before falling back to scraper/LLM.
- **Docs:** Full codebase audit and report in `docs/2026-02-26/CODEBASE_REPORT.md`; env vars (§11) and troubleshooting (§12) added.

### Short term (stability & ops)
- Optional circuit breaker for MCP trend sources (skip repeated failures for a cooldown window).
- Validate and normalize LLM JSON (topic, script, visual_prompts) in one place; log malformed responses.
- Pipeline Doctor: add checks for XTTS, Whisper, LTX, FFmpeg; surface in dashboard.
- Optional: root-level GitHub Actions (lint, test backend) and/or Dockerfile for backend.

### Medium term (quality & automation)
- 70/30 growth engine: wire template selection to analytics (e.g. top videos by template).
- Per-niche model tuning: document and expose in UI (LLM temp, Whisper model, TTS voice).
- Platform export: ensure encoding/aspect-ratio presets per platform; validate before publish.
- Governance: run compliance check before publish; block or warn from dashboard.

### Longer term (optional)
- LTX-2 local: document FP8/distilled setup for 8GB VRAM; optional ComfyUI workflow.
- Remotion: optional path for narrative/storyboard-driven clips.
- Dashboard: autopilot toggle, retention/cleanup config, more diagnostics and logs.

---

## 11. Environment Variables (Key)

Set in `backend/.env`. Only the main ones are listed; see `GET /api/settings/env-template` for a full template.

| Category | Variable | Example / note |
|----------|----------|----------------|
| **App** | `API_PORT` | 8100 |
| **Paths** | `BASE_PATH`, `DATA_PATH`, `MODELS_PATH` | Project and model root |
| **DB** | `DATABASE_URL` | SQLite path |
| **LLM** | `LLM_PROVIDER` | ollama \| hf_router \| mcp |
| **Ollama** | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_REASONING_MODEL` | For script + autonomous job |
| **HF Router** | `HF_ROUTER_BASE_URL`, `HF_TOKEN`, `HF_ROUTER_REASONING_LEVEL` | When LLM_PROVIDER=hf_router |
| **TTS** | `TTS_PROVIDER` | xtts \| elevenlabs |
| **XTTS** | `XTTS_SERVER_URL`, `XTTS_LANGUAGE` | e.g. http://localhost:8020 |
| **ElevenLabs** | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Fallback TTS |
| **Whisper** | `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE` | base, cuda, float16 |
| **Video** | `VIDEO_GEN_PROVIDER` | ffmpeg \| ltx |
| **LTX** | `LTX_API_URL`, `LTX_MODEL_PATH` | ComfyUI or direct API |
| **Worker** | `WORKER_ENABLED`, `WORKER_INTERVAL_SECONDS` | true, 60 |
| **MCP** | `MCP_ENABLED`, `MCP_DEFAULT_TIMEOUT` | true, 60 |
| **MCP trend** | `XPOZ_MCP_URL`, `YOUTUBE_MCP_URL` | e.g. localhost:8200, :8300 |
| **Publish** | `YOUTUBE_*`, `INSTAGRAM_*`, `TIKTOK_*` | OAuth / API keys per platform |

---

## 12. Troubleshooting

| Issue | What to check |
|-------|----------------|
| **Backend won’t start** | Python 3.11 in path; `cd backend` and run from project root; `.env` and `DATA_PATH`/`MODELS_PATH` correct; port 8100 free. |
| **Ollama not found** | Install Ollama; run `ollama serve`; set `OLLAMA_BASE_URL` if not default. |
| **“visual_prompts” / job crash** | Fixed: trend hunter now uses safe defaults when LLM omits keys; ensure backend is up to date. |
| **YouTube trends fail** | Scraper uses `ytsearch`; if MCP used, ensure xpoz/youtube_data MCP servers are running on configured URLs; check logs for “Falling back to internal scraper” or “LLM”. |
| **MCP “All connection attempts failed”** | MCP servers (xpoz, youtube_data) not running or wrong URL; increase `MCP_DEFAULT_TIMEOUT`; trend hunter now retries MCP calls before fallback. |
| **XTTS / TTS fails** | XTTS server running at `XTTS_SERVER_URL`; or set `TTS_PROVIDER=elevenlabs` and provide `ELEVENLABS_API_KEY`. |
| **Whisper OOM** | Set `WHISPER_DEVICE=cpu` or use smaller `WHISPER_MODEL` (e.g. tiny, base). |
| **FFmpeg not found** | Install FFmpeg; add to PATH or set `FFMPEG_PATH`/`FFPROBE_PATH` in .env. |
| **Frontend can’t reach API** | Configure Vite proxy to backend (e.g. 8100); CORS allows frontend origin (main.py). |
| **No jobs running** | `WORKER_ENABLED=true`; use `launch.bat` or start job worker with backend; check Queue page and job status. |

---

## 13. References

- **README:** `contentops-core/README.md`
- **Pipeline:** `contentops-core/PIPELINE.md`
- **Backend entry:** `backend/app/main.py`
- **API wiring:** `backend/app/api/__init__.py`
- **Frontend routes:** `frontend/src/App.jsx`
- **API client:** `frontend/src/api.js`

---

*Full audit and report generated 2026-02-26. Use this document for onboarding, planning, and what we are going to build/update.*
