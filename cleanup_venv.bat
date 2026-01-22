@echo off
title Content Factory - Cleanup Virtual Environment
color 0C

echo ========================================
echo   Content Factory - Cleanup Venv
echo ========================================
echo.
echo This will forcefully kill Python processes and delete the venv.
echo.

cd /d D:\Ideas\content_factory

set VENV_PATH=D:\Ideas\content_factory\venv

if not exist "%VENV_PATH%" (
    if not "%1"=="--silent" (
        echo Venv folder does not exist. Nothing to clean.
        pause
    )
    exit /b 0
)

echo Step 1: Killing Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM uvicorn.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done.
echo.

echo Step 2: Attempting to delete venv folder...
rmdir /s /q "%VENV_PATH%" 2>nul
if %errorlevel% equ 0 (
    echo Venv deleted successfully.
    if not "%1"=="--silent" pause
    exit /b 0
)

echo Standard deletion failed. Trying PowerShell method...
powershell -Command "Get-ChildItem -Path '%VENV_PATH%' -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue; Remove-Item -Path '%VENV_PATH%' -Force -Recurse -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul

if not exist "%VENV_PATH%" (
    echo Venv deleted successfully using PowerShell.
    if not "%1"=="--silent" pause
    exit /b 0
)

echo.
echo ERROR: Could not delete venv folder. Files are locked.
echo.
echo Please:
echo   1. Close all Python/command windows
echo   2. Close any IDEs (VS Code, PyCharm, etc.)
echo   3. Check Task Manager for python.exe processes
echo   4. Manually delete: D:\Ideas\content_factory\venv
echo.
if not "%1"=="--silent" pause
