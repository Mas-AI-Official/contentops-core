@echo off
setlocal
echo [STEP] Checking for FFmpeg...

where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] FFmpeg is already installed and in PATH.
    ffmpeg -version | findstr "ffmpeg version"
    goto :EOF
)

echo [INFO] FFmpeg not found in PATH.
echo [STEP] Downloading FFmpeg (gyan.dev build)...

set "DOWNLOAD_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "DEST_DIR=D:\Ideas\contentops-core\tools"
set "ZIP_FILE=%DEST_DIR%\ffmpeg.zip"

if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%ZIP_FILE%'"

if not exist "%ZIP_FILE%" (
    echo [ERROR] Failed to download FFmpeg.
    exit /b 1
)

echo [STEP] Extracting FFmpeg...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%DEST_DIR%' -Force"

echo [STEP] Configuring Environment...
for /d %%D in ("%DEST_DIR%\ffmpeg-*") do (
    set "FFMPEG_BIN=%%D\bin"
)

if defined FFMPEG_BIN (
    echo [INFO] Found binary path: %FFMPEG_BIN%
    echo [INFO] Adding to PATH (current session)...
    set "PATH=%FFMPEG_BIN%;%PATH%"
    
    echo [INFO] Adding to PATH (permanent - user)...
    setx PATH "%FFMPEG_BIN%;%PATH%"
    
    echo [OK] FFmpeg installed successfully!
    ffmpeg -version | findstr "ffmpeg version"
) else (
    echo [ERROR] Could not find bin directory in extracted files.
)

del "%ZIP_FILE%"
echo [DONE] Setup complete.
endlocal
