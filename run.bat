@echo off
title Content Factory - Starting Services
color 0A

echo ========================================
echo   Content Factory - One Click Start
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM Check if Ollama is running
echo [1/4] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
) else (
    echo Ollama is running
)

REM Start Backend
echo.
echo [2/4] Starting Backend API...
cd backend
if not exist venv (
    echo ERROR: Virtual environment not found. Run ops\install.ps1 first.
    pause
    exit /b 1
)
start "Content Factory - Backend" cmd /k "call venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd ..

REM Wait for backend
echo Waiting for backend...
:wait_backend
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
echo Backend is ready!

REM Start Frontend
echo.
echo [3/4] Starting Frontend...
cd frontend
start "Content Factory - Frontend" cmd /k "npm run dev"
cd ..

REM Wait and open browser
echo.
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
echo   Close this window to keep running.
echo   Close the other windows to stop.
echo ========================================
pause
