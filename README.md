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

### LLM (Ollama)
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_FAST_MODEL=llama3.2:3b
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

1. **Topic Selection** - AI-generated or manual
2. **Script Generation** - Ollama LLM with niche prompts
3. **Voice Synthesis** - XTTS (local) or ElevenLabs (API)
4. **Subtitle Generation** - Whisper/faster-whisper
5. **Video Rendering** - FFmpeg with platform-specific encoding
6. **Publishing** - Official APIs (YouTube, Instagram, TikTok)

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
install.bat
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
- Ollama (LLM)
- XTTS v2 (TTS)
- faster-whisper (STT)
- FFmpeg (video)

## License

Private project for personal content automation.

---

Built for local-first content creation with privacy and control.
