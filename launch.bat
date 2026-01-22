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
    
    REM Kill any Python processes first
    echo Closing any running Python processes...
    taskkill /F /IM python.exe /T >nul 2>&1
    taskkill /F /IM pythonw.exe /T >nul 2>&1
    taskkill /F /IM uvicorn.exe /T >nul 2>&1
    timeout /t 2 /nobreak >nul
    
    if exist "%VENV_PATH%" (
        echo Attempting to delete incomplete venv...
        
        REM Try renaming first (avoids access issues)
        set VENV_OLD=%VENV_PATH%_old_%RANDOM%
        if exist "%VENV_OLD%" rmdir /s /q "%VENV_OLD%" >nul 2>&1
        
        ren "%VENV_PATH%" "venv_old_%RANDOM%" >nul 2>&1
        if %errorlevel% equ 0 (
            echo Old venv renamed. Will delete in background...
            start /min "" cmd /c "timeout /t 5 /nobreak >nul && rmdir /s /q \"%VENV_OLD%\" >nul 2>&1"
        ) else (
            REM Rename failed, try direct deletion
            rmdir /s /q "%VENV_PATH%" >nul 2>&1
            if exist "%VENV_PATH%" (
                powershell -Command "Remove-Item -Path '%VENV_PATH%' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
            )
        )
        timeout /t 1 /nobreak >nul
    )
    
    echo Creating new virtual environment...
    
    REM Try creating venv - Python will handle existing files
    "%PYTHON_PATH%" -m venv "%VENV_PATH%" 2>&1
    set VENV_CREATE_ERROR=%errorlevel%
    
    if %VENV_CREATE_ERROR% neq 0 (
        echo.
        echo ERROR: Failed to create venv (Error: %VENV_CREATE_ERROR%)
        echo.
        echo Trying alternative method (creating in temp location)...
        
        REM Try creating in a different location first
        set TEMP_VENV=%VENV_PATH%_new
        if exist "%TEMP_VENV%" rmdir /s /q "%TEMP_VENV%" >nul 2>&1
        
        "%PYTHON_PATH%" -m venv "%TEMP_VENV%"
        if %errorlevel% equ 0 (
            timeout /t 2 /nobreak >nul
            if exist "%TEMP_VENV%\Scripts\python.exe" (
                echo Temp venv created successfully. Moving to final location...
                
                REM Remove old if still exists
                if exist "%VENV_PATH%" (
                    call cleanup_venv.bat --silent
                    timeout /t 2 /nobreak >nul
                )
                
                REM Move temp to final
                if not exist "%VENV_PATH%" (
                    move "%TEMP_VENV%" "%VENV_PATH%" >nul 2>&1
                    if %errorlevel% equ 0 (
                        echo Venv moved successfully.
                        goto venv_created
                    )
                )
            )
        )
        
        echo.
        echo ERROR: All venv creation methods failed.
        echo.
        echo Please try:
        echo   1. Run as Administrator
        echo   2. Or manually: C:\Python311\python.exe -m venv D:\Ideas\content_factory\venv
        echo   3. Or run: cleanup_venv.bat then launch.bat again
        echo.
        pause
        exit /b 1
    )
    
    :venv_created
    
    REM Wait a moment for files to be written
    timeout /t 3 /nobreak >nul
    
    REM Verify it was created
    if not exist "%VENV_PYTHON%" (
        echo ERROR: Venv created but Python executable not found.
        echo This may indicate a Python installation problem.
        echo.
        echo Checking venv structure...
        if exist "%VENV_PATH%" (
            dir "%VENV_PATH%" /b
            if exist "%VENV_PATH%\Scripts" (
                dir "%VENV_PATH%\Scripts" /b
            ) else (
                echo Scripts folder is missing!
            )
        )
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
