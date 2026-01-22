# Content Factory - Complete Pipeline Architecture

## Visual Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CONTENT FACTORY PIPELINE                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: TOPIC GENERATION (Auto/Manual)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  RSS Feeds (data/niches/*/feeds.json)│
        │  → Fetch headlines                   │
        │  → LLM picks best story              │
        └─────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌──────────────┐          ┌──────────────────┐
│ Topic List   │          │ LLM Generation    │
│ (topics.json)│          │ (Ollama/MCP)      │
└──────────────┘          └──────────────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  TOPIC READY  │
              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: SCRIPT GENERATION                                                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  LLM Provider (Ollama or MCP)        │
        │  → Generate Hook (15 words)          │
        │  → Generate Body (45-50s speech)     │
        │  → Generate CTA (10 words)           │
        │  → Combine → Full Script              │
        └─────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────┐
        │  Save Script (organized by date)     │
        │  data/scripts/{niche}/{date}/       │
        │    {time}_{job_id}_{topic}/          │
        │      - script.json                   │
        │      - script.txt                    │
        │      - metadata.json                 │
        └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: AUDIO GENERATION (TTS)                                           │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  TTS Provider (Per-Niche Config)    │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ XTTS (Local)                  │   │
        │  │ → Voice cloning from WAV     │   │
        │  │ → Server or CLI               │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ ElevenLabs (API Fallback)     │   │
        │  │ → Voice ID selection          │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ narration.wav │
              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: SUBTITLE GENERATION                                               │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Whisper/faster-whisper             │
        │  → Transcribe audio                 │
        │  → Generate SRT/ASS                 │
        │  → Per-niche model/device config     │
        └─────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ subtitles.srt │
              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: VIDEO GENERATION (Rendering)                                     │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Video Provider Selection            │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ LTX-2 (AI Video Gen)           │   │
        │  │ → Text-to-Video from script   │   │
        │  │ → Direct Python API (fast)    │   │
        │  │ → Or ComfyUI API (fallback)    │   │
        │  │ → 480p, 3-5s (8GB VRAM limit) │   │
        │  │ → DistilledPipeline (FP8)     │   │
        │  └──────────────────────────────┘   │
        │              │                       │
        │              ▼                       │
        │  ┌──────────────────────────────┐   │
        │  │ FFmpeg (Compositing)          │   │
        │  │ → Add audio                   │   │
        │  │ → Burn subtitles              │   │
        │  │ → Add logo watermark          │   │
        │  │ → Mix background music        │   │
        │  │ → Scale to 1080x1920          │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ FFmpeg (Stock Video)          │   │
        │  │ → Use stock B-roll            │   │
        │  │ → Composite all elements      │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  FINAL VIDEO  │
              │  (1080x1920)  │
              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 6: REVIEW & APPROVAL (Manual)                                       │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Dashboard Preview                   │
        │  → Watch video                       │
        │  → Review script                     │
        │  → Approve or Reject                 │
        └─────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  APPROVED?    │
              └───────────────┘
                      │
        ┌─────────────┴─────────────┐
        │ NO                         │ YES
        ▼                           ▼
   ┌─────────┐              ┌───────────────┐
   │ REJECT  │              │ QUEUE PUBLISH │
   └─────────┘              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 7: PUBLISHING (Platform APIs)                                       │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Platform Selection                  │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ YouTube Data API              │   │
        │  │ → Upload video                │   │
        │  │ → Set title/description       │   │
        │  │ → Add tags                    │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ Instagram Graph API            │   │
        │  │ → Upload Reel                  │   │
        │  │ → Add caption/hashtags         │   │
        │  └──────────────────────────────┘   │
        │                                      │
        │  ┌──────────────────────────────┐   │
        │  │ TikTok Content Posting API     │   │
        │  │ → Upload video                │   │
        │  │ → Add description             │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  PUBLISHED   │
              │  (Tracked)   │
              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 8: ANALYTICS & TRACKING                                             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Performance Metrics                 │
        │  → Views, engagement                 │
        │  → Winner detection                  │
        │  → Daily stats by niche              │
        │  → Trends & insights                 │
        └─────────────────────────────────────┘
```

## Component Details

### 1. Topic Sources (Priority Order)
1. **RSS Feeds** (`data/niches/{niche}/feeds.json`)
   - Fetches live headlines
   - LLM ranks and picks best story
2. **Topic Lists** (`data/niches/{niche}/topics.json`)
   - Pre-defined topics
   - Tracks used topics
3. **LLM Generation** (Ollama/MCP)
   - Generates new topic ideas
   - Uses niche description

### 2. LLM Providers
- **Ollama** (default, local)
  - Models: `llama3.1:8b`, `llama3.2:3b`
  - Per-niche model selection
- **MCP** (external APIs)
  - OpenAI, Anthropic, etc.
  - Configured via `MCP_CONNECTORS_JSON`

### 3. TTS Providers
- **XTTS** (local, default)
  - Voice cloning from speaker WAV
  - Server or CLI mode
- **ElevenLabs** (API fallback)
  - Voice ID selection
  - Per-niche configuration

### 4. Video Generation Modes

#### Mode A: LTX-2 AI Generation (New!)
```
Script Text → LTX-2 Model (Direct Python API)
                         ↓
              AI Video (480p, 3-5s, FP8 quantized)
                         ↓
                    FFmpeg Composite
                         ↓
              + Audio, Subtitles, Logo, Music
                         ↓
                  Final Video (1080x1920)
             
Alternative: ComfyUI API mode (if direct API unavailable)
```

#### Mode B: FFmpeg Compositing (Default)
```
Stock Video/Color → FFmpeg
                         ↓
              + Audio, Subtitles, Logo, Music
                         ↓
                  Final Video (1080x1920)
```

### 5. Per-Niche Configuration
Each niche can override:
- **LLM Model** (e.g., `llama3.1:8b` vs `llama3.2:3b`)
- **LLM Temperature** (creativity: 0.0-2.0)
- **TTS Provider** (`xtts` or `elevenlabs`)
- **Voice ID** (ElevenLabs ID or speaker WAV path)
- **Whisper Model** (`tiny`, `base`, `small`, `medium`, `large`)
- **Whisper Device** (`cuda` or `cpu`)

### 6. Automation Flow
1. **Scheduled Jobs**: APScheduler processes queue
2. **Auto Topic**: RSS → LLM pick → Generate
3. **Auto Generate**: Script → Audio → Subtitles → Video
4. **Manual Review**: Dashboard preview required
5. **Auto Publish**: After approval, posts to selected platforms

## Data Flow

```
User Action (Generator Page)
    ↓
Create Job (topic auto-generated if not provided)
    ↓
Job Worker (APScheduler)
    ↓
┌─────────────────────────────────────┐
│ 1. Topic (RSS/List/LLM)              │
│ 2. Script (LLM with niche prompts)   │
│ 3. Audio (TTS with niche voice)      │
│ 4. Subtitles (Whisper with niche cfg)│
│ 5. Video (LTX or FFmpeg)              │
│ 6. Save to Library                    │
└─────────────────────────────────────┘
    ↓
Status: READY_FOR_REVIEW
    ↓
User Reviews in Dashboard
    ↓
User Approves
    ↓
Job Worker (Publishing)
    ↓
┌─────────────────────────────────────┐
│ Publish to YouTube/Instagram/TikTok  │
│ Track results                        │
└─────────────────────────────────────┘
    ↓
Status: PUBLISHED
    ↓
Analytics Tracking
```

## File Organization

```
D:\Ideas\content_factory\
├── data/
│   ├── niches/
│   │   └── {niche_name}/
│   │       ├── feeds.json          # RSS feeds for auto topics
│   │       └── topics.json          # Manual topic lists
│   ├── scripts/
│   │   └── {niche_name}/
│   │       └── {YYYY-MM-DD}/
│   │           └── {HH-MM-SS}_{job_id}_{topic}/
│   │               ├── script.json
│   │               ├── script.txt
│   │               └── metadata.json
│   ├── outputs/
│   │   └── {job_id}/
│   │       ├── narration.wav
│   │       ├── subtitles.srt
│   │       ├── {job_id}_final.mp4
│   │       └── thumbnail.jpg
│   └── assets/
│       ├── music/                   # Background music
│       ├── logos/                   # Watermarks
│       ├── fonts/                   # Subtitle fonts
│       └── stock/                   # B-roll videos/images
├── models/
│   ├── ollama/                      # Ollama models (if OLLAMA_MODELS set)
│   ├── whisper/                     # Whisper models
│   ├── xtts/                        # XTTS models
│   ├── torch/                       # PyTorch cache
│   ├── image/                       # Image generation models
│   └── ltx/                         # LTX video models
└── backend/
    └── app/
        ├── services/
        │   ├── topic_service.py      # RSS/LLM topic generation
        │   ├── script_service.py     # LLM script generation
        │   ├── tts_service.py        # XTTS/ElevenLabs audio
        │   ├── subtitle_service.py   # Whisper subtitles
        │   ├── visual_service.py     # Stock assets
        │   ├── render_service.py     # FFmpeg/LTX video
        │   ├── ltx_service.py        # LTX API integration
        │   ├── publish_service.py    # Platform APIs
        │   └── analytics_service.py  # Performance tracking
        └── workers/
            └── job_worker.py         # Pipeline orchestrator
```

## Technology Stack

### Local-First AI Models
- **LLM**: Ollama (local) or MCP (external)
- **TTS**: XTTS v2 (local) or ElevenLabs (API)
- **STT**: faster-whisper (local)
- **Video Gen**: **LTX-2** (local Python API or ComfyUI) or FFmpeg (compositing)

### Backend
- **Framework**: FastAPI
- **Database**: SQLite (SQLModel)
- **Scheduler**: APScheduler
- **Video**: FFmpeg
- **HTTP**: httpx (async)

### Frontend
- **Framework**: React + Vite
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Charts**: Recharts

### External APIs
- **YouTube**: Data API v3
- **Instagram**: Graph API
- **TikTok**: Content Posting API

## Configuration Files

### Environment Variables (`backend/.env`)
```env
# LLM
LLM_PROVIDER=ollama                    # or "mcp"
OLLAMA_MODEL=llama3.1:8b
MCP_LLM_CONNECTOR=openai               # if using MCP

# TTS
TTS_PROVIDER=xtts                      # or "elevenlabs"
XTTS_SERVER_URL=http://localhost:8020

# Video
VIDEO_GEN_PROVIDER=ffmpeg              # or "ltx"
LTX_API_URL=http://127.0.0.1:8188      # if using LTX

# Whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cuda
```

### Niche Configuration (Database + Files)
- Database: `niches` table (prompts, hashtags, settings)
- Files: `data/niches/{niche}/feeds.json`, `topics.json`

## Automation Features

### Fully Automated (After Approval)
✅ RSS feed monitoring  
✅ Topic selection  
✅ Script generation  
✅ Audio synthesis  
✅ Subtitle generation  
✅ Video rendering  
✅ Publishing to platforms  

### Manual Steps (Required)
⚠️ **Review & Approval** (before publishing)  
⚠️ **Topic override** (optional)  
⚠️ **Script editing** (optional)  

## Performance Notes

### RTX 4060 8GB VRAM Constraints
- **LTX-2 Video**: Max 480p, 3-5 seconds per clip
  - Use `ltx-2-19b-distilled-fp8.safetensors` model
  - Use `DistilledPipeline` (fastest, 8 steps)
  - Enable FP8 transformer: `enable_fp8=True`
- **Whisper**: Use `base` model, `float16` compute
- **XTTS**: Server mode recommended
- **Ollama**: `llama3.2:3b` for speed, `llama3.1:8b` for quality

### Optimization Tips
1. Use **LTX-2 DistilledPipeline** with FP8 quantization
2. Download `ltx-2-19b-distilled-fp8.safetensors` (smaller, faster)
3. Use direct Python API (faster than ComfyUI HTTP)
4. Close other GPU applications
5. Use CPU fallback for Whisper if CUDA OOM
6. Batch process during off-hours

---

**Last Updated**: 2026-01-22  
**Version**: 1.0.0  
**Status**: Production-ready with LTX integration
