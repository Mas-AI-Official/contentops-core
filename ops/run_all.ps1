# Content Factory - Run All Services
# Starts both backend and frontend services

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$VenvPath = Join-Path $ProjectRoot "venv"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory - Run All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Root: $ProjectRoot"
Write-Host "Backend Port: $BackendPort"
Write-Host "Frontend Port: $FrontendPort"
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

# Check if virtual environment exists
if (-not (Test-Path $VenvPath)) {
    Exit-WithError "Virtual environment not found at $VenvPath. Please run .\ops\bootstrap_windows.ps1 first."
}

# Activate virtual environment
Write-Step "Activating virtual environment..."
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Exit-WithError "Virtual environment Python not found at $venvPython"
}

try {
    $activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Success "Virtual environment activated"
    } else {
        Write-Warning "Could not activate venv via script, using venv Python directly"
    }
} catch {
    Write-Warning "Could not activate venv via script, using venv Python directly"
}

# Set environment variables
$modelsDir = Join-Path $ProjectRoot "models"
$ollamaModelsDir = Join-Path $modelsDir "ollama"
$whisperHfDir = Join-Path $modelsDir "whisper\hf"
$torchDir = Join-Path $modelsDir "torch"
$cacheDir = Join-Path $modelsDir "cache"

$env:OLLAMA_MODELS = $ollamaModelsDir
$env:HF_HOME = $whisperHfDir
$env:TORCH_HOME = $torchDir
$env:XDG_CACHE_HOME = $cacheDir

# Start backend
if (-not $FrontendOnly) {
    Write-Step "Starting backend server..."
    $backendJob = Start-Job -ScriptBlock {
        param($BackendPath, $BackendPort, $OllamaModels, $HfHome, $TorchHome, $XdgCache, $VenvPython)
        Set-Location $BackendPath
        $env:OLLAMA_MODELS = $OllamaModels
        $env:HF_HOME = $HfHome
        $env:TORCH_HOME = $TorchHome
        $env:XDG_CACHE_HOME = $XdgCache
        & $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload
    } -ArgumentList $BackendPath, $BackendPort, $ollamaModelsDir, $whisperHfDir, $torchDir, $cacheDir, $venvPython

    Start-Sleep -Seconds 2

    # Check if backend started
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/docs" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Backend started on http://localhost:$BackendPort"
        Write-Host "  API Docs: http://localhost:$BackendPort/docs" -ForegroundColor Gray
    } catch {
        Write-Error "Backend failed to start or is not responding"
        Write-Host "Check the backend job for errors:" -ForegroundColor Yellow
        Receive-Job -Job $backendJob -Keep
        exit 1
    }
}

# Start frontend
if (-not $BackendOnly) {
    Write-Step "Starting frontend server..."
    Set-Location $FrontendPath

    if (-not (Test-Path "package.json")) {
        Exit-WithError "package.json not found in frontend directory"
    }

    $frontendJob = Start-Job -ScriptBlock {
        param($FrontendPath)
        Set-Location $FrontendPath
        & npm run dev
    } -ArgumentList $FrontendPath

    Start-Sleep -Seconds 3

    # Check if frontend started (may take longer)
    $frontendStarted = $false
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -TimeoutSec 2 -ErrorAction Stop
            Write-Success "Frontend started on http://localhost:$FrontendPort"
            $frontendStarted = $true
            break
        } catch {
            Write-Host "Waiting for frontend... ($($i + 1)/10)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }

    if (-not $frontendStarted) {
        Write-Error "Frontend failed to start"
        Write-Host "Check the frontend job for errors:" -ForegroundColor Yellow
        Receive-Job -Job $frontendJob -Keep
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

if (-not $FrontendOnly) {
    Write-Host "Backend:  http://localhost:$BackendPort" -ForegroundColor White
    Write-Host "API Docs: http://localhost:$BackendPort/docs" -ForegroundColor White
}

if (-not $BackendOnly) {
    Write-Host "Frontend: http://localhost:$FrontendPort" -ForegroundColor White
}

Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Wait for jobs to complete
try {
    while ($true) {
        Start-Sleep -Seconds 1

        # Check if jobs are still running
        if ((-not $FrontendOnly) -and ($backendJob.State -ne "Running")) {
            Write-Error "Backend job stopped unexpectedly"
            Receive-Job -Job $backendJob
            break
        }

        if ((-not $BackendOnly) -and ($frontendJob.State -ne "Running")) {
            Write-Error "Frontend job stopped unexpectedly"
            Receive-Job -Job $frontendJob
            break
        }
    }
} finally {
    # Cleanup jobs
    Write-Host "Stopping services..." -ForegroundColor Yellow
    if ($backendJob) {
        Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $backendJob -ErrorAction SilentlyContinue
    }
    if ($frontendJob) {
        Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $frontendJob -ErrorAction SilentlyContinue
    }
}