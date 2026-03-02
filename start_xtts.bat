@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Content OPS AI - XTTS Server
color 0D

set ROOT=D:\Ideas\contentops-core
set VENV_PATH=%ROOT%\venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set TTS_HOME=D:\Ideas\MODELS_ROOT\xtts
if "%XTTS_PORT%"=="" set XTTS_PORT=8020

for /f %%P in ('powershell -NoProfile -Command "$p=%XTTS_PORT%; while(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue){$p++}; Write-Output $p"') do set XTTS_PORT=%%P

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
set XTTS_VOICES_ROOT=%TTS_HOME%\voices
set COQUI_TOS_AGREED=1
set TORCHAUDIO_BACKEND=soundfile
REM Content Factory server exposes POST /tts_to_audio (backend expects this). Coqui TTS.server.server only has /api/tts and no speaker_wav.
cd /d "%ROOT%"
REM Using CUDA to vastly dramatically speed up generation times now that PyTorch + CUDA is installed
"%VENV_PYTHON%" xtts_server.py --model_path "%TTS_HOME%" --config_path "%TTS_HOME%\config.json" --port %XTTS_PORT% --use_cuda

if %errorlevel% neq 0 (
    echo.
    echo Server stopped with error.
    echo To use GPU, add --use_cuda to the xtts_server.py command in this bat.
    pause
)
