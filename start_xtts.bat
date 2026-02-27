@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Content OPS AI - XTTS Server
color 0D

set ROOT=D:\Ideas\contentops-core
set VENV_PATH=%ROOT%\venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set TTS_HOME=D:\Ideas\MODELS_ROOT\xtts
if "%XTTS_PORT%"=="" set XTTS_PORT=8020

for /f %%P in ('powershell -NoProfile -Command "$p=%XTTS_PORT%; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; $p"') do set XTTS_PORT=%%P

echo ========================================
echo   Content OPS AI - XTTS Server
echo ========================================
echo.

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found. Please run launch.bat first.
    pause
    exit /b 1
)

echo [1/2] Checking TTS installation...
"%VENV_PYTHON%" -c "import TTS" >nul 2>&1
if %errorlevel% neq 0 (
    echo TTS not found. Installing Coqui TTS...
    echo This may take a while...
    
    REM Install basic dependencies first to avoid build errors
    "%VENV_PYTHON%" -m pip install numpy==1.24.3 scipy==1.10.1 pandas
    
    REM Install TTS without dependencies first to check if wheel exists
    "%VENV_PYTHON%" -m pip install TTS --no-deps
    
    REM Install dependencies excluding problematic ones if needed
    "%VENV_PYTHON%" -m pip install TTS
    
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Failed to install TTS automatically.
        echo Please try running this manually in the venv:
        echo pip install TTS --no-build-isolation
        echo.
        pause
        exit /b 1
    )
    echo TTS installed successfully.
) else (
    echo TTS is already installed.
)

echo.
echo [2/2] Starting XTTS Server...
echo Server will run at http://localhost:%XTTS_PORT%
echo.

REM Set environment variables for TTS
set TTS_HOME=D:\Ideas\MODELS_ROOT\xtts
set COQUI_TOS_AGREED=1
set TORCHAUDIO_BACKEND=soundfile
"%VENV_PYTHON%" -m TTS.server.server --model_path D:\Ideas\MODELS_ROOT\xtts --config_path D:\Ideas\MODELS_ROOT\xtts\config.json --port %XTTS_PORT% --use_cuda false

if %errorlevel% neq 0 (
    echo.
    echo Server stopped with error.
    echo If CUDA is unavailable, keep '--use_cuda false' (already set by default).
    pause
)
