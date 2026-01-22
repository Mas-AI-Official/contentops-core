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
set OLLAMA_MODELS=%OLLAMA_MODELS%

echo Using OLLAMA_MODELS=%OLLAMA_MODELS%
echo.

REM Ensure Ollama is running
echo Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama is not running. Starting Ollama...
    start /min "" ollama serve
    timeout /t 5 /nobreak >nul
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Ollama did not start. Please run: ollama serve
        pause
        exit /b 1
    )
)
echo Ollama is running.
echo.

echo Checking installed models...
ollama list
echo.

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

ollama list | findstr /i "%MODEL%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] %MODEL% already installed.
) else (
    echo [DL] Downloading %MODEL% ...
    ollama pull "%MODEL%"
    if %errorlevel% neq 0 (
        echo [WARN] Failed to download %MODEL%.
    ) else (
        echo [OK] %MODEL% downloaded.
    )
)
exit /b 0
