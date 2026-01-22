@echo off
title Content Factory - Setup Models
color 0E

set ROOT=D:\Ideas\content_factory
set OLLAMA_MODELS=%ROOT%\models\ollama
set MODELS=llama3.1:8b llama3.2:3b

echo ========================================
echo   Content Factory - Setup Models
echo ========================================
echo.

cd /d %ROOT%

REM Ensure models directory exists
if not exist "models\ollama" mkdir "models\ollama"

REM Check Ollama command
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ollama is not installed or not in PATH.
    echo Download it from: https://ollama.com/download
    pause
    exit /b 1
)

REM Use project-local Ollama models directory
REM Set environment variable for this session
set OLLAMA_MODELS=%ROOT%\models\ollama

echo Using OLLAMA_MODELS=%OLLAMA_MODELS%
echo.

REM Check if Ollama is running and stop it if needed to apply new OLLAMA_MODELS
echo Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is running. Checking if OLLAMA_MODELS needs to be updated...
    set CURRENT_OLLAMA_MODELS=
    for /f "tokens=2 delims==" %%A in ('setx OLLAMA_MODELS 2^>nul ^| findstr /i "OLLAMA_MODELS"') do set CURRENT_OLLAMA_MODELS=%%A
    if not "%CURRENT_OLLAMA_MODELS%"=="%OLLAMA_MODELS%" (
        echo OLLAMA_MODELS needs to be updated. Stopping Ollama...
        taskkill /F /IM ollama.exe >nul 2>&1
        timeout /t 2 /nobreak >nul
    )
)

REM Set OLLAMA_MODELS system-wide
echo Setting OLLAMA_MODELS environment variable...
setx OLLAMA_MODELS "%OLLAMA_MODELS%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] OLLAMA_MODELS set to: %OLLAMA_MODELS%
) else (
    echo [WARNING] Could not set OLLAMA_MODELS permanently.
    echo          You may need to run as Administrator or set it manually.
    echo          Setting for current session only...
)
REM Also set for current session
set OLLAMA_MODELS=%ROOT%\models\ollama
echo.

REM Ensure Ollama is running with new OLLAMA_MODELS
echo Starting Ollama with OLLAMA_MODELS=%OLLAMA_MODELS%...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama service...
    start /min "" ollama serve
    timeout /t 8 /nobreak >nul
    
    REM Verify Ollama started
    set RETRY_COUNT=0
    :check_ollama
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        set /a RETRY_COUNT+=1
        if %RETRY_COUNT% lss 5 (
            echo Waiting for Ollama to start... (%RETRY_COUNT%/5)
            timeout /t 2 /nobreak >nul
            goto check_ollama
        ) else (
            echo [ERROR] Ollama did not start after 10 seconds.
            echo         Please run manually: ollama serve
            echo         Make sure OLLAMA_MODELS=%OLLAMA_MODELS% is set.
            pause
            exit /b 1
        )
    )
)
echo [OK] Ollama is running.
echo.

echo Checking installed models...
ollama list
echo.

REM Download models with retry logic
for %%M in (%MODELS%) do (
    call :ensure_model "%%M"
)

echo.
echo ========================================
echo   Model setup complete
echo ========================================
echo.
pause
exit /b 0

:ensure_model
set MODEL=%~1
if "%MODEL%"=="" exit /b 0

echo.
echo ========================================
echo Checking for %MODEL%...
echo ========================================

REM Check if model is already installed
ollama list | findstr /i /c:"%MODEL%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] %MODEL% is already installed.
    
    REM Verify it's accessible
    echo Verifying model accessibility...
    ollama show %MODEL% >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] %MODEL% is accessible and ready to use.
        
        REM Check if model files exist in our directory
        if exist "%OLLAMA_MODELS%\*%MODEL%*" (
            echo [OK] Model files found in: %OLLAMA_MODELS%
        ) else (
            echo [INFO] Model may be in default Ollama location.
            echo        This is OK - Ollama will use it regardless of location.
        )
    ) else (
        echo [WARNING] Model listed but may be corrupted. Re-downloading...
        goto download_model
    )
) else (
    echo [INFO] %MODEL% not found. Will download now.
    goto download_model
)
goto end_ensure_model

:download_model
echo.
echo [DL] Downloading %MODEL% ...
echo This may take several minutes depending on your connection and model size...
echo Model will be saved to: %OLLAMA_MODELS%
echo.

REM Download with progress
ollama pull "%MODEL%"
set PULL_ERROR=%errorlevel%

if %PULL_ERROR% neq 0 (
    echo.
    echo [ERROR] Failed to download %MODEL% (exit code: %PULL_ERROR%).
    echo.
    echo Possible causes:
    echo - No internet connection
    echo - Ollama service not running properly
    echo - Insufficient disk space
    echo - Network timeout
    echo.
    echo Retrying in 5 seconds...
    timeout /t 5 /nobreak >nul
    
    echo Retrying download...
    ollama pull "%MODEL%"
    set PULL_ERROR=%errorlevel%
    
    if %PULL_ERROR% neq 0 (
        echo.
        echo [ERROR] Retry also failed. Please check:
        echo 1. Internet connection: ping 8.8.8.8
        echo 2. Ollama is running: curl http://localhost:11434/api/tags
        echo 3. Disk space: dir %OLLAMA_MODELS%
        echo 4. Try manual download: ollama pull %MODEL%
        echo.
    ) else (
        echo.
        echo [OK] %MODEL% downloaded successfully on retry!
    )
) else (
    echo.
    echo [OK] %MODEL% downloaded successfully!
    
    REM Verify the download
    echo Verifying installation...
    ollama show %MODEL% >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] %MODEL% verified and ready to use.
    ) else (
        echo [WARNING] Model downloaded but verification failed.
    )
)

:end_ensure_model
exit /b 0
