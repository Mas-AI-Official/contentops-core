@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Content OPS AI - Launch All
color 0B

set ROOT=D:\Ideas\contentops-core
set PYTHON_PATH=C:\Python311\python.exe
set VENV_PATH=%ROOT%\venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set VENV_PIP=%VENV_PATH%\Scripts\pip.exe

echo ========================================
echo   Content OPS AI - Launch All
echo ========================================
echo.

REM Port resolution: never kill existing processes. If default port is busy, use next free port.
echo [0/6] Resolving free ports (no process kill - busy port = use next free)...
for /f %%P in ('powershell -NoProfile -Command "$p=8100; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; Write-Output $p"') do set BACKEND_PORT=%%P
for /f %%P in ('powershell -NoProfile -Command "$p=3005; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; Write-Output $p"') do set FRONTEND_PORT=%%P
for /f %%P in ('powershell -NoProfile -Command "$p=8020; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; Write-Output $p"') do set XTTS_PORT=%%P

if not "!BACKEND_PORT!"=="8100" echo [INFO] Port 8100 busy, using backend port !BACKEND_PORT!
if not "!FRONTEND_PORT!"=="3005" echo [INFO] Port 3005 busy, using frontend port !FRONTEND_PORT!
if not "!XTTS_PORT!"=="8020" echo [INFO] Port 8020 busy, using XTTS port !XTTS_PORT!
echo.

cd /d %ROOT%

REM ==== Check Python 3.11 ====
echo [1/6] Checking Python 3.11...
if not exist "%PYTHON_PATH%" (
    echo ERROR: Python 3.11 not found at C:\Python311
    echo Please install Python 3.11 and try again.
    pause
    exit /b 1
)
"%PYTHON_PATH%" --version
echo.

REM ==== Create/Repair Virtual Environment ====
echo [2/6] Setting up virtual environment...
if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment in %VENV_PATH%...
    if exist "%VENV_PATH%" (
        rmdir /s /q "%VENV_PATH%"
    )
    "%PYTHON_PATH%" -m venv "%VENV_PATH%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create venv.
        echo Try running as Administrator or close any Python processes.
        pause
        exit /b 1
    )
)
if not exist "%VENV_PYTHON%" (
    echo ERROR: Venv Python not found after creation.
    pause
    exit /b 1
)
echo Venv ready.
echo.

REM ==== Install Python Dependencies ====
echo [3/6] Installing Python dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
"%VENV_PIP%" install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: Some Python packages failed to install.
    echo Check the output above for details.
)
echo.

REM ==== Install Frontend Dependencies ====
echo [4/6] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd /d %ROOT%\frontend
    call npm install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install frontend dependencies.
        cd /d %ROOT%
        pause
        exit /b 1
    )
    cd /d %ROOT%
) else (
    echo Frontend dependencies already installed.
)
echo.

REM ==== Configure Model Cache Paths ====
echo [5/6] Setting up model cache paths...
set OLLAMA_MODELS=D:\Ideas\MODELS_ROOT\ollama
set HF_HOME=D:\Ideas\MODELS_ROOT\hf
set TORCH_HOME=D:\Ideas\MODELS_ROOT\torch
set XDG_CACHE_HOME=D:\Ideas\MODELS_ROOT\cache
set TTS_HOME=D:\Ideas\MODELS_ROOT\xtts
set COQUI_TOS_AGREED=1
set TORCHAUDIO_BACKEND=soundfile

if not exist "%OLLAMA_MODELS%" mkdir "%OLLAMA_MODELS%"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"
if not exist "%TTS_HOME%" mkdir "%TTS_HOME%"
if not exist "%TORCH_HOME%" mkdir "%TORCH_HOME%"
if not exist "%XDG_CACHE_HOME%" mkdir "%XDG_CACHE_HOME%"
echo Model paths ready (centralized at D:\Ideas\MODELS_ROOT).
echo.

REM ==== Remotion (optional) ====
echo [6/6] Checking Remotion dependencies...
if exist "backend\remotion\package.json" (
    if not exist "backend\remotion\node_modules" (
        echo Installing Remotion dependencies...
        cd /d %ROOT%\backend\remotion
        call npm install
        if %errorlevel% neq 0 (
            echo WARNING: Failed to install Remotion dependencies.
        )
        cd /d %ROOT%
    )
) else (
    echo Remotion not present, skipping.
)
echo.

REM ==== Start Backend ====
echo Starting Backend API...
start "Content OPS AI - Backend" cmd /k "cd /d %ROOT% && call venv\Scripts\activate.bat && set OLLAMA_MODELS=%OLLAMA_MODELS% && set HF_HOME=%HF_HOME% && set TORCH_HOME=%TORCH_HOME% && set XDG_CACHE_HOME=%XDG_CACHE_HOME% && set TTS_HOME=%TTS_HOME% && set COQUI_TOS_AGREED=1 && set TORCHAUDIO_BACKEND=soundfile && set API_PORT=!BACKEND_PORT! && set XTTS_SERVER_URL=http://localhost:!XTTS_PORT! && cd backend && python -m app.main"

REM ==== Start Frontend ====
echo Starting Frontend...
start "Content OPS AI - Frontend" cmd /k "cd /d %ROOT%\frontend && set VITE_API_PROXY_TARGET=http://localhost:!BACKEND_PORT! && npm run dev -- --port !FRONTEND_PORT!"

REM ==== Start XTTS Server ====
echo Starting XTTS Server...
start "Content OPS AI - XTTS" cmd /k "cd /d %ROOT% && set XTTS_PORT=!XTTS_PORT! && call start_xtts.bat"

REM ==== Start Autonomous Content Engine ====
echo Starting Autonomous Content Engine...
start "Content OPS AI - Autonomous Engine" cmd /k "cd /d %ROOT% && call venv\Scripts\activate.bat && set OLLAMA_MODELS=%OLLAMA_MODELS% && set HF_HOME=%HF_HOME% && set TORCH_HOME=%TORCH_HOME% && set XDG_CACHE_HOME=%XDG_CACHE_HOME% && set TTS_HOME=%TTS_HOME% && set API_PORT=!BACKEND_PORT! && set XTTS_SERVER_URL=http://localhost:!XTTS_PORT! && cd backend && python launch_autonomous.py"

REM ==== Open Dashboard ====
echo Opening dashboard...
echo Waiting 10 seconds for backend to initialize...
timeout /t 10 /nobreak >nul
start http://localhost:!FRONTEND_PORT!

echo.
echo ========================================
echo   Content OPS AI is Launching!
echo ========================================
echo   Backend:     http://localhost:!BACKEND_PORT!
echo   API Docs:    http://localhost:!BACKEND_PORT!/docs
echo   Frontend:    http://localhost:!FRONTEND_PORT!
echo   XTTS:        http://localhost:!XTTS_PORT!
echo   Autonomous:  Active (Background)
echo ========================================
echo.
pause
