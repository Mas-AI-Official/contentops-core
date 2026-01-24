@echo off
title Content Factory - Setup LTX-2 Video Model
color 0E

setlocal enabledelayedexpansion

REM Set Root to parent directory
pushd "%~dp0.."
set ROOT=%CD%
popd

set LTX_DIR=%ROOT%\LTX-2
set MODELS_DIR=%ROOT%\models\ltx
set LOG_FILE=%ROOT%\data\logs\setup_ltx.log

REM Ensure logs directory exists
if not exist "%ROOT%\data\logs" mkdir "%ROOT%\data\logs"

echo ========================================
echo   Content Factory - Setup LTX-2
echo ========================================
echo.
echo Root: %ROOT%
echo LTX-2 Directory: %LTX_DIR%
echo Models Directory: %MODELS_DIR%
echo Log File: %LOG_FILE%
echo.

REM Function to log messages
call :log "Starting LTX-2 setup..."

echo This will install LTX-2 from the official repository:
echo https://github.com/Lightricks/LTX-2
echo.
echo NOTE: LTX models are LARGE - several GB.
echo For RTX 4060 8GB: Use distilled/FP8 models, max 480p, 3-5 seconds.
echo.

cd /d %ROOT%

REM Ensure models directory exists
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

REM Check if venv exists
set VENV_PYTHON=%ROOT%\venv\Scripts\python.exe
set VENV_PIP=%ROOT%\venv\Scripts\pip.exe

if not exist "%VENV_PYTHON%" (
    call :log "ERROR: Virtual environment not found."
    echo.
    echo ========================================
    echo ERROR: Virtual environment not found.
    echo ========================================
    echo.
    echo Please run launch.bat first to create the virtual environment.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    call :log "ERROR: Failed to activate virtual environment."
    echo.
    echo ========================================
    echo ERROR: Failed to activate virtual environment.
    echo ========================================
    echo.
    echo The venv may be corrupted. Please run launch.bat to recreate it.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
call :log "Virtual environment activated."
echo [OK] Virtual environment activated.
echo.

REM Verify environment is working
echo ========================================
echo   Verifying Environment
echo ========================================
echo.
echo Checking Python version...
"%VENV_PYTHON%" --version
if %errorlevel% neq 0 (
    call :log "ERROR: Python in venv is not working!"
    echo ERROR: Python in venv is not working!
    pause
    exit /b 1
)

echo Checking for dependency conflicts...
"%VENV_PIP%" check
if %errorlevel% neq 0 (
    call :log "WARNING: Dependency conflicts detected."
    echo WARNING: Dependency conflicts detected!
    echo This may cause issues. Consider recreating the venv.
    echo.
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" (
        echo Cancelled.
        pause
        exit /b 1
    )
) else (
    echo [OK] No dependency conflicts detected.
)
echo.

REM Install uv if not available
echo Checking for uv package manager...
"%VENV_PYTHON%" -c "import uv" >nul 2>&1
if %errorlevel% neq 0 (
    echo uv not found in venv. Installing uv...
    "%VENV_PIP%" install uv --quiet
    if %errorlevel% neq 0 (
        call :log "WARNING: Failed to install uv. Will use pip instead."
        echo WARNING: Failed to install uv. Will use pip instead.
        set USE_UV=0
    ) else (
        echo [OK] uv installed in virtual environment.
        set USE_UV=1
    )
) else (
    echo [OK] uv found in virtual environment.
    set USE_UV=1
)
echo.

REM Check if uv command is available
where uv >nul 2>&1
if %errorlevel% equ 0 (
    set USE_UV=1
    echo [OK] uv command available in PATH.
) else (
    if %USE_UV% equ 1 (
        echo [INFO] uv installed in venv but not in PATH. Will use python -m uv
        set UV_CMD="%VENV_PYTHON%" -m uv
    ) else (
        echo [INFO] uv not available. Will use pip instead.
        set UV_CMD=
    )
)
echo.

echo ========================================
echo   Step 1: Clone LTX-2 Repository
echo ========================================
echo.

if exist "%LTX_DIR%" (
    call :log "LTX-2 directory already exists. Using existing."
    echo LTX-2 directory already exists: %LTX_DIR%
    echo.
    echo Using existing repository. To update, delete the directory and run again.
    echo.
) else (
    call :log "Cloning LTX-2 repository..."
    echo Cloning LTX-2 repository...
    echo This may take a moment...
    git clone https://github.com/Lightricks/LTX-2.git
    if %errorlevel% neq 0 (
        call :log "ERROR: Failed to clone LTX-2 repository."
        echo.
        echo ========================================
        echo ERROR: Failed to clone LTX-2 repository.
        echo ========================================
        echo.
        echo Please check your internet connection and try again.
        echo.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
    REM Verify the directory was created
    if exist "%LTX_DIR%" (
        echo [OK] Repository cloned successfully.
    ) else (
        call :log "ERROR: Repository cloned but directory not found."
        echo.
        echo ========================================
        echo ERROR: Repository cloned but directory not found.
        echo ========================================
        echo.
        echo Please check the error messages above.
        echo.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
)
echo.

echo ========================================
echo   Step 2: Install LTX-2 Dependencies
echo ========================================
echo.

cd /d "%LTX_DIR%"

if %USE_UV% equ 1 (
    call :log "Installing dependencies with uv..."
    echo Installing dependencies with uv...
    echo This may take several minutes...
    echo.
    echo NOTE: Using --active flag to use existing venv instead of creating new one.
    echo.
    if defined UV_CMD (
        %UV_CMD% sync --frozen --active --link-mode=copy
    ) else (
        uv sync --frozen --active --link-mode=copy
    )
    if %errorlevel% neq 0 (
        call :log "WARNING: uv sync failed. Trying with pip..."
        echo.
        echo WARNING: uv sync failed. Trying with pip...
        echo.
        "%VENV_PIP%" install -e packages/ltx-core -e packages/ltx-pipelines
        if %errorlevel% neq 0 (
            call :log "ERROR: Failed to install dependencies."
            echo.
            echo ========================================
            echo ERROR: Failed to install dependencies.
            echo ========================================
            echo.
            echo Please check the error messages above.
            echo.
            echo Press any key to exit...
            pause >nul
            exit /b 1
        )
    ) else (
        echo [OK] Dependencies installed with uv.
    )
) else (
    call :log "Installing dependencies with pip..."
    echo Installing dependencies with pip...
    echo This may take several minutes...
    echo.
    "%VENV_PIP%" install -e packages/ltx-core -e packages/ltx-pipelines
    if %errorlevel% neq 0 (
        call :log "ERROR: Failed to install dependencies."
        echo.
        echo ========================================
        echo ERROR: Failed to install dependencies.
        echo ========================================
        echo.
        echo Please check the error messages above.
        echo.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
    echo [OK] Dependencies installed with pip.
)
echo.

cd /d "%ROOT%"

echo ========================================
echo   Step 3: Download LTX-2 Models
echo ========================================
echo.
echo LTX-2 requires model files to be downloaded.
echo.
echo For RTX 4060 8GB, we recommend:
echo   - ltx-2-19b-distilled-fp8.safetensors (main model)
echo   - ltx-2-spatial-upscaler-x2-1.0.safetensors (upscaler)
echo   - ltx-2-19b-distilled-lora-384.safetensors (LoRA)
echo.
set DOWNLOAD_MODELS=
set /p DOWNLOAD_MODELS="Download models now? (Y/n): "

REM Handle empty input (default to Yes)
if "!DOWNLOAD_MODELS!"=="" set DOWNLOAD_MODELS=Y

REM Normalize: convert lowercase y/yes to Y
if /i "!DOWNLOAD_MODELS!"=="y" set DOWNLOAD_MODELS=Y
if /i "!DOWNLOAD_MODELS!"=="yes" set DOWNLOAD_MODELS=Y

REM Check if user wants to download
if /i "!DOWNLOAD_MODELS!"=="n" goto skip_download

REM User wants to download
echo.
echo Checking for huggingface-hub...
"%VENV_PYTHON%" -c "import huggingface_hub" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing huggingface-hub...
    echo NOTE: Dependency conflicts are warnings, not errors. Installation will continue...
    "%VENV_PIP%" install huggingface-hub[cli] --quiet
    if %errorlevel% neq 0 (
        echo WARNING: pip reported errors, but checking if module is available anyway...
    )
    REM Verify installation by importing
    "%VENV_PYTHON%" -c "import huggingface_hub; print('OK')" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] huggingface-hub is available and working.
    ) else (
        echo [WARNING] huggingface-hub installation had issues, but continuing...
        echo You may need to install manually: "%VENV_PIP%" install huggingface-hub[cli]
    )
)

echo.
call :log "Starting model download..."
echo Starting model download...
echo Models will be saved to: %MODELS_DIR%
echo.
echo This will download large files - several GB. This may take a long time...
echo.

REM Initialize download exit code
set DOWNLOAD_EXIT=1

REM Check if download script exists
if not exist "%ROOT%\download_ltx_models.py" (
    if not exist "%ROOT%\download_ltx_simple.py" (
        goto manual_download
    )
)

REM Use the simple Python download script
if exist "%ROOT%\download_ltx_simple.py" (
    echo Using simple download script: download_ltx_simple.py
    echo.
    echo This will download essential LTX-2 models with progress bars.
    echo Each model is 5-20GB - this may take hours.
    echo.
    echo Press Ctrl+C to cancel if needed (partial downloads are saved).
    echo.
    echo.
    echo Executing download script...
    call "%VENV_PYTHON%" "%ROOT%\download_ltx_simple.py"
    if errorlevel 1 (
        set DOWNLOAD_EXIT=1
    ) else (
        set DOWNLOAD_EXIT=0
    )
) else (
    echo Simple download script not found, using original...
    echo Using download script: download_ltx_models.py
    echo.
    echo IMPORTANT: This will download ALL LTX-2 models - several GB.
    echo The script will show progress and may take a long time.
    echo.
    echo Starting download...
    echo.
    echo Press Ctrl+C to cancel if needed.
    echo.
    call "%VENV_PYTHON%" "%ROOT%\download_ltx_models.py"
    if errorlevel 1 (
        set DOWNLOAD_EXIT=1
    ) else (
        set DOWNLOAD_EXIT=0
    )
)
echo.
echo Download script finished with exit code: !DOWNLOAD_EXIT!
echo.
if "!DOWNLOAD_EXIT!"=="0" goto download_ok
goto download_failed

:download_ok
call :log "Models downloaded successfully."
echo.
echo [OK] Models downloaded successfully!
goto download_done

:download_failed
call :log "WARNING: Model download had errors."
echo.
echo [WARNING] Model download had errors. Check messages above.
echo Exit code: !DOWNLOAD_EXIT!
echo.
echo You can run the download script manually:
if exist "%ROOT%\download_ltx_simple.py" (
    echo   "%VENV_PYTHON%" "%ROOT%\download_ltx_simple.py"
) else (
    echo   "%VENV_PYTHON%" "%ROOT%\download_ltx_models.py"
)
goto download_done

:manual_download
call :log "Downloading manually..."
echo Download script not found. Downloading manually using helper script...
echo.
echo Downloading main model: ltx-2-19b-distilled-fp8.safetensors
"%VENV_PYTHON%" "%ROOT%\ops\download_hf_model.py" Lightricks/ltx-2 ltx-2-19b-distilled-fp8.safetensors "%MODELS_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download main model
)
echo.
echo Downloading upscaler: ltx-2-spatial-upscaler-x2-1.0.safetensors
"%VENV_PYTHON%" "%ROOT%\ops\download_hf_model.py" Lightricks/ltx-2 ltx-2-spatial-upscaler-x2-1.0.safetensors "%MODELS_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download upscaler
)
echo.
echo Downloading LoRA: ltx-2-19b-distilled-lora-384.safetensors
"%VENV_PYTHON%" "%ROOT%\ops\download_hf_model.py" Lightricks/ltx-2 ltx-2-19b-distilled-lora-384.safetensors "%MODELS_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download LoRA
)
goto download_done

:skip_download
call :log "Skipping model download."
echo Skipping model download.
echo You can download models later using: python download_ltx_models.py
echo.
goto download_done

:download_done

call :log "Setup complete."
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo LTX-2 has been installed to: %LTX_DIR%
echo.
echo Next steps:
echo.
echo 1. Models location: %MODELS_DIR%
echo    Make sure models are downloaded before using LTX-2.
echo.
echo 2. To use LTX-2 in your application:
echo    - Set in backend\.env: VIDEO_GEN_PROVIDER=ltx
echo    - Set in backend\.env: LTX_MODEL_PATH=%MODELS_DIR%
echo    - Set in backend\.env: LTX_REPO_PATH=%LTX_DIR%
echo.
echo 3. Example Python usage:
echo    cd %LTX_DIR%
echo    python -c "from ltx_pipelines import TI2VidTwoStagesPipeline; print('LTX-2 ready!')"
echo.
echo 4. For optimization - RTX 4060 8GB:
echo    - Use DistilledPipeline for fastest inference
echo    - Enable FP8: --enable-fp8 or fp8transformer=True
echo    - Use max 480p resolution, 3-5 second videos
echo.
echo Documentation: https://github.com/Lightricks/LTX-2
echo.
echo ========================================
echo   Press any key to exit...
echo ========================================
pause >nul
exit /b 0

:log
echo [%date% %time%] %~1 >> "%LOG_FILE%"
exit /b
