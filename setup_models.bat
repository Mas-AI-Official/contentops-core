@echo off
title Content Factory - Model Setup
color 0B

echo ========================================
echo   Content Factory - Model Setup
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM ==== Check Ollama ====
echo [1/4] Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
    
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Ollama is not running and could not be started.
        echo Please install Ollama from: https://ollama.ai/download
        pause
        exit /b 1
    )
)
echo Ollama is running.
echo.

REM ==== Optional: Set Ollama Models Path ====
echo TIP: To store Ollama models in this project folder, run:
echo   setx OLLAMA_MODELS "D:\Ideas\content_factory\models\ollama"
echo   Then restart Ollama.
echo.

REM ==== Pull Main Model ====
echo [2/4] Pulling main LLM model (llama3.1:8b)...
echo This may take a few minutes depending on your connection...
ollama pull llama3.1:8b
if %errorlevel% neq 0 (
    echo WARNING: Failed to pull llama3.1:8b
    echo You can try manually: ollama pull llama3.1:8b
)
echo.

REM ==== Pull Fast Model ====
echo [3/4] Pulling fast LLM model (llama3.2:3b)...
ollama pull llama3.2:3b
if %errorlevel% neq 0 (
    echo WARNING: Failed to pull llama3.2:3b
    echo You can try manually: ollama pull llama3.2:3b
)
echo.

REM ==== Seed Database with Default Niches ====
echo [4/4] Seeding database with default niches...
if not exist venv (
    echo ERROR: Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM Set environment variables for model caching
set HF_HOME=D:\Ideas\content_factory\models\whisper\hf
set TORCH_HOME=D:\Ideas\content_factory\models\torch

cd backend
python scripts\seed_niches.py
if %errorlevel% neq 0 (
    echo WARNING: Failed to seed niches.
    echo Database may need to be created first. Try running the app once.
)
cd ..
echo.

REM ==== List Installed Models ====
echo.
echo ========================================
echo   Installed Ollama Models:
echo ========================================
ollama list
echo.

echo ========================================
echo   Model Setup Complete!
echo ========================================
echo.
echo Installed models:
echo   - llama3.1:8b (main content generation)
echo   - llama3.2:3b (fast topic generation)
echo.
echo You can download additional models:
echo   ollama pull mistral:7b
echo   ollama pull gemma2:9b
echo   ollama pull phi3:mini
echo.
echo Or use the Models page in the dashboard.
echo.
pause
