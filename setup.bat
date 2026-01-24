@echo off
title Content Factory - Setup
color 0E

set ROOT=%~dp0
set OPS=%ROOT%ops

echo ========================================
echo   Content Factory - Setup
echo ========================================
echo.
echo 1. Setup Models (Ollama + LTX)
echo 2. Setup LTX Only
echo 3. Setup Ollama Only
echo 4. Exit
echo.

set /p CHOICE="Select option (1-4): "

if "%CHOICE%"=="1" goto setup_all
if "%CHOICE%"=="2" goto setup_ltx
if "%CHOICE%"=="3" goto setup_ollama
if "%CHOICE%"=="4" goto end

goto end

:setup_all
echo.
echo Setting up ALL models...
echo.
call "%OPS%\setup_models.bat"
if %errorlevel% neq 0 exit /b %errorlevel%
call "%OPS%\setup_ltx.bat"
if %errorlevel% neq 0 exit /b %errorlevel%
goto end

:setup_ltx
echo.
echo Setting up LTX models...
echo.
call "%OPS%\setup_ltx.bat"
goto end

:setup_ollama
echo.
echo Setting up Ollama models...
echo.
call "%OPS%\setup_models.bat"
goto end

:end
echo.
echo Setup finished.
echo.
pause
