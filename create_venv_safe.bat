@echo off
REM Safe venv creation that avoids access denied errors
set PYTHON_PATH=%~1
set TARGET_PATH=%~2

if "%PYTHON_PATH%"=="" exit /b 1
if "%TARGET_PATH%"=="" exit /b 1

REM Create in temp location first
set TEMP_VENV=%TARGET_PATH%_temp_%RANDOM%
if exist "%TEMP_VENV%" rmdir /s /q "%TEMP_VENV%" >nul 2>&1

echo Creating venv in temp location: %TEMP_VENV%
"%PYTHON_PATH%" -m venv "%TEMP_VENV%"
if %errorlevel% neq 0 (
    echo Failed to create venv in temp location
    exit /b 1
)

REM Wait and verify
timeout /t 2 /nobreak >nul
if not exist "%TEMP_VENV%\Scripts\python.exe" (
    echo Venv created but python.exe not found
    rmdir /s /q "%TEMP_VENV%" >nul 2>&1
    exit /b 1
)

REM Now remove old target if exists
if exist "%TARGET_PATH%" (
    echo Removing old venv...
    rmdir /s /q "%TARGET_PATH%" >nul 2>&1
    powershell -Command "Remove-Item -Path '%TARGET_PATH%' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
    timeout /t 1 /nobreak >nul
)

REM Move temp to target
if not exist "%TARGET_PATH%" (
    ren "%TEMP_VENV%" "venv" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Failed to rename venv
        REM Try moving instead
        move "%TEMP_VENV%" "%TARGET_PATH%" >nul 2>&1
        if %errorlevel% neq 0 (
            echo Failed to move venv
            exit /b 1
        )
    )
)

REM Cleanup any leftover temp
if exist "%TEMP_VENV%" rmdir /s /q "%TEMP_VENV%" >nul 2>&1

exit /b 0
