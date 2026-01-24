@echo off
title Content Factory - Cleanup C:\ Drive Models
color 0E

set ROOT=D:\Ideas\content_factory

echo ========================================
echo   Cleanup Models from C:\ Drive
echo ========================================
echo.
echo This script will find and remove models that were
echo incorrectly downloaded to C:\ drive.
echo.
echo Models should be in: D:\Ideas\content_factory\models
echo.

cd /d %ROOT%

powershell -ExecutionPolicy Bypass -File "%~dp0ops\cleanup_c_drive_models.ps1"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Cleanup script failed.
    pause
    exit /b 1
)

exit /b 0
