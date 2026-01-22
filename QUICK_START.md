# Content Factory - Quick Start Guide

## One Script to Launch Everything
Run this once and it will:
- Create the venv in `D:\Ideas\content_factory\venv`
- Install backend dependencies
- Install frontend dependencies
- Set local model cache paths
- Start backend + frontend
- Open the dashboard

```batch
launch.bat
```

## If Venv Creation Fails
1. Close all Python/command windows
2. Run `launch.bat` as Administrator
3. If still failing, delete the folder:
   `D:\Ideas\content_factory\venv`
4. Run `launch.bat` again

## File Structure

```
D:\Ideas\content_factory\
├── venv\                    # Virtual environment (Scripts\python.exe)
├── backend\                 # FastAPI backend
├── frontend\                # React frontend
├── models\                  # AI model cache
├── data\                    # Runtime data
└── launch.bat               # ⭐ Main launcher
```

## After Launch
1. Open http://localhost:3000
2. Go to Settings to verify services
3. Go to Models to download Ollama models
4. Go to Niches to configure niches
5. Go to Generator to create your first video
