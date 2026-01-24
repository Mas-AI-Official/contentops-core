@echo off
title Content Factory - Setup Models
color 0E

setlocal enabledelayedexpansion

REM Set Root to parent directory
pushd "%~dp0.."
set ROOT=%CD%
popd

set VENV_PYTHON=%ROOT%\venv\Scripts\python.exe

REM Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found at %ROOT%\venv
    echo Please run launch.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM Try to run PowerShell script first
cd /d %ROOT%
powershell -ExecutionPolicy Bypass -File "%~dp0setup_models.ps1" %*
if %errorlevel% equ 0 (
    echo.
    echo Model setup completed successfully via PowerShell script.
    pause
    exit /b 0
)
echo.
echo PowerShell script failed or returned error, using batch fallback...
echo.

REM Fallback to batch implementation
REM Enable delayed expansion for error handling

REM Ensure venv is activated for fallback
if exist "%VENV_PYTHON%" (
    call venv\Scripts\activate.bat
)

set OLLAMA_MODELS=%ROOT%\models\ollama
set MODELS=llama3.1:8b llama3.2:3b

echo ========================================
echo   Content Factory - Setup Models (Batch Fallback)
echo ========================================
echo.
echo Root: %ROOT%
echo Ollama Models Path: %OLLAMA_MODELS%
echo Models to download: %MODELS%
echo.

cd /d %ROOT%

REM Ensure models directory exists
if not exist "models\ollama" mkdir "models\ollama"

REM Check Ollama command
echo Checking for Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo ERROR: Ollama is not installed or not in PATH.
    echo ========================================
    echo.
    echo Please download Ollama from: https://ollama.com/download
    echo.
    echo After installing Ollama, run this script again.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo [OK] Ollama found in PATH.

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
echo Checking if Ollama is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama is already running.
    echo      Using existing Ollama instance.
    echo      NOTE: If you need to change OLLAMA_MODELS, stop Ollama first.
    echo.
) else (
    echo Ollama is not running. Starting Ollama service with OLLAMA_MODELS=%OLLAMA_MODELS%...
    echo.
    echo IMPORTANT: Ollama will save models to: %OLLAMA_MODELS%
    echo.
    
    REM Create a batch file to start Ollama with the correct environment
    set OLLAMA_START_BAT=%TEMP%\start_ollama_%RANDOM%.bat
    echo @echo off > "%OLLAMA_START_BAT%"
    echo set OLLAMA_MODELS=%OLLAMA_MODELS% >> "%OLLAMA_START_BAT%"
    echo cd /d %ROOT% >> "%OLLAMA_START_BAT%"
    echo echo OLLAMA_MODELS is set to: %%OLLAMA_MODELS%% >> "%OLLAMA_START_BAT%"
    echo ollama serve >> "%OLLAMA_START_BAT%"
    
    REM Start Ollama using the batch file
    start "Ollama Service" cmd /k ""%OLLAMA_START_BAT%""
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
            echo [WARNING] Ollama did not start automatically.
            echo          Ollama may already be running in another window.
            echo          Continuing with downloads - if they fail, start Ollama manually:
            echo          set OLLAMA_MODELS=%OLLAMA_MODELS%
            echo          ollama serve
            echo.
        )
    ) else (
        echo [OK] Ollama started successfully.
        echo.
    )
)

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
echo Verifying model locations...
echo.

REM Check if models are in our directory
set FOUND_IN_CORRECT_LOCATION=0
for %%M in (%MODELS%) do (
    REM Check for model files in our directory
    dir "%OLLAMA_MODELS%\*" /s /b 2>nul | findstr /i "%%M" >nul
    if %errorlevel% equ 0 (
        echo [OK] Model files found in: %OLLAMA_MODELS%
        set /a FOUND_IN_CORRECT_LOCATION+=1
    ) else (
        echo [INFO] Model %%M may be in default Ollama location
        echo        This is OK - Ollama will use it regardless
    )
)

echo.
echo OLLAMA_MODELS is set to: %OLLAMA_MODELS%
echo Models should be saved here when downloaded.
echo.
echo To verify, check: %OLLAMA_MODELS%
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

REM Verify OLLAMA_MODELS is set and directory exists
if not exist "%OLLAMA_MODELS%" (
    echo Creating directory: %OLLAMA_MODELS%
    mkdir "%OLLAMA_MODELS%"
)

REM Set OLLAMA_MODELS for this command (ensure it's set)
set "OLLAMA_MODELS=%OLLAMA_MODELS%"

REM Verify Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama service is not running!
    echo Please start Ollama manually or restart this script.
    pause
    exit /b 1
)

REM Download with progress
echo Executing: ollama pull "%MODEL%"
echo Current OLLAMA_MODELS: %OLLAMA_MODELS%
echo.
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
