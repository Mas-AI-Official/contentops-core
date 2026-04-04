# BUILD_SEQUENCE.md — Ordered Build Instructions for Claude Code

> This is the single source of truth for what to build next.
> Claude Code: after each step, check it off and verify with a real test before moving forward.
> Never jump ahead. Never skip verification.

---

## CURRENT BUILD POSITION
```
Step: 0 (Not started)
Last completed: None
Last verified: None
Next step: Step 1
```

---

## PHASE 1: FOUNDATION (Steps 1–5)
*Goal: Get one real video produced end-to-end. No polish. Just working.*

### Step 1: Environment Setup
```
[ ] Create directory structure (mkdir -p src/agents src/video/remotion data/... tenants/mas-ai intelligence)
[ ] Create requirements.txt with all Python dependencies
[ ] Create .env.template with all required env vars
[ ] Create config/settings.py with env loading
[ ] Verify: python -c "import all_dependencies" runs without error
```

**requirements.txt must include:**
```
# Core
fastapi uvicorn python-dotenv pydantic apscheduler

# Intelligence / scraping
yt-dlp playwright whisper faster-whisper requests beautifulsoup4

# AI / LLM
anthropic openai  

# Voice
elevenlabs kokoro-onnx soundfile

# Video
ffmpeg-python Pillow

# Data
sqlalchemy alembic sqlite3

# Utils
aiohttp asyncio loguru rich click
```

**Verify:** `pip install -r requirements.txt && python -c "import fastapi, anthropic, elevenlabs, yt_dlp"`

---

### Step 2: Tool Manager (P0 — runs before everything)
```
[ ] Build src/agents/tool_manager.py (full implementation from TOOL_MANAGEMENT.md)
[ ] Test: python src/agents/tool_manager.py --status (should show all tools as idle)
[ ] Test: python -c "from src.agents.tool_manager import ToolManager; tm = ToolManager(); tm.activate(['ollama']); print(tm.status())"
```

---

### Step 3: Script Maestro — The Core Problem
*This is the most important component. The messy-script problem lives here.*

```
[ ] Build src/agents/script_maestro.py with full 4-stage pipeline
[ ] Stage S1: extract_insight() using Ollama (qwen2.5:7b)
[ ] Stage S2: generate_hook_variants() using Hook Vault + Ollama
[ ] Stage S3: build_5act_structure() using Ollama + platform template
[ ] Stage S4: quality_check() using Claude Haiku API
[ ] Build intelligence/hook_vault.json with 10 seed hooks from VIRAL_INTELLIGENCE.md
[ ] Test: python src/agents/script_maestro.py --topic "Claude vs GPT-4o comparison" --platform tiktok
[ ] Verify: output script must have score ≥ 7.0 and clear 5 acts
```

**Test input:**
```bash
python -c "
import asyncio
from src.agents.script_maestro import ScriptMaestro
sm = ScriptMaestro()
result = asyncio.run(sm.create_script('Claude AI just released a new reasoning model. It beats GPT-4o on coding benchmarks by 23%.', 'tiktok'))
print(result)
assert result['quality_score'] >= 7.0, 'Script failed quality gate'
print('✅ Script Maestro working')
"
```

---

### Step 4: Voice Generation
```
[ ] Build src/agents/avatar_engine.py — voice module only (no animation yet)
[ ] Implement generate_voice_free() using Kokoro TTS
[ ] Implement generate_voice() using ElevenLabs API
[ ] Build voice mode selection logic
[ ] Test: python src/agents/avatar_engine.py --script-id {script_id} --mode test
[ ] Verify: data/audio/{script_id}.wav exists and plays correctly (approx 30-60s)
```

**Kokoro install:**
```bash
pip install kokoro-onnx soundfile numpy
# Download model
python -c "from huggingface_hub import hf_hub_download; hf_hub_download('hexgrad/Kokoro-82M', 'kokoro-v0_19.onnx', local_dir='models')"
python -c "from huggingface_hub import hf_hub_download; hf_hub_download('hexgrad/Kokoro-82M', 'voices.bin', local_dir='models')"
```

---

### Step 5: SadTalker / MuseTalk Integration
```
[ ] Clone MuseTalk to D:\contentops\models\MuseTalk\ (or use Codex CLI for this task)
[ ] Build avatar animation function in avatar_engine.py
[ ] Build outfit selector using mood → avatar image mapping
[ ] Place Daena avatar images in tenants/mas-ai/avatars/
[ ] Test: full pipeline — script → audio → avatar video
[ ] Verify: data/videos/{script_id}_avatar.mp4 plays and lip sync looks correct
```

**MuseTalk install (use Codex for this):**
```bash
codex "Write a shell script that clones MuseTalk from GitHub, creates a conda environment musetalk with python 3.10, installs requirements.txt, and downloads the required model weights from HuggingFace"
```

---

## PHASE 2: VIDEO PRODUCTION (Steps 6–8)
*Goal: Full production-quality video output*

### Step 6: Remotion Video Composer
```
[ ] Initialize Remotion project in src/video/remotion/
[ ] Build TikTokShort.tsx composition (from VIDEO_PRODUCTION.md)
[ ] Build components: AvatarOverlay, CaptionBurner, HookText, BRollLayer, ProgressBar
[ ] Build caption_generator.py (Whisper word timestamps → Remotion data)
[ ] Build broll_fetcher.py (Pexels API)
[ ] Build music_selector.py
[ ] Build video_composer.py orchestrator
[ ] Test: render one full TikTok video with avatar + captions + B-roll
[ ] Verify: output is 1080x1920, H.264, ~60s, all layers present
```

**Remotion test command:**
```bash
# In src/video/remotion/
npx remotion render src/index.ts TikTokShort out/test.mp4 \
  --props='{"avatarVideoPath": "test.mp4", "hookText": "Test hook", "captions": []}' \
  --width=1080 --height=1920
```

---

### Step 7: Dashboard Backend (FastAPI)
```
[ ] Build src/api/dashboard.py with routes:
    GET  /api/status          → agent + tool status
    GET  /api/queue           → current content queue
    GET  /api/analytics       → performance metrics
    GET  /api/hooks           → Hook Vault contents
    POST /api/idea            → operator drops an idea
    POST /api/pipeline/run    → trigger pipeline for tenant
    GET  /api/tenant/{id}     → tenant info
[ ] Build simple React dashboard (src/dashboard/)
[ ] Start: uvicorn src.api.dashboard:app --reload --port 8080
[ ] Verify: http://localhost:8080/docs shows all routes
```

---

### Step 8: VirAI Scout
```
[ ] Build src/agents/virai_scout.py
[ ] Implement fetch_top_videos() using YouTube Data API (free tier)
[ ] Implement transcribe_all() using Faster-Whisper
[ ] Implement analyze_viral_patterns() using Gemini CLI
[ ] Implement update_hook_vault()
[ ] Test: python src/agents/virai_scout.py --niche ai-tech --count 3
[ ] Verify: 3+ new entries in intelligence/hook_vault.json
```

---

## PHASE 3: DISTRIBUTION + ANALYTICS (Steps 9–11)

### Step 9: Distribution Engine
```
[ ] Build src/agents/distributor.py
[ ] Implement platform-specific formatting for each platform
[ ] Implement optimal time scheduler using APScheduler
[ ] Start with TikTok + YouTube (most important for Daena)
[ ] Build post metadata generator (captions, hashtags, titles)
[ ] Test with a real post to MAS-AI TikTok
[ ] Verify: post appears with correct caption, hashtags, formatting
```

---

### Step 10: Analytics Hawk
```
[ ] Build src/agents/analytics_hawk.py
[ ] Connect to platform analytics APIs
[ ] Implement metric normalization (different platforms have different fields)
[ ] Implement viral signal detection (>10K views in 6h)
[ ] Connect to method_scores.json updates
[ ] Verify: after 24h, can see real metrics for posted videos
```

---

### Step 11: Method Optimizer
```
[ ] Build src/agents/method_optimizer.py
[ ] Implement method scoring with minimum 5 data points
[ ] Implement promotion/retirement logic from PIPELINE.md
[ ] Implement daily report generation
[ ] Schedule: daily at 02:00 using APScheduler
[ ] Test: manually run optimizer, verify method_scores.json updates
```

---

## PHASE 4: AUTONOMY + POLISH (Steps 12–15)

### Step 12: Full Pipeline Orchestrator
```
[ ] Build scripts/run_full_pipeline.py
[ ] Wire all agents together in correct order
[ ] Add error handling and retry logic at each stage
[ ] Add operator notification on failure
[ ] Test: "full run" on one topic from start to published post
[ ] Verify: one full video published to TikTok with zero manual intervention
```

---

### Step 13: Multi-tenant Support
```
[ ] Add tenant isolation to all agents
[ ] Build tenant onboarding flow
[ ] Test: create client-001 tenant with different niche
[ ] Verify: content never bleeds between tenants
```

---

### Step 14: Dashboard Frontend Polish
```
[ ] Complete React dashboard with all panels from AGENTS.md
[ ] Add real-time viral alerts (WebSocket)
[ ] Add method scoreboard visualization
[ ] Add idea drop interface
[ ] Verify: Masoud can open dashboard and see full system status
```

---

### Step 15: Phase 2 Avatar (Stretch)
```
[ ] Evaluate MuseTalk quality vs SadTalker on RTX 4060
[ ] Research LivePortrait for full-body (Phase 2)
[ ] Build outfit/wardrobe variation system
[ ] If budget allows: evaluate cloud GPU for Wan2.2 (Phase 3 digital human)
```

---

## ISSUES.md TEMPLATE

```markdown
# ISSUES.md — Known Blockers and Issues

## OPEN ISSUES

| ID | Component | Issue | Impact | Workaround | Status |
|----|-----------|-------|--------|------------|--------|
| I001 | | | | | Open |

## RESOLVED ISSUES

| ID | Component | Issue | Resolution | Date |
|----|-----------|-------|------------|------|
```

---

## OPERATOR ONBOARDING CHECKLIST

Before first production run, Masoud must:
```
[ ] Add Daena avatar images to tenants/mas-ai/avatars/ (5 variants)
[ ] Set ELEVENLABS_API_KEY in .env
[ ] Set DAENA_VOICE_ID in .env (create Daena voice in ElevenLabs first)
[ ] Set PEXELS_API_KEY in .env (free at pexels.com/api)
[ ] Set YouTube Data API key in .env
[ ] Connect TikTok, IG, YouTube, LinkedIn, X accounts
[ ] Verify Ollama is running with qwen2.5:7b installed
[ ] Verify MuseTalk or SadTalker works on RTX 4060
[ ] Set ANTHROPIC_API_KEY for QA gates
[ ] Run: python scripts/setup_verify.py (checks all dependencies)
```
