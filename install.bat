@echo off
title Content Factory - Installation
color 0E

echo ========================================
echo   Content Factory - Installation
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM ==== Python 3.11 Check ====
echo [1/6] Checking Python 3.11...
set PYTHON_PATH=C:\Python311\python.exe

if exist "%PYTHON_PATH%" (
    echo Found Python 3.11 at %PYTHON_PATH%
    "%PYTHON_PATH%" --version
) else (
    echo WARNING: Python 3.11 not found at C:\Python311
    echo.
    echo Please install Python 3.11:
    echo   Option 1: winget install Python.Python.3.11
    echo   Option 2: https://www.python.org/downloads/release/python-3119/
    echo.
    echo After installing, ensure it's at C:\Python311 or update PYTHON_PATH in this script.
    pause
    exit /b 1
)
echo.

REM ==== Create Virtual Environment in Project Root ====
echo [2/6] Setting up Python virtual environment...
if exist venv (
    echo Virtual environment already exists.
    echo To recreate, delete the 'venv' folder and run this script again.
) else (
    echo Creating virtual environment with Python 3.11...
    "%PYTHON_PATH%" -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)
echo.

REM ==== Install Python Dependencies ====
echo [3/6] Installing Python dependencies...
call venv\Scripts\activate.bat
python --version
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install packages that might need pre-built wheels first
echo Installing packages with pre-built wheels...
pip install --only-binary :all: av 2>nul
if %errorlevel% neq 0 (
    echo Note: av package not available as wheel, skipping ^(optional^)
)

REM Install main requirements
echo.
echo Installing main requirements...
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some packages failed to install.
    echo Trying to continue with essential packages...
    echo.
    pip install fastapi uvicorn sqlmodel aiosqlite apscheduler httpx pydantic pydantic-settings faster-whisper loguru Pillow
)
echo Python dependencies installed.
echo.

REM ==== Check FFmpeg ====
echo [4/6] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: FFmpeg not found in PATH.
    echo Please install FFmpeg:
    echo   Option 1: winget install Gyan.FFmpeg
    echo   Option 2: Download from https://ffmpeg.org/download.html
    echo   Then add to PATH or set FFMPEG_PATH in .env
    echo.
) else (
    echo FFmpeg found:
    ffmpeg -version 2>&1 | findstr "ffmpeg version"
)
echo.

REM ==== Check Node.js ====
echo [5/6] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)
echo Node.js found:
node --version
echo.

REM Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)
cd ..
echo Frontend dependencies installed successfully.
echo.

REM ==== Setup Configuration ====
echo [6/6] Setting up configuration...
if not exist backend\.env (
    copy ops\env.example backend\.env
    echo Created backend\.env from template.
    echo.
    echo IMPORTANT: Edit backend\.env to configure:
    echo   - API keys (ElevenLabs, YouTube, Instagram, TikTok)
    echo   - Model paths and settings
) else (
    echo backend\.env already exists.
)
echo.

REM ==== Create models directory structure ====
echo Setting up models directory...
if not exist models\ollama mkdir models\ollama
if not exist models\whisper mkdir models\whisper
if not exist models\xtts mkdir models\xtts
if not exist models\image mkdir models\image
if not exist models\torch mkdir models\torch
echo Models directory ready.
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Python Version: 3.11 (from C:\Python311)
echo Virtual Env: D:\Ideas\content_factory\venv
echo.
echo Next steps:
echo   1. Install Ollama from https://ollama.ai/download
echo   2. Run: setup_models.bat (to download AI models)
echo   3. Edit backend\.env with your API keys
echo   4. Run: run.bat (to start everything)
echo.
echo TIP: To use local model storage, set this environment variable:
echo   setx OLLAMA_MODELS "D:\Ideas\content_factory\models\ollama"
echo   Then restart Ollama.
echo.
echo Dashboard will be at: http://localhost:3000
echo.
pause
