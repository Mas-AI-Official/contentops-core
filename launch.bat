@echo off
title Content Factory - Complete Launch
color 0B

echo ========================================
echo   Content Factory - Complete Launch
echo ========================================
echo.

cd /d D:\Ideas\content_factory

REM ==== Step 1: Check Python ====
echo [Step 1/7] Checking Python 3.11...
set PYTHON_PATH=C:\Python311\python.exe
if not exist "%PYTHON_PATH%" (
    echo ERROR: Python 3.11 not found at C:\Python311
    echo Please install Python 3.11 first.
    pause
    exit /b 1
)
echo Python found: 
"%PYTHON_PATH%" --version
echo.

REM ==== Step 2: Check/Fix Virtual Environment ====
echo [Step 2/7] Checking virtual environment...
set VENV_PATH=D:\Ideas\content_factory\venv
set VENV_ACTIVATE=%VENV_PATH%\Scripts\activate.bat
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set VENV_PIP=%VENV_PATH%\Scripts\pip.exe

if not exist "%VENV_PYTHON%" (
    echo Virtual environment is missing or incomplete.
    echo.
    if exist "%VENV_PATH%" (
        echo Deleting incomplete venv...
        rmdir /s /q "%VENV_PATH%" 2>nul
    )
    echo Creating new virtual environment...
    "%PYTHON_PATH%" -m venv --clear "%VENV_PATH%"
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Failed to create venv. This might be a Python installation issue.
        echo.
        echo Try running this manually:
        echo   C:\Python311\python.exe -m venv D:\Ideas\content_factory\venv
        echo.
        echo Or reinstall Python 3.11 with "Add Python to PATH" enabled.
        pause
        exit /b 1
    )
    
    REM Wait a moment for files to be written
    timeout /t 2 /nobreak >nul
    
    REM Verify it was created
    if not exist "%VENV_PYTHON%" (
        echo ERROR: Venv created but Python executable not found.
        echo This may indicate a Python installation problem.
        pause
        exit /b 1
    )
    echo Venv created successfully.
) else (
    echo Virtual environment exists and appears complete.
)
echo.

REM ==== Step 3: Install/Update Dependencies ====
echo [Step 3/7] Checking Python dependencies...
"%VENV_PYTHON%" -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Python dependencies (this may take a few minutes)...
    "%VENV_PYTHON%" -m pip install --upgrade pip --quiet
    "%VENV_PIP%" install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo WARNING: Some packages failed to install. Continuing anyway...
    ) else (
        echo Python dependencies installed successfully.
    )
) else (
    echo Python dependencies already installed.
)
echo.

REM ==== Step 4: Check Frontend Dependencies ====
echo [Step 4/7] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo Frontend dependencies installed.
) else (
    echo Frontend dependencies already installed.
)
echo.

REM ==== Step 5: Check Ollama ====
echo [Step 5/7] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo WARNING: Ollama may not be running. LLM features will not work.
    ) else (
        echo Ollama started successfully.
    )
) else (
    echo Ollama is running.
)
echo.

REM ==== Step 6: Set Environment Variables ====
echo [Step 6/7] Setting up environment...
set HF_HOME=D:\Ideas\content_factory\models\whisper\hf
set TORCH_HOME=D:\Ideas\content_factory\models\torch
set XDG_CACHE_HOME=D:\Ideas\content_factory\models\cache

REM Ensure model directories exist
if not exist "models\whisper\hf" mkdir "models\whisper\hf"
if not exist "models\torch" mkdir "models\torch"
if not exist "models\cache" mkdir "models\cache"
echo Environment configured.
echo.

REM ==== Step 7: Start Services ====
echo [Step 7/7] Starting services...
echo.

REM Start Backend
echo Starting Backend API...
start "Content Factory - Backend" cmd /k "cd /d D:\Ideas\content_factory && set HF_HOME=%HF_HOME% && set TORCH_HOME=%TORCH_HOME% && set XDG_CACHE_HOME=%XDG_CACHE_HOME% && cd backend && %VENV_PYTHON% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM Wait for backend to start
echo Waiting for backend to start...
set BACKEND_READY=0
for /L %%i in (1,1,30) do (
    timeout /t 2 /nobreak >nul
    curl -s http://127.0.0.1:8000/health >nul 2>&1
    if %errorlevel% equ 0 (
        set BACKEND_READY=1
        goto backend_ready
    )
)
:backend_ready
if %BACKEND_READY% equ 1 (
    echo Backend is ready!
) else (
    echo WARNING: Backend may not have started. Check the Backend window for errors.
)
echo.

REM Start Frontend
echo Starting Frontend...
start "Content Factory - Frontend" cmd /k "cd /d D:\Ideas\content_factory\frontend && npm run dev"

REM Wait a bit for frontend
timeout /t 3 /nobreak >nul
echo.

REM Open Dashboard
echo Opening dashboard...
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo   Content Factory is Launching!
echo ========================================
echo.
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo.
echo   Check the Backend and Frontend windows for any errors.
echo   Close those windows to stop the services.
echo.
echo   This window will stay open to monitor.
echo ========================================
echo.
pause
