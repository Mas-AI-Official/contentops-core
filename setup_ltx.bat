@echo off
title Content Factory - Setup LTX Video Model
color 0E

set ROOT=D:\Ideas\content_factory
set MODELS_DIR=%ROOT%\models\ltx

echo ========================================
echo   Content Factory - Setup LTX Video Model
echo ========================================
echo.
echo This will download LTX video models for local generation.
echo.
echo NOTE: LTX models are LARGE (several GB).
echo For RTX 4060 8GB: Use distilled/FP8 models, max 480p, 3-5 seconds.
echo.

cd /d %ROOT%

REM Ensure models directory exists
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo Checking for ComfyUI-LTXVideo...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.11 and add it to PATH.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation Options
echo ========================================
echo.
echo 1. Install ComfyUI-LTXVideo (recommended)
echo 2. Download LTX models only (if ComfyUI already installed)
echo 3. Skip (manual setup)
echo.
set /p CHOICE="Choose option (1-3): "

if "%CHOICE%"=="1" (
    echo.
    echo Installing ComfyUI-LTXVideo...
    echo This will clone the repository and install dependencies.
    echo.
    
    if not exist "comfyui_ltx" (
        echo Cloning ComfyUI-LTXVideo repository...
        git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git comfyui_ltx
        if %errorlevel% neq 0 (
            echo ERROR: Failed to clone repository.
            pause
            exit /b 1
        )
    )
    
    cd comfyui_ltx
    
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    
    echo.
    echo ComfyUI-LTXVideo installed!
    echo.
    echo Next steps:
    echo 1. Run ComfyUI: cd comfyui_ltx && python main.py --lowvram
    echo 2. Set in backend\.env: VIDEO_GEN_PROVIDER=ltx
    echo 3. Set in backend\.env: LTX_API_URL=http://127.0.0.1:8188
    echo.
    cd ..
    
) else if "%CHOICE%"=="2" (
    echo.
    echo Downloading LTX models...
    echo.
    echo Models will be downloaded to: %MODELS_DIR%
    echo.
    echo For 8GB VRAM, use the distilled FP8 model:
    echo - ltx-video-distilled-fp8 (recommended for RTX 4060)
    echo.
    echo You can download manually from:
    echo https://huggingface.co/Lightricks/ltx-video-distilled
    echo.
    echo Or use huggingface-cli:
    echo huggingface-cli download Lightricks/ltx-video-distilled --local-dir %MODELS_DIR%
    echo.
    
) else (
    echo Skipping automatic setup.
    echo.
    echo Manual setup instructions:
    echo 1. Install ComfyUI-LTXVideo: https://github.com/Lightricks/ComfyUI-LTXVideo
    echo 2. Download LTX models to: %MODELS_DIR%
    echo 3. Run ComfyUI with --lowvram flag
    echo 4. Configure backend\.env with VIDEO_GEN_PROVIDER=ltx
    echo.
)

echo.
echo ========================================
echo   Setup Complete
echo ========================================
echo.
pause
