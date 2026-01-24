@echo off
title Content Factory - Launch All
color 0B

set ROOT=D:\Ideas\content_factory
set PYTHON_PATH=C:\Python311\python.exe
set VENV_PATH=%ROOT%\venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set VENV_PIP=%VENV_PATH%\Scripts\pip.exe

echo ========================================
echo   Content Factory - Launch All
echo ========================================
echo.

cd /d %ROOT%

REM ==== Check Python 3.11 ====
echo [1/5] Checking Python 3.11...
if not exist "%PYTHON_PATH%" (
    echo ERROR: Python 3.11 not found at C:\Python311
    echo Please install Python 3.11 and try again.
    pause
    exit /b 1
)
"%PYTHON_PATH%" --version
echo.

REM ==== Create/Repair Virtual Environment ====
echo [2/5] Setting up virtual environment...
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
echo [3/5] Installing Python dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
"%VENV_PIP%" install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: Some Python packages failed to install.
    echo Check the output above for details.
)
echo.

REM ==== Install Frontend Dependencies ====
echo [4/5] Checking frontend dependencies...
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
echo [5/5] Setting up model cache paths...
set OLLAMA_MODELS=%ROOT%\models\ollama
set HF_HOME=%ROOT%\models\whisper\hf
set TORCH_HOME=%ROOT%\models\torch
set XDG_CACHE_HOME=%ROOT%\models\cache
if not exist "models\ollama" mkdir "models\ollama"
if not exist "models\whisper\hf" mkdir "models\whisper\hf"
if not exist "models\xtts" mkdir "models\xtts"
if not exist "models\torch" mkdir "models\torch"
if not exist "models\cache" mkdir "models\cache"
if not exist "models\image" mkdir "models\image"
echo Model paths ready.
echo.

REM ==== Start Backend ====
echo Starting Backend API...
start "Content Factory - Backend" cmd /k "cd /d %ROOT% && call venv\Scripts\activate.bat && set OLLAMA_MODELS=%OLLAMA_MODELS% && set HF_HOME=%HF_HOME% && set TORCH_HOME=%TORCH_HOME% && set XDG_CACHE_HOME=%XDG_CACHE_HOME% && cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM ==== Start Frontend ====
echo Starting Frontend...
start "Content Factory - Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev"

REM ==== Open Dashboard ====
echo Opening dashboard...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo   Content Factory is Launching!
echo ========================================
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo ========================================
echo.
pause
