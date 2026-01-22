# Content Factory

A local-first, end-to-end content generation system for creating and publishing short-form vertical videos across YouTube Shorts, Instagram Reels, and TikTok.

## Features

- **Multi-Niche Support**: Create content for different niches with customized prompts
- **AI-Powered Scripts**: Generate video scripts using local Ollama LLMs
- **Model Management**: Download, test, and switch AI models from the UI
- **Text-to-Speech**: Convert scripts to audio using XTTS (local) or ElevenLabs
- **Auto Subtitles**: Generate subtitles using Whisper/faster-whisper
- **Video Rendering**: FFmpeg-based rendering with B-roll, music, subtitles, and watermarks
- **Platform-Specific Export**: Optimized exports for YouTube Shorts, Instagram Reels, TikTok
- **Multi-Platform Publishing**: Official API integrations for all platforms
- **Script Library**: All scripts saved organized by date and niche
- **Analytics Dashboard**: Track video performance and identify winners
- **Job Queue**: Background processing with scheduling support

## Requirements

- Windows 10/11
- Python 3.11+
- Node.js 18+
- NVIDIA GPU (optional, for faster processing)
- FFmpeg
- Ollama

## Quick Start (One-Click)

### Option 1: Batch Files (Recommended)

**Double-click these files in order:**

1. **`install.bat`** - First time setup (installs Python deps, Node deps)
2. **`setup_models.bat`** - Download AI models (llama3.1:8b, llama3.2:3b)
3. **`run.bat`** - Start everything and open browser!

### Option 2: PowerShell Scripts

```powershell
cd D:\Ideas\content_factory\ops
.\install.ps1       # Install dependencies
.\setup_models.ps1  # Download AI models
.\run_all.ps1       # Start all services
```

### Configure API Keys (Optional)

Edit `backend\.env` to add your platform API keys:

- **YouTube**: Follow [YouTube Data API setup](https://developers.google.com/youtube/v3/getting-started)
- **Instagram**: Follow [Instagram Graph API setup](https://developers.facebook.com/docs/instagram-api/getting-started)
- **TikTok**: Follow [TikTok Content Posting API setup](https://developers.tiktok.com/doc/content-posting-api-get-started)

Note: You can generate videos without API keys. Publishing will work in "export for manual upload" mode.

### 5. Create Your First Video

1. Open http://localhost:3000
2. Go to **Niches** - verify default niches are loaded
3. Go to **Generator**
4. Select a niche, generate a topic, preview the script
5. Click "Generate Full Video"
6. Wait for processing (check Queue for status)
7. Preview and approve in Library

## Directory Structure

```
content_factory/
├── run.bat               # One-click start (double-click this!)
├── install.bat           # One-click install
├── setup_models.bat      # Download AI models
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Configuration + platform specs
│   │   ├── db/           # Database setup
│   │   ├── models/       # Pydantic/SQLModel models
│   │   ├── services/     # Business logic + script storage
│   │   ├── workers/      # Background job processing
│   │   └── main.py       # FastAPI application
│   ├── scripts/          # Utility scripts
│   └── tests/
├── frontend/             # React + Vite dashboard (10 pages!)
├── data/
│   ├── assets/
│   │   ├── music/        # Background music tracks
│   │   ├── logos/        # Watermark logos
│   │   ├── fonts/        # Subtitle fonts
│   │   └── stock/        # B-roll footage by niche
│   ├── niches/           # Niche configurations
│   ├── outputs/          # Generated videos
│   ├── scripts/          # Saved scripts (by date/niche)
│   ├── uploads/          # User uploads
│   └── logs/             # Application logs
└── ops/
    ├── install.ps1       # PowerShell install
    ├── setup_models.ps1
    ├── run_all.ps1
    └── env.example
```

## Adding Assets

### Stock Videos (B-Roll)

Place stock videos in `data/assets/stock/`:
- Organize by niche: `stock/ai_tech/`, `stock/finance_tax/`
- Or use `stock/general/` for universal footage
- Supported formats: MP4, MOV, AVI, MKV, WebM

### Background Music

Place music files in `data/assets/music/`:
- Organize by mood: `music/upbeat/`, `music/calm/`
- Or by niche: `music/ai_tech/`
- Supported formats: MP3, WAV

### Logos

Place watermark logos in `data/assets/logos/`:
- Use `default.png` for all videos
- Or `{niche_name}.png` for niche-specific logos
- Recommended: PNG with transparency, ~200px width

### Fonts

Place subtitle fonts in `data/assets/fonts/`:
- TTF or OTF format
- First font found will be used for subtitles

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Compliance Notes

This tool is designed for **legitimate content creation** only:

1. **Official APIs Only**: Publishing uses official platform APIs
2. **No Engagement Automation**: No auto-liking, auto-commenting, or follow/unfollow
3. **Content Creation Only**: Generate, render, and publish your own content
4. **Platform Guidelines**: You are responsible for ensuring content compliance

### TikTok Important Note

TikTok's Content Posting API has a **verification requirement**:
- Unverified apps can only post videos as **PRIVATE**
- Videos will be private/self-only until TikTok completes audit
- Use "export for manual upload" until verified
- Apply for verification at developers.tiktok.com

## Troubleshooting

### Ollama not connecting
```powershell
ollama serve
```

### FFmpeg not found
```powershell
winget install Gyan.FFmpeg
# Restart terminal after install
```

### CUDA/GPU errors
Set `WHISPER_DEVICE=cpu` in `.env` if no GPU available

### Python module not found
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## License

Private use only. Do not distribute.
