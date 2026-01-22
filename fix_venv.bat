@echo off
title Content Factory - Fix Virtual Environment
color 0C

echo ========================================
echo   Content Factory - Fix Virtual Environment
echo ========================================
echo.

cd /d D:\Ideas\content_factory

set PYTHON_PATH=C:\Python311\python.exe
set VENV_PATH=D:\Ideas\content_factory\venv

echo This will delete and recreate the virtual environment.
if "%1"=="--auto" (
    echo Running in auto mode...
) else (
    echo.
    set /p CONFIRM="Continue? (Y/N): "
    if /i not "%CONFIRM%"=="Y" (
        echo Cancelled.
        pause
        exit /b 0
    )
)

echo.
echo Deleting old venv...
if exist "%VENV_PATH%" (
    rmdir /s /q "%VENV_PATH%"
    echo Deleted.
)

echo.
echo Creating new virtual environment...
"%PYTHON_PATH%" -m venv "%VENV_PATH%"
if %errorlevel% neq 0 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

echo.
echo Verifying venv...
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo ERROR: Venv Python not found after creation
    pause
    exit /b 1
)

echo Venv created successfully!
"%VENV_PYTHON%" --version
echo.

echo Now installing dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
"%VENV_PATH%\Scripts\pip.exe" install -r backend\requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Virtual Environment Fixed!
    echo ========================================
    echo.
    echo You can now run launch.bat to start the application.
) else (
    echo.
    echo WARNING: Some packages may have failed to install.
    echo Check the output above for errors.
)

echo.
pause
