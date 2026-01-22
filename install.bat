@echo off
title Content Factory - Installation
color 0E

echo ========================================
echo   Content Factory - Installation
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Create venv and install Python deps
echo [2/5] Setting up Python environment...
cd backend
if not exist venv (
    python -m venv venv
    echo Created virtual environment
)
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo Python dependencies installed
cd ..
echo.

REM Check FFmpeg
echo [3/5] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo FFmpeg not found. Please install FFmpeg:
    echo   Option 1: winget install Gyan.FFmpeg
    echo   Option 2: https://ffmpeg.org/download.html
    echo.
) else (
    echo FFmpeg found
)
echo.

REM Check Node.js
echo [4/5] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)
node --version

REM Install frontend deps
echo Installing frontend dependencies...
cd frontend
call npm install
cd ..
echo.

REM Create .env
echo [5/5] Setting up configuration...
if not exist backend\.env (
    copy ops\env.example backend\.env
    echo Created backend\.env from template
    echo Please edit backend\.env to add your API keys
) else (
    echo backend\.env already exists
)
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Install Ollama from https://ollama.ai/download
echo   2. Run: ollama serve
echo   3. Run: setup_models.bat (to download AI models)
echo   4. Edit backend\.env with your settings
echo   5. Run: run.bat (to start everything)
echo.
echo Dashboard will be at: http://localhost:3000
echo.
pause
