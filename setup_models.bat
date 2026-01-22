@echo off
title Content Factory - Model Setup
color 0B

echo ========================================
echo   Content Factory - Model Setup
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM Check if Ollama is running
echo [1/3] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
)
echo Ollama is ready
echo.

REM Pull models
echo [2/3] Downloading AI models...
echo This may take a while depending on your internet speed.
echo.

echo Pulling llama3.1:8b (main model, ~4.7GB)...
ollama pull llama3.1:8b
echo.

echo Pulling llama3.2:3b (fast model, ~2GB)...
ollama pull llama3.2:3b
echo.

REM Seed database with niches
echo [3/3] Setting up default niches...
cd backend
call venv\Scripts\activate.bat
python scripts\seed_niches.py
cd ..
echo.

echo ========================================
echo   Model Setup Complete!
echo ========================================
echo.
echo Installed models:
echo   - llama3.1:8b (main model for scripts)
echo   - llama3.2:3b (fast model for topics)
echo.
echo You can now run: run.bat
echo.
pause
