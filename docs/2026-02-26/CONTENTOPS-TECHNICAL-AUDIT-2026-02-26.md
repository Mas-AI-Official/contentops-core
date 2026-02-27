# Content OPS – Technical Audit Report  
**Date:** 2026-02-26  
**Scope:** contentops-core codebase  
**Role:** Lead Enterprise System Architect  
**Target Vision:** 24/7 autonomous “AI Influencer Machine” (scrape → LLM scripts → LTX video → watermark → auto-publish)

---

## Executive Summary

The codebase is a **manual-generation dashboard with a partial backend**: Niches and Accounts have full DB + API; Scrape has a capable service layer but the **Scrape tab calls API routes that do not exist**, so the UI is partially broken. The generation pipeline runs in a **background task + DB poll** model; the frontend uses **HTTP polling every 2s** for status. The pipeline has **no timeout on Remotion**, **no explicit unload of the text LLM before loading the 25GB LTX model**, and **sequential processing** that can stall at script → audio → LTX → Remotion. Together, this explains the “55% stall” and the gap between the current manual flow and a headless autonomous engine.

**Critical findings:**

1. **Architecture gap:** Scrape frontend expects 6 routes that are not implemented; topic-from-scrape exists in the generator via `source=rss` but is not wired from the Scrape tab; Niches/Accounts are real (DB + API).
2. **55% stall:** Remotion subprocess has no timeout; LTX direct Python path blocks in executor with no upper bound; script phase uses 120s HTTP timeout; no explicit Ollama unload before LTX; single job blocks the worker.
3. **Publishing:** Hybrid REST + MCP (YouTube/X use MCP when `mcp_enabled=True`; Instagram/TikTok are REST only). MCP is the right direction for X/YouTube to reduce API key and shadowban surface.
4. **Roadmap:** Implement missing scraper routes, connect Scrape → topic picker → generator; add Remotion/LTX timeouts and optional job queue; unload Ollama before LTX; move frontend to WebSocket for progress; then harden MCP publishing and headless scheduler.

---

## 1. The Architecture Gap

### 1.1 What Exists Today

| Module    | Backend logic | DB/Storage | API routes | Frontend | Verdict |
|----------|----------------|------------|------------|----------|---------|
| **Niches** | Full: CRUD, generate-topics, automate, trigger-generation, platform stats | `Niche` model, niche_sync, disk niches_path | `/api/niches/*` (list, get, create, patch, delete, generate-topics, automate, bulk-automate, smart-schedule, trigger-generation, platforms/stats, toggle-auto-mode) | Tabs call real APIs | **Real** |
| **Accounts** | Full: CRUD, status, verify, link/unlink niche | `Account`, `NicheAccountMap` | `/api/accounts/*` | Tabs call real APIs | **Real** |
| **Platforms** | Config in `core/platforms.py`; stats/trigger via Niches API | Niche.platform, platform configs | Via `/api/niches/platforms/stats`, trigger-generation | Platforms tab uses niches + trigger | **Real** |
| **Scrape** | Service: RSS/feeds, file-based topics, get_unused_topic, seed_niche_feeds, scrape_niche, yt-dlp/trafilatura/Crawl4AI | File-based `feeds.json`, `scraped_topics.json`; DB `ScrapedItem`, `ViralDNA` for ingest/analyze | `/api/scraper/ingest`, `/analyze/{id}`, `/items`, `/viral-dna`, `/run` only | Scrape tab calls **different** routes (see below) | **Gap** |

### 1.2 The Scrape Frontend–Backend Mismatch

**Frontend** (`frontend/src/api.js` lines 112–118) calls:

- `POST /scraper/scrape` (body)
- `POST /scraper/scrape/{slug}?force=...`
- `GET /scraper/topics/{slug}?unused_only=...`
- `GET /scraper/feeds/{slug}`
- `PUT /scraper/feeds/{slug}` (body: `{ feeds }`)
- `POST /scraper/seed-feeds/{slug}`
- `POST /scraper/pick-topic/{slug}`

**Backend** (`backend/app/api/scraper.py`) implements only:

- `POST /scraper/ingest` (URL + optional content)
- `POST /scraper/analyze/{item_id}`
- `GET /scraper/items`
- `GET /scraper/viral-dna`
- `POST /scraper/run` (placeholder, returns empty data)

So the Scrape tab will **404 or fail** for: `/scraper/scrape`, `/scraper/scrape/{slug}`, `/scraper/topics/{slug}`, `/scraper/feeds/{slug}`, `/scraper/seed-feeds/{slug}`, `/scraper/pick-topic/{slug}`.

The **data and logic exist** in `scraper_service.py`:

- `seed_niche_feeds(niche_slug, niche_name)` (lines 54–72)
- `update_niche_feeds(niche_slug, feed_urls)` (74–81)
- `scrape_niche(niche_slug)` async (84–113)
- `get_unused_topic(niche_slug)` (129–139)
- `mark_topic_used(niche_slug, topic_id)` (141–154)
- File layout: `settings.data_path / "feeds.json"`, `"scraped_topics.json"`

### 1.3 Connecting Scrape Data to the LLM (Bypassing Manual Input)

**Already working for “topic” only:** The generator can use scraped topics without the Scrape tab.

- **Generator API** (`backend/app/api/generator.py`):  
  `POST /generator/topic?niche_id=...&source=rss` (lines 65–79) calls `scraper_service.get_unused_topic(niche_slug)` and returns that topic (or falls back to LLM).
- **Frontend Generator** (`frontend/src/pages/Generator.jsx`): The “RSS” button calls `generateTopic(selectedNiche.id, 'rss')` (line 274), so **topic** from scrape is already connected when the user picks “RSS” in the Generator.

What’s missing to fully “bypass the manual input screen”:

1. **Scrape tab → one-click “Use this in Generator”**  
   - Either: Scrape tab has a “Pick for video” that calls an API that returns a topic (e.g. `POST /scraper/pick-topic/{slug}`) and then the frontend can navigate to Generator with that topic pre-filled, **or**  
   - Backend implements `GET /scraper/topics/{slug}?unused_only=true` and `POST /scraper/pick-topic/{slug}` so the Scrape tab can show topics and “send to generator” (e.g. store selected topic in job or pass as query param).

2. **Headless/autonomous flow**  
   - Scheduler or worker should be able to: for a niche → `scraper_service.get_unused_topic(slug)` → create job with that topic → run job (script from topic via existing `script_service.generate_with_niche_config`). No manual screen needed.

So: **backend** needs the **missing scraper routes** so the Scrape tab works and so any client (including a headless scheduler) can list topics, pick one, and feed it into the generator. The “connect Scrape to LLM” is already there for **topic**; the gap is exposing it via the Scrape API and optionally pre-filling or auto-creating jobs from picked topics.

---

## 2. The 55% Stall Bug – Generation Pipeline Analysis

### 2.1 Pipeline Flow (Where 55% Likely Stalls)

End-to-end flow:

1. **Trigger**  
   - `POST /api/generator/video` creates a `Job`, then `BackgroundTasks.add_task(run_job_now, job.id)` (generator.py lines 159–161).  
   - So the HTTP request returns immediately with `job_id`; the actual work runs in the same process via `run_job_now` → `job_worker._process_job`.

2. **Job worker** (`backend/app/workers/job_worker.py`)  
   - `_process_job` runs sequentially: script → audio → subtitles → **LTX video assets** → **Remotion** → thumbnail → (optional) publish.  
   - Progress steps: 10% (script), 50% (subtitles), 70% (LTX), then Remotion (no % update until done), then 90% (publish).  
   - So **~55%** is right after subtitles (50%) and at the start of LTX (70%). The stall is most likely in **LTX** or **Remotion**, or in the **script** phase if the LLM is slow.

3. **Script** (`script_service.generate_with_niche_config`)  
   - Uses Ollama (or HF Router / MCP) with **120s** timeout (`script_service.py` e.g. lines 208, 239, 266).  
   - Ollama request uses `"keep_alive": 0` so the model is unloaded after the request.  
   - So script phase is bounded by 120s per call; multiple calls (reasoning, writer, judge/visuals) can add up.

4. **Audio**  
   - `studio_service.generate_audio` → `tts_service.generate_audio` (XTTS/ElevenLabs).  
   - After audio, `studio_service.unload_gpu()` is called (studio_service.py lines 71–72).  
   - So **TTS is unloaded before LTX**.

5. **LTX video assets** (`studio_service.generate_video_assets`)  
   - For each scene, `ltx_service.generate_video_from_text(...)` is called.  
   - **Direct Python path:** `_generate_direct` runs `_run_ltx_inference` in `loop.run_in_executor(None, ...)` (ltx_service.py lines 184–199). There is **no timeout** on this executor call. A 25GB model can take minutes per clip; the main thread waits indefinitely.  
   - **ComfyUI path:** `_queue_prompt` uses **30s** timeout (line 377); `_wait_and_download` polls with **max_wait = 600** (10 min) and **check_interval = 5** (lines 405–406). So ComfyUI path is bounded; direct Python is not.  
   - After each clip, `studio_service.unload_gpu()` is called (studio_service.py line 184).  
   - **Ollama (text LLM)** is not explicitly unloaded by the app; it’s managed by Ollama with `keep_alive: 0`. If the user or another process has loaded a large model, **VRAM contention** with LTX can cause OOM or extreme slowness. The app does not call an “unload” endpoint for Ollama before LTX.

6. **Remotion** (`remotion_service.render_promo`)  
   - `asyncio.create_subprocess_shell(...)` then `await process.communicate()` (remotion_service.py lines 44–51).  
   - **No timeout** is passed to `communicate()`. If Remotion hangs (e.g. missing Node/npx, bad props, or render bug), the worker hangs forever.  
   - This is a **primary stall risk** after LTX completes (e.g. user sees ~70% then nothing).

7. **Publish**  
   - `publish_service.publish` uses httpx with **600s** timeout for uploads (documented in explore summary).  
   - Less likely to cause a 55% stall (publish is at 90%).

### 2.2 “Spawn-All-Wait” and Blocking Points

- **Remotion:** One subprocess, wait with `communicate()` and no timeout → **classic “spawn and wait forever”**.  
- **LTX direct:** One long-running `run_in_executor` per clip with no timeout → **blocking wait**.  
- **Worker:** Only one job is processed per poll (up to `max_concurrent_jobs`); one stuck job blocks others until it fails or completes.  
- **Frontend:** Uses **HTTP polling** every **2 seconds** for `GET /generator/status/{jobId}` (Generator.jsx lines 188–209). The request itself does not stall the backend, but if the backend worker is stuck in Remotion or LTX, status never reaches `ready_for_review` and the UI appears to “hang” at ~55% (or 70%).

### 2.3 Timeouts Summary

| Component        | Timeout | Location |
|-----------------|--------|----------|
| Script (Ollama) | 120s   | script_service.py (httpx.AsyncClient(timeout=120.0)) |
| HF Router       | 120s   | config hf_router_timeout |
| Topic (Ollama)  | 60s    | topic_service (implied) |
| TTS             | 60s/300s (API), 600s (CLI) | tts_service |
| LTX ComfyUI     | 30s (request), 600s (poll) | ltx_service |
| LTX direct      | **None** | run_in_executor, no timeout |
| Remotion        | **None** | process.communicate() |
| Publish         | 600s   | publish_service (httpx) |

### 2.4 VRAM / Model Unload

- **TTS:** Unloaded with `studio_service.unload_gpu()` after audio (and after each LTX retry).  
- **LTX:** Unloaded after each clip via `unload_gpu()`.  
- **Ollama (text LLM):** Not explicitly unloaded before LTX. The app relies on `keep_alive: 0` so that after each script request Ollama unloads the model. If script generation finishes and then LTX loads a 25GB model, VRAM can still be tight if:  
  - Ollama hasn’t yet evicted the model, or  
  - Another process (or a previous request) has loaded a large model.  
  So: **explicitly calling Ollama’s “unload” (e.g. keep_alive=0 or a dedicated unload API) before starting LTX** would make VRAM behavior more predictable.

### 2.5 Root Causes for the 55% Stall (Summary)

1. **Remotion** – No timeout on `process.communicate()`; hang there = permanent stall.  
2. **LTX direct Python** – No timeout on `run_in_executor`; long or stuck inference = stall.  
3. **VRAM** – No guaranteed Ollama unload before LTX; OOM or thrashing can cause failures or extreme slowness that looks like a stall.  
4. **Single-threaded worker** – One stuck job blocks the queue; no visibility into “which step” without logs.

---

## 3. The Publishing Pipeline

### 3.1 Current Integration Layout

- **REST (native APIs):**  
  - **YouTube:** OAuth + Data API v3 upload (when `mcp_enabled=False` or no MCP), 600s timeout.  
  - **Instagram:** Graph API (access token, business account id).  
  - **TikTok:** Upload API (client key/secret, access token; unverified → private).

- **MCP:**  
  - **X (Twitter):** `mcp_publisher.publish_to_x` → `mcp_service.call_tool(server_name="x_posting", tool_name="post_tweet", ...)` (mcp_publisher.py, publish_service.py 477–481).  
  - **YouTube:** When `settings.mcp_enabled` is True, `mcp_publisher.publish_to_youtube` → `call_tool(server_name="yutu", tool_name="upload_video", ...)` (publish_service.py 442–446).  
  - Config: `x_post_mcp_url`, `yutu_mcp_url` (e.g. mcp-x, yutu), `mcp_default_timeout=60`.

- **Choice:** In `publish_service.publish()`, YouTube and X use MCP when `settings.mcp_enabled` is True; otherwise YouTube uses native REST. Instagram and TikTok are REST-only.

### 3.2 Recommendation: REST vs MCP

- **Use MCP for posting where possible** (X, YouTube) so that:  
  - Posting is delegated to a dedicated, sandboxed agent (e.g. mcp-x, yutu).  
  - API keys and token refresh live in one place, reducing exposure and shadowban risk.  
  - You can swap or add MCP servers (e.g. Xpoz for scraping, mcp-x for X) without changing core app logic.

- **Keep REST for Instagram/TikTok** until you have MCP servers for them; then add a similar `mcp_enabled` branch for those platforms.

- **Architecture:**  
  - **Option A (current):** Single Content OPS process calls MCP servers via HTTP (e.g. `POST .../tools/call`).  
  - **Option B:** Introduce a small “publisher” service that only talks to MCP servers and is called by Content OPS (e.g. via REST or queue).  
  For a 24/7 autonomous engine, Option A is enough; Option B is useful if you want to scale posting or isolate failures.

So: **prefer MCP for X and YouTube**; add timeouts and retries for MCP calls (e.g. 60s is short for large uploads – consider platform-specific timeouts); add Instagram/TikTok via MCP when available.

---

## 4. Execution Roadmap – Prioritized Technical Checklist

Goal: Turn the codebase from a **manual generation dashboard** into a **headless, 24/7 autonomous content engine**.

### Phase 1 – Fix the Scrape Tab and Scrape → Generator Link (High)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 1.1 | Implement missing scraper API routes so Scrape tab works | **Create/modify:** `backend/app/api/scraper.py` – Add: `POST /scraper/scrape` (body: e.g. `{ niche_slug }`), `POST /scraper/scrape/{slug}`, `GET /scraper/topics/{slug}`, `GET /scraper/feeds/{slug}`, `PUT /scraper/feeds/{slug}`, `POST /scraper/seed-feeds/{slug}`, `POST /scraper/pick-topic/{slug}`. Delegate to `scraper_service` (seed_niche_feeds, update_niche_feeds, scrape_niche, get_unused_topic, mark_topic_used; for feeds read/write use existing file helpers). |
| 1.2 | Fix scraper analyze bug | **Modify:** `backend/app/api/scraper.py` – Add `from datetime import datetime` and use `datetime.utcnow()` where `item.processed_at = datetime.utcnow()` is set (line 115). |
| 1.3 | Scrape tab “Use in Generator” | **Modify:** `frontend/src/pages/Scrape.jsx` (or equivalent) – Add “Pick for video” / “Send to Generator” that calls `POST /scraper/pick-topic/{slug}` (or `GET /scraper/topics/{slug}?unused_only=true` then pick one) and navigate to Generator with topic pre-filled (e.g. state or query param). |
| 1.4 | Headless topic-from-scrape | **Modify:** Scheduler or job creation path – When creating a job for a niche in “auto” mode, call `scraper_service.get_unused_topic(niche.slug)` and set `job.topic`; then `scraper_service.mark_topic_used(niche.slug, topic_id)` when job is created or when video is approved. Ensure `content_scheduler.trigger_manual_generation` (or equivalent) can use this. |

### Phase 2 – Fix the 55% Stall (Critical)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 2.1 | Remotion timeout | **Modify:** `backend/app/services/remotion_service.py` – Use `asyncio.wait_for(process.communicate(), timeout=900)` (or config) so Remotion cannot hang indefinitely. On timeout, kill process and raise. |
| 2.2 | LTX direct timeout | **Modify:** `backend/app/services/ltx_service.py` – In `_generate_direct`, wrap `loop.run_in_executor(...)` in `asyncio.wait_for(..., timeout=600)` (or config). On timeout, cancel or leave executor to finish in background and fail the clip. |
| 2.3 | Config timeouts | **Modify:** `backend/app/core/config.py` – Add e.g. `remotion_render_timeout: float = 900`, `ltx_clip_timeout: float = 600`. Use these in remotion_service and ltx_service. |
| 2.4 | Ollama unload before LTX | **Modify:** `backend/app/services/studio_service.py` – Before `generate_video_assets`, call Ollama unload: e.g. `POST {ollama_base_url}/api/delete` with the reasoning/generator model name, or ensure keep_alive=0 was used and add a short delay. Alternatively add a small helper in script_service or a new ollama_service that triggers unload; call it from studio_service before LTX. |
| 2.5 | Progress during Remotion | **Modify:** `backend/app/workers/job_worker.py` – Before calling `remotion_service.render_promo`, set e.g. `job.progress_percent = 75` and commit; after Remotion, set 85. So the frontend does not stay at 70% for the whole Remotion run. |

### Phase 3 – Frontend: WebSocket Instead of Polling (High)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 3.1 | Generator subscribes to WebSocket | **Modify:** `frontend/src/pages/Generator.jsx` – On “Generate video”, open WebSocket to `/ws/events` (or existing event endpoint from main.py). Subscribe to `job_log` and `job_completed` for the current job_id. Update status and progress from events; reduce or remove polling interval. |
| 3.2 | Optional: fallback polling | **Modify:** `frontend/src/pages/Generator.jsx` – If WebSocket is disconnected, fall back to current 2s polling so the UI still updates. |

### Phase 4 – Background Job Queue (Optional but Recommended)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 4.1 | Introduce Redis + BullMQ (or Celery) | **Create:** Queue module (e.g. `backend/app/queue/`) – Define “video_generation” queue. Producer: when creating a job, push job_id to the queue instead of (or in addition to) `BackgroundTasks.add_task(run_job_now, job.id)`. Consumer: worker process that runs job_worker logic or calls `run_job_now`. |
| 4.2 | API returns immediately | **Modify:** `backend/app/api/generator.py` – After creating the job, enqueue job_id and return; do not run `run_job_now` in the same process. This avoids HTTP timeouts and keeps the API responsive. |
| 4.3 | Worker runs from queue | **Modify:** `backend/app/workers/job_worker.py` – Either keep current “poll DB for PENDING” or replace with “poll queue for job_id” and then run `_process_job(job_id)`. Ensure only one long-running job per worker if you have a single GPU. |

### Phase 5 – Publishing Hardening and MCP-First (Medium)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 5.1 | MCP timeouts for uploads | **Modify:** `backend/app/services/mcp_service.py` / `mcp_publisher.py` – Use a longer timeout for `upload_video` (e.g. 300s) while keeping 60s for quick tools. Consider a config key per connector. |
| 5.2 | Instagram/TikTok via MCP when available | **Modify:** `backend/app/services/publish_service.py` – When MCP servers for Instagram/TikTok exist, add branches similar to YouTube/X (if settings.mcp_instagram_enabled then mcp_publisher.publish_to_instagram, etc.). |
| 5.3 | Retries and idempotency | **Modify:** `backend/app/services/publish_service.py` – Retry once or twice on 5xx or network errors; store publish result in `VideoPublish` so duplicate triggers are idempotent. |

### Phase 6 – Headless / 24/7 Autonomous (High)

| # | Action | Files to create/modify |
|---|--------|------------------------|
| 6.1 | Scheduler uses scrape topics | **Modify:** `backend/app/services/scheduler_service.py` (or equivalent) – When creating jobs for niches (e.g. trigger_manual_generation or cron), set topic from `scraper_service.get_unused_topic(niche.slug)` and mark topic used when job is created. |
| 6.2 | Autopilot loop | **Modify:** Worker or scheduler – If `autopilot_enabled`, periodically (e.g. from scheduler) create jobs for auto_mode niches with scrape-derived topics, no manual approval step for “generate only” path. Optionally add “approve and publish” step via a separate queue or manual trigger. |
| 6.3 | Trend hunter / Xpoz | **Integrate:** If using Xpoz (or similar) for trends, add a step that pulls trending topics and merges them into scraper topics or creates jobs with that topic. Ensure one place (e.g. scraper_service or trend_hunter_service) is the source of truth for “next topic” per niche. |

---

## 5. File Reference Quick Map

| Area | Key files |
|------|-----------|
| App entry | `backend/app/main.py` |
| Config | `backend/app/core/config.py` |
| Job worker | `backend/app/workers/job_worker.py` |
| Generation pipeline | `backend/app/services/studio_service.py`, `ltx_service.py`, `remotion_service.py`, `script_service.py`, `tts_service.py`, `render_service.py` |
| Generator API | `backend/app/api/generator.py` |
| LLM / prompts | `backend/app/services/script_service.py`, `topic_service.py` |
| VRAM | `backend/app/services/studio_service.py` (`unload_gpu`) |
| Publishing | `backend/app/services/publish_service.py`, `mcp_publisher.py`, `backend/app/api/publisher.py` |
| MCP | `backend/app/services/mcp_service.py`, `backend/app/api/mcp.py` |
| Scrape / niches / accounts | `backend/app/services/scraper_service.py`, `backend/app/api/scraper.py`, `backend/app/api/niches.py`, `backend/app/api/accounts.py` |
| Frontend API + Generator | `frontend/src/api.js`, `frontend/src/pages/Generator.jsx` |
| WebSocket | `backend/app/core/websockets.py`, `main.py` (`/ws/events`) |

---

## 6. What to Expect After Implementation

- **Scrape tab** will work: seed feeds, run scrape, list topics, pick topic for generator.  
- **55% stall** should be addressed: Remotion and LTX have timeouts; optional Ollama unload before LTX reduces VRAM issues; progress updates during Remotion improve perceived progress.  
- **Frontend** will feel responsive: WebSocket-driven progress instead of blind polling.  
- **Publishing** remains MCP-first for X/YouTube with clearer timeouts and optional retries.  
- **Headless engine:** Scheduler + scrape-derived topics + queue (optional) will allow 24/7 autonomous runs without the manual Generator screen.

This audit is based on a direct read of the codebase and aligns with the architecture you described (scrape → LLM → LTX → assemble → watermark → publish). Implementing the roadmap in order (Scrape APIs → stall fixes → WebSocket → queue → publishing → headless) will close the gap between the current manual dashboard and the ultimate vision.
