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
    echo ========================================
    echo   Model Download Options
    echo ========================================
    echo.
    echo LTX-2 (NEW, RECOMMENDED):
    echo - Official DiT-based audio-video model
    echo - Synchronized audio/video, high fidelity
    echo - Multiple performance modes (DistilledPipeline fastest)
    echo - Production-ready outputs
    echo.
    echo LTX Video Distilled (OLD, Legacy):
    echo - Older model, still functional
    echo - Simpler but less capable
    echo.
    echo Which models to download?
    echo 1. LTX-2 only (RECOMMENDED for RTX 4060)
    echo 2. Both LTX-2 and legacy LTX (for compatibility)
    echo 3. Legacy LTX only (not recommended)
    echo 4. Show download commands only (manual)
    echo.
    set /p MODEL_CHOICE="Choose option (1-4): "
    
    if "%MODEL_CHOICE%"=="1" (
        echo.
        echo Downloading LTX-2 models (RECOMMENDED)...
        echo.
        echo For 8GB VRAM (RTX 4060), downloading:
        echo - ltx-2-19b-distilled-fp8.safetensors (main model)
        echo - ltx-2-spatial-upscaler-x2-1.0.safetensors (upscaler)
        echo - ltx-2-19b-distilled-lora-384.safetensors (LoRA)
        echo.
        
        REM Check if huggingface-cli is available
        where huggingface-cli >nul 2>&1
        if %errorlevel% neq 0 (
            echo WARNING: huggingface-cli not found in PATH.
            echo Please install: pip install huggingface-hub
            echo.
            echo Manual download instructions:
            echo 1. Visit: https://huggingface.co/Lightricks/ltx-2
            echo 2. Download these files to: %MODELS_DIR%
            echo    - ltx-2-19b-distilled-fp8.safetensors
            echo    - ltx-2-spatial-upscaler-x2-1.0.safetensors
            echo    - ltx-2-19b-distilled-lora-384.safetensors
            echo.
            pause
            goto :end_models
        )
        
        echo Starting download (this may take a while, models are large)...
        echo.
        
        REM Download LTX-2 models (specific files for 8GB VRAM)
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-fp8.safetensors" --local-dir %MODELS_DIR%
        if %errorlevel% neq 0 (
            echo ERROR: Failed to download main model.
            echo You may need to login: huggingface-cli login
            pause
            goto :end_models
        )
        
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-spatial-upscaler-x2-1.0.safetensors" --local-dir %MODELS_DIR%
        if %errorlevel% neq 0 (
            echo WARNING: Failed to download upscaler. Continuing...
        )
        
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-lora-384.safetensors" --local-dir %MODELS_DIR%
        if %errorlevel% neq 0 (
            echo WARNING: Failed to download LoRA. Continuing...
        )
        
        echo.
        echo LTX-2 models downloaded successfully!
        echo Location: %MODELS_DIR%
        echo.
        
    ) else if "%MODEL_CHOICE%"=="2" (
        echo.
        echo Downloading both LTX-2 and legacy LTX models...
        echo.
        echo This will download:
        echo 1. LTX-2 models (recommended)
        echo 2. Legacy ltx-video-distilled models (for compatibility)
        echo.
        
        REM Check if huggingface-cli is available
        where huggingface-cli >nul 2>&1
        if %errorlevel% neq 0 (
            echo WARNING: huggingface-cli not found in PATH.
            echo Please install: pip install huggingface-hub
            pause
            goto :end_models
        )
        
        echo Downloading LTX-2 models first...
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-fp8.safetensors" --local-dir %MODELS_DIR%
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-spatial-upscaler-x2-1.0.safetensors" --local-dir %MODELS_DIR%
        huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-lora-384.safetensors" --local-dir %MODELS_DIR%
        
        echo.
        echo Downloading legacy LTX models...
        REM Create subdirectory for legacy models
        set LEGACY_DIR=%MODELS_DIR%\legacy
        if not exist "%LEGACY_DIR%" mkdir "%LEGACY_DIR%"
        
        huggingface-cli download Lightricks/ltx-video-distilled --local-dir %LEGACY_DIR%
        
        echo.
        echo All models downloaded!
        echo LTX-2: %MODELS_DIR%
        echo Legacy: %LEGACY_DIR%
        echo.
        
    ) else if "%MODEL_CHOICE%"=="3" (
        echo.
        echo WARNING: Legacy LTX is older and less capable than LTX-2.
        echo LTX-2 is strongly recommended for better quality and features.
        echo.
        set /p CONFIRM="Continue with legacy LTX? (y/N): "
        if /i not "%CONFIRM%"=="y" (
            echo Cancelled.
            goto :end_models
        )
        
        REM Check if huggingface-cli is available
        where huggingface-cli >nul 2>&1
        if %errorlevel% neq 0 (
            echo WARNING: huggingface-cli not found in PATH.
            echo Please install: pip install huggingface-hub
            pause
            goto :end_models
        )
        
        echo Downloading legacy LTX models...
        huggingface-cli download Lightricks/ltx-video-distilled --local-dir %MODELS_DIR%
        echo.
        echo Legacy models downloaded to: %MODELS_DIR%
        echo.
        
    ) else if "%MODEL_CHOICE%"=="4" (
        echo.
        echo ========================================
        echo   Manual Download Commands
        echo ========================================
        echo.
        echo LTX-2 (RECOMMENDED):
        echo huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-fp8.safetensors" --local-dir %MODELS_DIR%
        echo huggingface-cli download Lightricks/ltx-2 --include "ltx-2-spatial-upscaler-x2-1.0.safetensors" --local-dir %MODELS_DIR%
        echo huggingface-cli download Lightricks/ltx-2 --include "ltx-2-19b-distilled-lora-384.safetensors" --local-dir %MODELS_DIR%
        echo.
        echo Or download all LTX-2 files:
        echo huggingface-cli download Lightricks/ltx-2 --local-dir %MODELS_DIR%
        echo.
        echo Legacy LTX (not recommended):
        echo huggingface-cli download Lightricks/ltx-video-distilled --local-dir %MODELS_DIR%\legacy
        echo.
        echo Manual download URLs:
        echo LTX-2: https://huggingface.co/Lightricks/ltx-2
        echo Legacy: https://huggingface.co/spaces/Lightricks/ltx-video-distilled
        echo.
        
    ) else (
        echo Invalid choice. Showing manual commands...
        goto :end_models
    )
    
    :end_models
    
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
