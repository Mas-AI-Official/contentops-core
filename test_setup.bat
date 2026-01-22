@echo off
title Content Factory - Setup Test
color 0E

echo ========================================
echo   Content Factory - Setup Test
echo ========================================
echo.

cd /d D:\Ideas\content_factory

echo Testing setup...
echo.

REM Check Python
set PYTHON_PATH=C:\Python311\python.exe
if exist "%PYTHON_PATH%" (
    echo [OK] Python 3.11 found
    "%PYTHON_PATH%" --version
) else (
    echo [FAIL] Python 3.11 not found
)
echo.

REM Check Venv
set VENV_PYTHON=D:\Ideas\content_factory\venv\Scripts\python.exe
if exist "%VENV_PYTHON%" (
    echo [OK] Virtual environment Python found
    "%VENV_PYTHON%" --version
    echo.
    echo Testing imports...
    "%VENV_PYTHON%" -c "import fastapi; print('FastAPI:', fastapi.__version__)" 2>nul
    "%VENV_PYTHON%" -c "import uvicorn; print('Uvicorn:', uvicorn.__version__)" 2>nul
    "%VENV_PYTHON%" -c "import sqlmodel; print('SQLModel:', sqlmodel.__version__)" 2>nul
) else (
    echo [FAIL] Virtual environment Python not found
    echo Venv may be incomplete. Run install.bat to fix.
)
echo.

REM Check Frontend
if exist "frontend\node_modules" (
    echo [OK] Frontend node_modules found
) else (
    echo [FAIL] Frontend node_modules not found
)
echo.

REM Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama is running
) else (
    echo [WARN] Ollama is not running
)
echo.

REM Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] FFmpeg found
) else (
    echo [WARN] FFmpeg not found in PATH
)
echo.

echo ========================================
echo   Test Complete
echo ========================================
pause
