@echo off
setlocal
title Content OPS AI - Setup Environment
color 0B

set ROOT=D:\Ideas\contentops-core
set ENV_FILE=%ROOT%\backend\.env
cd /d %ROOT%

echo ========================================
echo   Content OPS AI - Environment Setup
echo ========================================
echo.

if not exist "%ENV_FILE%" (
    echo ERROR: .env file not found at %ENV_FILE%
    echo Please run launch.bat first to generate default config.
    pause
    exit /b 1
)

echo Current .env file found.
echo.
echo Please enter your Hugging Face Token (starts with hf_...):
echo (Press Enter to skip if you don't have one or already set it)
set /p HF_TOKEN=Token: 

if "%HF_TOKEN%"=="" goto :skip_hf

echo.
echo Updating HF_TOKEN in .env...
powershell -Command "(Get-Content '%ENV_FILE%') -replace '# HF_TOKEN=your_token_here', 'HF_TOKEN=%HF_TOKEN%' | Set-Content '%ENV_FILE%'"
powershell -Command "(Get-Content '%ENV_FILE%') -replace 'HF_TOKEN=your_token_here', 'HF_TOKEN=%HF_TOKEN%' | Set-Content '%ENV_FILE%'"
echo Done.

:skip_hf
echo.
echo Setup complete.
echo Please restart the application (launch.bat) for changes to take effect.
echo.
pause
