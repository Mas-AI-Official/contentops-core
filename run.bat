@echo off
title Content Factory - Starting Services
color 0A

echo ========================================
echo   Content Factory - One Click Start
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM ==== Python Version Check ====
echo Checking Python environment...
if not exist "D:\Ideas\content_factory\venv" (
    echo ERROR: Virtual environment not found at D:\Ideas\content_factory\venv
    echo.
    echo Please run install.bat first to create the virtual environment.
    pause
    exit /b 1
)

if not exist "D:\Ideas\content_factory\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment is incomplete or corrupted.
    echo The venv folder exists but Scripts\activate.bat is missing.
    echo.
    echo This usually means the venv creation was interrupted or failed.
    echo.
    echo To fix this:
    echo   1. Delete the 'venv' folder manually
    echo   2. Run install.bat to recreate it properly
    echo.
    echo Or press Y to delete it now and then run install.bat:
    set /p DELETE_VENV="Delete broken venv now? (Y/N): "
    if /i "%DELETE_VENV%"=="Y" (
        echo Deleting broken venv...
        rmdir /s /q "D:\Ideas\content_factory\venv"
        echo.
        echo Venv deleted. Please run install.bat to recreate it.
    )
    pause
    exit /b 1
)

REM Activate venv and check Python version
call "D:\Ideas\content_factory\venv\Scripts\activate.bat"
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python version: %PYVER%

REM Warn if not Python 3.11
echo %PYVER% | findstr /C:"3.11" >nul
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Expected Python 3.11.x but found %PYVER%
    echo Some packages may not work correctly.
    echo Consider recreating the venv with Python 3.11:
    echo   1. Delete the 'venv' folder
    echo   2. Run install.bat again
    echo.
    timeout /t 5
)
echo.

REM ==== Check Ollama ====
echo [1/4] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
    
    REM Check again
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo WARNING: Ollama may not be running. LLM features will not work.
        echo Install from: https://ollama.ai/download
    ) else (
        echo Ollama started successfully.
    )
) else (
    echo Ollama is running.
)
echo.

REM ==== Set Environment Variables for Local Models ====
set HF_HOME=D:\Ideas\content_factory\models\whisper\hf
set TORCH_HOME=D:\Ideas\content_factory\models\torch
set XDG_CACHE_HOME=D:\Ideas\content_factory\models\cache

REM ==== Start Backend ====
echo [2/4] Starting Backend API...
start "Content Factory - Backend" cmd /k "cd /d D:\Ideas\content_factory && call D:\Ideas\content_factory\venv\Scripts\activate.bat && set HF_HOME=%HF_HOME% && set TORCH_HOME=%TORCH_HOME% && set XDG_CACHE_HOME=%XDG_CACHE_HOME% && cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM Wait for backend
echo Waiting for backend to start...
:wait_backend
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
echo Backend is ready!
echo.

REM ==== Start Frontend ====
echo [3/4] Starting Frontend...
start "Content Factory - Frontend" cmd /k "cd /d D:\Ideas\content_factory\frontend && npm run dev"
echo.

REM ==== Open Dashboard ====
echo [4/4] Opening dashboard...
timeout /t 5 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo   Content Factory is Running!
echo ========================================
echo.
echo   Dashboard: http://localhost:3000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Python: %PYVER%
echo   Venv: D:\Ideas\content_factory\venv
echo.
echo   Close this window to keep running.
echo   Close the Backend/Frontend windows to stop.
echo ========================================
pause
