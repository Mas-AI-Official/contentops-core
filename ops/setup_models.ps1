# Content Factory - Setup Models
# Downloads and configures AI models

param(
    [switch]$SkipOllama,
    [switch]$SkipLtx,
    [string[]]$Models = @("llama3.1:8b", "llama3.2:3b"),
    [int]$RetryCount = 3
)

$ErrorActionPreference = "Stop"

# Configuration
# PSScriptRoot is ops\ directory, so go up one level to get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
# Ensure absolute path
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$VenvPath = Join-Path $ProjectRoot "venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"
$ModelsDir = Join-Path $ProjectRoot "models"
$OllamaModelsDir = Join-Path $ModelsDir "ollama"
$LtxDir = Join-Path $ModelsDir "ltx"

# Ensure all paths are absolute
$ModelsDir = [System.IO.Path]::GetFullPath($ModelsDir)
$OllamaModelsDir = [System.IO.Path]::GetFullPath($OllamaModelsDir)
$LtxDir = [System.IO.Path]::GetFullPath($LtxDir)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory - Setup Models" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Models Directory: $ModelsDir"
Write-Host "Ollama Models: $OllamaModelsDir"
Write-Host "LTX Models: $LtxDir"
Write-Host ""

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Exit-WithError {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

# Check and activate venv
if (-not (Test-Path $VenvPython)) {
    Exit-WithError "Virtual environment not found at $VenvPath. Please run launch.bat or bootstrap_windows.ps1 first."
}

Write-Step "Activating virtual environment..."
$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    try {
        & $activateScript
        Write-Success "Virtual environment activated"
    }
    catch {
        Write-Warning "Could not activate venv via script, using venv Python directly"
    }
}
else {
    Write-Warning "Could not activate venv, using venv Python directly"
}

# Create directories
Write-Step "Creating model directories..."
$dirsToCreate = @($OllamaModelsDir, $LtxDir)
foreach ($dir in $dirsToCreate) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Model directories created"

# Setup Ollama models
if (-not $SkipOllama) {
    Write-Step "Setting up Ollama models..."

    # Check if Ollama is available
    try {
        $ollamaVersion = & ollama --version 2>&1
        Write-Success "Ollama found: $ollamaVersion"
    }
    catch {
        Write-Error "Ollama not found in PATH. Please install from https://ollama.com/download"
        Write-Host "You can download models manually or run this script after installing Ollama." -ForegroundColor Yellow
        $SkipOllama = $true
    }

    if (-not $SkipOllama) {
        # Set Ollama models directory (ensure it's absolute path)
        $OllamaModelsDir = [System.IO.Path]::GetFullPath($OllamaModelsDir)
        $env:OLLAMA_MODELS = $OllamaModelsDir
        
        # Set system-wide environment variable
        Write-Host "Setting OLLAMA_MODELS to: $OllamaModelsDir" -ForegroundColor Yellow
        try {
            [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $OllamaModelsDir, "User")
            Write-Success "OLLAMA_MODELS set system-wide"
        }
        catch {
            Write-Warning "Could not set OLLAMA_MODELS system-wide. It will only be set for this session."
        }

        # Check if Ollama is running and restart if needed
        Write-Host "Checking Ollama service..." -ForegroundColor Yellow
        $ollamaRunning = $false
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
            Write-Success "Ollama is running"
            $ollamaRunning = $true
        }
        catch {
            Write-Host "Ollama not running, starting..." -ForegroundColor Yellow
        }
        
        # If Ollama is already running, skip starting it
        # NOTE: If you need to change OLLAMA_MODELS, stop Ollama first manually
        if ($ollamaRunning) {
            Write-Host "Ollama is already running. Using existing instance." -ForegroundColor Green
            Write-Host "Downloads will work with the current Ollama setup." -ForegroundColor Gray
            Write-Host "NOTE: If you need to change OLLAMA_MODELS, stop Ollama first." -ForegroundColor Yellow
        }
        
        # Start Ollama with OLLAMA_MODELS environment variable only if not running
        if (-not $ollamaRunning) {
            Write-Host "Starting Ollama with OLLAMA_MODELS=$OllamaModelsDir..." -ForegroundColor Yellow
            Write-Host "IMPORTANT: Models will be saved to: $OllamaModelsDir" -ForegroundColor Cyan
            
            # Ensure directory exists
            if (-not (Test-Path $OllamaModelsDir)) {
                New-Item -ItemType Directory -Path $OllamaModelsDir -Force | Out-Null
                Write-Host "Created directory: $OllamaModelsDir" -ForegroundColor Green
            }
            
            # Set OLLAMA_MODELS in current session
            $env:OLLAMA_MODELS = $OllamaModelsDir
            
            # Create a batch file to start Ollama with environment variable
            $ollamaStartBat = Join-Path $env:TEMP "start_ollama_$(Get-Random).bat"
            @"
@echo off
set OLLAMA_MODELS=$OllamaModelsDir
cd /d "$ProjectRoot"
ollama serve
"@ | Out-File -FilePath $ollamaStartBat -Encoding ASCII
            
            # Start Ollama using the batch file
            Write-Host "Starting Ollama process..." -ForegroundColor Gray
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", "`"Ollama Service`"", "cmd", "/k", "`"$ollamaStartBat`"" -WindowStyle Hidden
            
            Start-Sleep -Seconds 8
            
            # Verify Ollama started
            $retries = 0
            $ollamaStarted = $false
            while ($retries -lt 10) {
                try {
                    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
                    Write-Success "Ollama started successfully"
                    $ollamaStarted = $true
                    break
                }
                catch {
                    $retries++
                    if ($retries -lt 10) {
                        Write-Host "Waiting for Ollama to start... ($retries/10)" -ForegroundColor Yellow
                        Start-Sleep -Seconds 2
                    }
                }
            }
            
            if (-not $ollamaStarted) {
                Write-Warning "Ollama did not start automatically. Please start it manually:"
                Write-Host "  set OLLAMA_MODELS=$OllamaModelsDir" -ForegroundColor Yellow
                Write-Host "  ollama serve" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "Or try running this script again after starting Ollama." -ForegroundColor Yellow
            }
        }

        # Verify Ollama is running before downloading
        Write-Host "Verifying Ollama is accessible..." -ForegroundColor Yellow
        $ollamaAccessible = $false
        try {
            $testResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
            Write-Success "Ollama is running and accessible"
            $ollamaAccessible = $true
        }
        catch {
            Write-Warning "Ollama is not running or not accessible."
            Write-Host "If Ollama is already running, downloads will still work." -ForegroundColor Yellow
            Write-Host "If not, please start Ollama manually:" -ForegroundColor Yellow
            Write-Host "  set OLLAMA_MODELS=$OllamaModelsDir" -ForegroundColor Cyan
            Write-Host "  ollama serve" -ForegroundColor Cyan
        }
        
        # Download models (even if Ollama check failed, try anyway)
        Write-Host ""
        Write-Host "Starting model downloads..." -ForegroundColor Yellow
        Write-Host "Models will be saved to: $OllamaModelsDir" -ForegroundColor Cyan
        Write-Host ""
        
        foreach ($model in $Models) {
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host "Downloading $model..." -ForegroundColor Yellow
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host "This may take several minutes depending on your connection..." -ForegroundColor Gray
            Write-Host ""

            $success = $false
            for ($i = 1; $i -le $RetryCount; $i++) {
                try {
                    # Set OLLAMA_MODELS for the pull command
                    $env:OLLAMA_MODELS = $OllamaModelsDir
                    
                    Write-Host "Attempt $i of $RetryCount..." -ForegroundColor Gray
                    
                    # Run ollama pull - let it show progress in console
                    $process = Start-Process -FilePath "ollama" -ArgumentList "pull", $model -NoNewWindow -Wait -PassThru
                    
                    if ($process.ExitCode -eq 0) {
                        Write-Success "$model downloaded successfully"
                        $success = $true
                        break
                    }
                    else {
                        Write-Warning "Attempt $i failed for $model (exit code: $($process.ExitCode))"
                        if ($i -lt $RetryCount) {
                            Write-Host "This might be a network issue. Retrying in 5 seconds..." -ForegroundColor Yellow
                        }
                    }
                }
                catch {
                    Write-Warning "Attempt $i failed for $model`: $($_.Exception.Message)"
                }

                if ($i -lt $RetryCount) {
                    Start-Sleep -Seconds 5
                }
            }

            if (-not $success) {
                Write-Error "Failed to download $model after $RetryCount attempts"
                Write-Host "You can try manually:" -ForegroundColor Yellow
                Write-Host "  set OLLAMA_MODELS=$OllamaModelsDir" -ForegroundColor Cyan
                Write-Host "  ollama pull $model" -ForegroundColor Cyan
            }
            Write-Host ""
        }

        # Verify models
        Write-Host "Verifying installed models..." -ForegroundColor Yellow
        try {
            $modelsList = & ollama list
            Write-Host "Installed models:" -ForegroundColor Gray
            Write-Host $modelsList -ForegroundColor Gray
        }
        catch {
            Write-Warning "Could not verify installed models"
        }
        
        # Verify model files location
        Write-Host ""
        Write-Host "Verifying model file locations..." -ForegroundColor Yellow
        Write-Host "OLLAMA_MODELS is set to: $OllamaModelsDir" -ForegroundColor Cyan
        
        if (Test-Path $OllamaModelsDir) {
            $modelFiles = Get-ChildItem -Path $OllamaModelsDir -Recurse -ErrorAction SilentlyContinue
            if ($modelFiles) {
                Write-Success "Found $($modelFiles.Count) file(s) in: $OllamaModelsDir"
                $totalSize = ($modelFiles | Measure-Object -Property Length -Sum).Sum / 1GB
                Write-Host "Total size: $([math]::Round($totalSize, 2)) GB" -ForegroundColor Gray
            }
            else {
                Write-Host "No model files found yet in: $OllamaModelsDir" -ForegroundColor Yellow
                Write-Host "Models may be in default Ollama location, which is OK." -ForegroundColor Gray
            }
        }
        else {
            Write-Warning "Models directory does not exist: $OllamaModelsDir"
        }
    }
}

# Setup LTX models
if (-not $SkipLtx) {
    Write-Step "Setting up LTX models..."

    # Check if huggingface_hub is available (use venv Python)
    Write-Host "Checking for huggingface_hub..." -ForegroundColor Yellow
    $hfAvailable = $false
    try {
        $importTest = & $VenvPython -c "import huggingface_hub; print('OK')" 2>&1
        if ($LASTEXITCODE -eq 0 -and $importTest -match "OK") {
            Write-Success "huggingface_hub is available"
            $hfAvailable = $true
        }
        else {
            Write-Host "huggingface_hub not found. Installing..." -ForegroundColor Yellow
            & $VenvPip install huggingface-hub --upgrade 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "huggingface_hub installed"
                $hfAvailable = $true
            }
            else {
                throw "Failed to install huggingface_hub"
            }
        }
    }
    catch {
        Write-Error "Failed to setup huggingface_hub: $($_.Exception.Message)"
        $SkipLtx = $true
    }

    if (-not $SkipLtx) {
        Write-Host "LTX-2 models for RTX 4060 (8GB VRAM):" -ForegroundColor Cyan
        Write-Host "- Main model: ltx-2-19b-distilled-fp8.safetensors" -ForegroundColor White
        Write-Host "- Upscaler: ltx-2-spatial-upscaler-x2-1.0.safetensors" -ForegroundColor White
        Write-Host "- LoRA: ltx-2-19b-distilled-lora-384.safetensors" -ForegroundColor White
        Write-Host ""

        $modelsToDownload = @(
            "Lightricks/ltx-2:ltx-2-19b-distilled-fp8.safetensors",
            "Lightricks/ltx-2:ltx-2-spatial-upscaler-x2-1.0.safetensors",
            "Lightricks/ltx-2:ltx-2-19b-distilled-lora-384.safetensors"
        )

        $downloadScript = Join-Path $PSScriptRoot "download_hf_model.py"

        foreach ($modelSpec in $modelsToDownload) {
            $repo, $filename = $modelSpec -split ":"
            Write-Host "Downloading $filename from $repo..." -ForegroundColor Yellow

            try {
                $process = Start-Process -FilePath $VenvPython -ArgumentList $downloadScript, $repo, $filename, $LtxDir -NoNewWindow -Wait -PassThru
                if ($process.ExitCode -eq 0) {
                    Write-Success "$filename downloaded"
                }
                else {
                    Write-Error "Failed to download $filename (exit code: $($process.ExitCode))"
                }
            }
            catch {
                Write-Error "Error downloading $filename`: $($_.Exception.Message)"
            }
        }

    }

    # Verify LTX models
    $ltxFiles = Get-ChildItem -Path $LtxDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
    if ($ltxFiles) {
        Write-Success "LTX models downloaded: $($ltxFiles.Count) files"
        foreach ($file in $ltxFiles) {
            Write-Host "  - $($file.Name) ($([math]::Round($file.Length / 1GB, 2)) GB)" -ForegroundColor Gray
        }
    }
    else {
        Write-Warning "No LTX model files found. Download may have failed."
    }
}


Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Model Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

if (-not $SkipOllama) {
    Write-Host "Ollama models: $OllamaModelsDir" -ForegroundColor White
}

if (-not $SkipLtx) {
    Write-Host "LTX models: $LtxDir" -ForegroundColor White
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "- Run the application: .\ops\run_all.ps1" -ForegroundColor White
Write-Host "- Configure niches in the web interface" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")