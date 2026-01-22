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
echo 1. Install LTX-2 Python package (recommended - direct API)
echo 2. Install ComfyUI-LTXVideo (alternative - via API)
echo 3. Download LTX models only
echo 4. Skip (manual setup)
echo.
set /p CHOICE="Choose option (1-4): "

if "%CHOICE%"=="1" (
    echo.
    echo Installing LTX-2 Python package...
    echo This will install the official LTX-2 inference package.
    echo.
    
    cd /d %ROOT%
    call venv\Scripts\activate.bat
    
    echo Installing LTX-2 packages...
    pip install git+https://github.com/Lightricks/LTX-2.git#subdirectory=packages/ltx-core
    pip install git+https://github.com/Lightricks/LTX-2.git#subdirectory=packages/ltx-pipelines
    
    echo.
    echo LTX-2 Python package installed!
    echo.
    echo Next steps:
    echo 1. Download models (see option 3)
    echo 2. Set in backend\.env: VIDEO_GEN_PROVIDER=ltx
    echo 3. Set in backend\.env: LTX_MODEL_PATH=D:\Ideas\content_factory\models\ltx
    echo.
    
) else if "%CHOICE%"=="2" (
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
    
) else if "%CHOICE%"=="3" (
    echo.
    echo Downloading LTX-2 models...
    echo.
    echo Models will be downloaded to: %MODELS_DIR%
    echo.
    echo For 8GB VRAM (RTX 4060), download:
    echo - ltx-2-19b-distilled-fp8.safetensors (RECOMMENDED)
    echo - ltx-2-spatial-upscaler-x2-1.0.safetensors (required)
    echo - ltx-2-19b-distilled-lora-384.safetensors (required)
    echo.
    echo Download from:
    echo https://huggingface.co/Lightricks/ltx-2
    echo.
    echo Or use huggingface-cli:
    echo huggingface-cli download Lightricks/ltx-2 --local-dir %MODELS_DIR%
    echo.
    echo NOTE: Models are LARGE (several GB). Use distilled FP8 for 8GB VRAM.
    echo.
    
) else if "%CHOICE%"=="4" (
    echo Skipping automatic setup.
    echo.
    echo Manual setup instructions:
    echo.
    echo Option A: Direct Python API (recommended)
    echo 1. Clone: git clone https://github.com/Lightricks/LTX-2.git
    echo 2. Install: cd LTX-2 && uv sync --frozen
    echo 3. Or pip: pip install git+https://github.com/Lightricks/LTX-2.git#subdirectory=packages/ltx-core
    echo 4. Download models from: https://huggingface.co/Lightricks/ltx-2
    echo 5. Set in backend\.env: VIDEO_GEN_PROVIDER=ltx
    echo 6. Set in backend\.env: LTX_MODEL_PATH=%MODELS_DIR%
    echo.
    echo Option B: ComfyUI API
    echo 1. Install ComfyUI-LTXVideo: https://github.com/Lightricks/ComfyUI-LTXVideo
    echo 2. Download LTX models to: %MODELS_DIR%
    echo 3. Run ComfyUI with --lowvram flag
    echo 4. Set in backend\.env: VIDEO_GEN_PROVIDER=ltx
    echo 5. Set in backend\.env: LTX_API_URL=http://127.0.0.1:8188
    echo.
)

echo.
echo ========================================
echo   Setup Complete
echo ========================================
echo.
pause
