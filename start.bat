@echo off
title ContentOps Agency - MAS-AI Technologies
color 0A

echo.
echo  =============================================
echo    ContentOps - Autonomous AI Media Agency
echo    MAS-AI Technologies Inc.
echo  =============================================
echo.

cd /d "D:\Ideas\contentops-fresh"

:: Check Python venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found. Run: python -m venv venv
    pause
    exit /b 1
)

:: Load .env and validate credentials
echo [1/4] Checking credentials...
venv\Scripts\python.exe scripts\check_credentials.py
echo.

:: Start backend API
echo [2/4] Starting backend API on :8080 ...
start "ContentOps Backend" cmd /k "cd /d D:\Ideas\contentops-fresh && venv\Scripts\python.exe scripts\start_server.py"

:: Wait for backend to boot
ping -n 4 127.0.0.1 >nul

:: Open dashboard in browser
echo [3/4] Opening dashboard...
start http://127.0.0.1:8080

echo.
echo [4/4] ContentOps is running!
echo.
echo   Dashboard:  http://127.0.0.1:8080/dashboard
echo   API Docs:   http://127.0.0.1:8080/docs
echo   Health:     http://127.0.0.1:8080/health
echo.
echo   To connect platforms, run:  venv\Scripts\python.exe scripts\setup_credentials.py
echo.
echo Press any key to stop the server...
pause >nul

:: Kill backend
taskkill /FI "WINDOWTITLE eq ContentOps Backend" /F >nul 2>&1
echo Server stopped.
