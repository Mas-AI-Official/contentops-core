# Content Factory

A local-first, end-to-end content generation system for creating short-form vertical videos across multiple niches and platforms.

## Features

- **Multi-Niche Content Generation**: Create content for AI/Tech, Finance, Health, Travel, Comedy, and more
- **AI-Powered Pipeline**: Script generation (Ollama), TTS (XTTS/ElevenLabs), Subtitles (Whisper)
- **Multi-Platform Publishing**: YouTube Shorts, Instagram Reels, TikTok
- **Per-Niche Model Selection**: Configure different AI models per content niche
- **Local Model Management**: Download and manage Ollama models from the dashboard
- **Script Library**: Organized script storage by date/niche with search
- **Platform-Specific Export**: Optimized video encoding per platform requirements
- **Modern Dashboard**: React + Tailwind UI with 10 feature pages

## System Requirements

- **OS**: Windows 10/11
- **GPU**: NVIDIA GPU (4060 or better recommended for local AI)
- **Python**: 3.11.x (Required - located at `C:\Python311`)
- **Node.js**: 18.x or later
- **FFmpeg**: Required for video processing

## Quick Start (One-Click Setup)

### Step 1: Install Dependencies

Double-click `install.bat` to:
- Verify Python 3.11 is available
- Create virtual environment in project root
- Install Python packages
- Install Node.js dependencies
- Create initial `.env` configuration

```batch
install.bat
```

### Step 2: Install Ollama

Download and install from: https://ollama.ai/download

### Step 3: Setup AI Models

Double-click `setup_models.bat` to:
- Start Ollama service
- Download llama3.1:8b (main model)
- Download llama3.2:3b (fast model)
- Seed default niches

```batch
setup_models.bat
```

### Step 4: Start the System

Double-click `run.bat` to:
- Start Ollama (if not running)
- Start backend API server
- Start frontend development server
- Open dashboard in browser

```batch
run.bat
```

**Dashboard**: http://localhost:3000  
**API Docs**: http://localhost:8000/docs

## Directory Structure

```
D:\Ideas\content_factory\
├── backend\           # FastAPI backend
│   ├── app\
│   │   ├── api\       # API routes
│   │   ├── core\      # Configuration
│   │   ├── db\        # Database
│   │   ├── models\    # SQLModel schemas
│   │   ├── services\  # Business logic
│   │   └── workers\   # Background jobs
│   └── scripts\       # Utility scripts
├── frontend\          # React + Tailwind
├── data\              # Runtime data
│   ├── assets\        # Stock media, fonts, logos
│   ├── outputs\       # Generated videos
│   ├── scripts\       # Saved scripts
│   └── logs\          # Application logs
├── models\            # Local AI model cache
│   ├── ollama\        # Ollama models
│   ├── whisper\       # Whisper models
│   ├── xtts\          # TTS models
│   └── torch\         # PyTorch cache
├── ops\               # Operations scripts
├── venv\              # Python virtual environment
├── install.bat        # One-click install
├── run.bat            # One-click start
└── setup_models.bat   # Model download
```

## Local Model Storage

To store Ollama models in this project folder, set the environment variable:

```batch
setx OLLAMA_MODELS "D:\Ideas\content_factory\models\ollama"
```

Then restart Ollama.

Other model caches (Whisper, PyTorch) are automatically configured to use the `models\` directory.

## Configuration

Edit `backend\.env` to configure:

### LLM Providers

**Option 1: Ollama (Local, Default)**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_FAST_MODEL=llama3.2:3b
```

**Option 2: Hugging Face Router (Recommended for Best Quality)**
```env
LLM_PROVIDER=hf_router
HF_ROUTER_BASE_URL=https://router.huggingface.co/v1
HF_TOKEN=your_huggingface_token
HF_ROUTER_REASONING_LEVEL=medium  # low, medium, high
HF_ROUTER_TEMPERATURE=0.7
```
The HF Router intelligently routes requests to the best available model (Llama-3.3-70B, Qwen3-Coder, etc.) for optimal reasoning and quality.

**Option 3: MCP (External APIs)**
```env
LLM_PROVIDER=mcp
MCP_CONNECTORS_JSON=[{"name":"openai",...}]
```

### TTS Options
```env
TTS_PROVIDER=xtts
XTTS_ENABLED=true

# Or use ElevenLabs
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### Whisper (Subtitles)
```env
WHISPER_MODEL=base
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

### Platform APIs
See `backend\.env` template for YouTube, Instagram, and TikTok API configuration.

### MCP / External Connectors (Optional)
You can wire external providers (hosted LLMs, TTS, or tools) using the MCP-style proxy.

Add to `backend\.env`:
```env
MCP_ENABLED=true
MCP_DEFAULT_TIMEOUT=60
MCP_CONNECTORS_JSON=[{"name":"openai","type":"llm","base_url":"https://api.openai.com/v1","auth_header":"Authorization","auth_env":"OPENAI_API_KEY","auth_prefix":"Bearer "}]
MCP_LLM_CONNECTOR=openai
MCP_LLM_PATH=v1/chat/completions
MCP_LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=mcp
```

Then call:
- `GET /api/mcp/status`
- `GET /api/mcp/connectors`
- `POST /api/mcp/forward`

## Per-Niche Model Settings

Each niche can override global AI settings:

| Setting | Options | Description |
|---------|---------|-------------|
| LLM Model | Any installed Ollama model | Script generation model |
| Temperature | 0.0 - 2.0 | Creativity level |
| TTS Provider | xtts, elevenlabs | Voice synthesis |
| Voice ID | ElevenLabs ID or speaker wav | Voice selection |
| Whisper Model | tiny, base, small, medium, large | Subtitle accuracy |
| Whisper Device | cuda, cpu | Processing device |

## Dashboard Pages

1. **Overview** - Today's jobs, success/fail stats, scheduled runs
2. **Niches** - Create/edit content niches and AI settings
3. **Accounts** - Platform connection status
4. **Generator** - Generate test videos, preview, approve
5. **Queue** - Job management, retry, logs
6. **Library** - Video outputs, metadata, preview, platform compatibility
7. **Analytics** - Performance metrics, trends, winners
8. **Settings** - Paths, models, service status
9. **Models** - Download/manage Ollama models
10. **Scripts** - Browse saved scripts by date/niche

## Content Pipeline

**📊 See [PIPELINE.md](PIPELINE.md) for complete visual diagram and architecture details.**

1. **Topic Selection** - RSS feeds → LLM picks best story, or topic lists, or LLM generation
2. **Script Generation** - Ollama/MCP LLM with niche prompts (hook, body, CTA)
3. **Voice Synthesis** - XTTS (local) or ElevenLabs (API) with per-niche voice config
4. **Subtitle Generation** - Whisper/faster-whisper with per-niche model/device
5. **Video Rendering** - **LTX AI generation** (new!) or FFmpeg compositing with stock B-roll
6. **Review & Approval** - Manual review in dashboard (required before publishing)
7. **Publishing** - Official APIs (YouTube, Instagram, TikTok)

## News/RSS Automation

To let the system pull real-world stories automatically, add RSS/Atom feeds per niche:

`data/niches/<niche_name>/feeds.json`
```json
{
  "feeds": [
    "https://rss.cnn.com/rss/edition_technology.rss",
    "https://www.theverge.com/rss/index.xml"
  ]
}
```

When you click **Generate Topic**, the backend will:
1. Pull headlines from RSS feeds
2. Use the LLM to pick the best story
3. Generate script → audio → subtitles → video

If no feeds exist, it falls back to topic lists or LLM generation.

## Local LTX-2 Video Generation (Optional)

**LTX-2 (Lightricks)** is the official open-source AI video generation model. It's the first DiT-based audio-video foundation model. You can run it locally,
but laptop GPUs (like RTX 4060 8GB) are limited to short, low-res clips unless heavily optimized.

**Official Repository**: https://github.com/Lightricks/LTX-2

### Setup LTX

Run the setup script:
```batch
setup_ltx.bat
```

This will:
- Install ComfyUI-LTXVideo (or guide you to manual setup)
- Download LTX models (distilled FP8 recommended for 8GB VRAM)
- Configure for local generation

### Configuration

In `backend\.env`:
```env
VIDEO_GEN_PROVIDER=ltx
LTX_API_URL=http://127.0.0.1:8188
```

### How It Works

When `VIDEO_GEN_PROVIDER=ltx`:
1. **LTX generates base video** from script text (480p, 3-5 seconds)
2. **FFmpeg composites** audio, subtitles, logo, music on top
3. **Final output** is 1080x1920 vertical video

### System Requirements

- **8GB VRAM**: Max 480p, 3-5 seconds per clip
- **ComfyUI**: Run with `--lowvram` flag
- **Models**: Use distilled/FP8 variants

See:
- [LTX System Requirements](https://docs.ltx.video/open-source-model/getting-started/system-requirements)
- [ComfyUI LTX Memory Management](https://deepwiki.com/Lightricks/ComfyUI-LTXVideo/4.3-memory-management)

The Settings page will show LTX connection status.

## Compliance Notes

- **Official APIs Only**: Uses YouTube Data API, Instagram Graph API, TikTok Content Posting API
- **No Engagement Bots**: Only content creation and publishing
- **TikTok Unverified**: Posts as private until app audit approval
- **Rate Limiting**: Respects platform API limits
- **Content Guidelines**: User responsible for content compliance

## Troubleshooting

### Python Version Mismatch
Ensure Python 3.11 is at `C:\Python311`. The install script specifically uses this path.

### Ollama Not Running
```batch
ollama serve
```

### FFmpeg Not Found
Install via winget:
```batch
winget install Gyan.FFmpeg
```

### GPU/CUDA Issues
Set Whisper to CPU fallback:
```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### Virtual Environment Issues
Delete and recreate:
```batch
rmdir /s /q venv
launch.bat
```

## Development

### Backend (FastAPI)
```batch
cd D:\Ideas\content_factory
call venv\Scripts\activate
cd backend
uvicorn app.main:app --reload
```

### Frontend (Vite + React)
```batch
cd D:\Ideas\content_factory\frontend
npm run dev
```

## Tech Stack

**Backend**:
- Python 3.11
- FastAPI
- SQLModel (SQLite)
- APScheduler
- httpx (async HTTP)

**Frontend**:
- Vite
- React 18
- Tailwind CSS
- Lucide Icons
- Recharts

**AI/ML**:
- Ollama (LLM) or MCP (external LLMs)
- XTTS v2 (TTS) or ElevenLabs (API)
- faster-whisper (STT)
- LTX (AI video generation) or FFmpeg (compositing)

## License

Private project for personal content automation.

---

Built for local-first content creation with privacy and control.
