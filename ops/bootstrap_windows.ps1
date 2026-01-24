# Content Factory Bootstrap Script for Windows
# This script sets up the entire development environment

param(
    [switch]$Force,
    [switch]$SkipDeps,
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonVersion = "3.11.9"
$VenvPath = Join-Path $ProjectRoot "venv"
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory Bootstrap" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Root: $ProjectRoot"
Write-Host "Python Version Required: $PythonVersion"
Write-Host "Virtual Environment: $VenvPath"
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
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Check Python version
Write-Step "Checking Python version..."
$PythonPath = "C:\Python311\python.exe"

# First check if Python 3.11 exists at the specified path
if (Test-Path $PythonPath) {
    try {
        $pythonVersion = & $PythonPath --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            $patch = [int]$matches[3]

            if ($major -eq 3 -and $minor -eq 11) {
                Write-Success "Python $pythonVersion found at $PythonPath"
                $env:PYTHON = $PythonPath
            } else {
                Exit-WithError "Python $pythonVersion found at $PythonPath, but Python 3.11 is required."
            }
        } else {
            throw "Could not parse Python version"
        }
    } catch {
        Exit-WithError "Python found at $PythonPath but could not get version"
    }
} else {
    # Fallback to checking PATH
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            $patch = [int]$matches[3]

            if ($major -eq 3 -and $minor -ge 11) {
                Write-Success "Python $pythonVersion found in PATH (3.11+ required)"
                $PythonPath = "python"
            } else {
                Exit-WithError "Python $pythonVersion found in PATH, but Python 3.11 is required. Please install Python 3.11 at C:\Python311"
            }
        } else {
            throw "Could not parse Python version"
        }
    } catch {
        Exit-WithError "Python not found at C:\Python311 or in PATH. Please install Python 3.11 at C:\Python311"
    }
}

# Create virtual environment
Write-Step "Setting up virtual environment..."
if ((Test-Path $VenvPath) -and $Force) {
    Write-Host "Removing existing venv..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvPath -ErrorAction SilentlyContinue
}

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..."
    if ($PythonPath -eq "python") {
        & python -m venv $VenvPath
    } else {
        & $PythonPath -m venv $VenvPath
    }
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Failed to create virtual environment"
    }
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment already exists"
}

# Activate venv and upgrade pip
Write-Step "Activating virtual environment..."
$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
$venvPip = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $activateScript)) {
    Exit-WithError "Virtual environment activation script not found"
}

if (-not (Test-Path $venvPython)) {
    Exit-WithError "Virtual environment Python not found at $venvPython"
}

try {
    & $activateScript
    Write-Success "Virtual environment activated"
} catch {
    Write-Warning "Could not activate venv via script, using venv Python directly"
}

# Upgrade pip using venv Python
Write-Step "Upgrading pip..."
& $venvPython -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Failed to upgrade pip, continuing..."
}

# Install backend dependencies
if (-not $SkipDeps) {
    Write-Step "Installing backend dependencies..."
    Set-Location $BackendPath
    & pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Failed to install backend dependencies"
    }
    Write-Success "Backend dependencies installed"

    # Install frontend dependencies
    Write-Step "Installing frontend dependencies..."
    Set-Location $FrontendPath
    if (Test-Path "package.json") {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            Exit-WithError "Failed to install frontend dependencies"
        }
        Write-Success "Frontend dependencies installed"
    } else {
        Write-Warning "package.json not found, skipping frontend setup"
    }
}

# Setup model directories
Write-Step "Setting up model directories..."
$modelsDir = Join-Path $ProjectRoot "models"
$ollamaModelsDir = Join-Path $modelsDir "ollama"
$whisperHfDir = Join-Path $modelsDir "whisper\hf"
$xttsDir = Join-Path $modelsDir "xtts"
$torchDir = Join-Path $modelsDir "torch"
$cacheDir = Join-Path $modelsDir "cache"
$imageDir = Join-Path $modelsDir "image"
$ltxDir = Join-Path $modelsDir "ltx"

$dirsToCreate = @($ollamaModelsDir, $whisperHfDir, $xttsDir, $torchDir, $cacheDir, $imageDir, $ltxDir)

foreach ($dir in $dirsToCreate) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Success "Model directories created"

# Set environment variables
Write-Step "Setting environment variables..."
$env:OLLAMA_MODELS = $ollamaModelsDir
$env:HF_HOME = $whisperHfDir
$env:TORCH_HOME = $torchDir
$env:XDG_CACHE_HOME = $cacheDir

# Set system environment variables
try {
    [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ollamaModelsDir, "User")
    [Environment]::SetEnvironmentVariable("HF_HOME", $whisperHfDir, "User")
    [Environment]::SetEnvironmentVariable("TORCH_HOME", $torchDir, "User")
    [Environment]::SetEnvironmentVariable("XDG_CACHE_HOME", $cacheDir, "User")
    Write-Success "Environment variables set"
} catch {
    Write-Warning "Could not set system environment variables. They will only be set for this session."
}

# Setup models if not skipped
if (-not $SkipModels) {
    Write-Step "Setting up Ollama models..."
    Set-Location $ProjectRoot

    # Check if Ollama is available
    try {
        $ollamaVersion = & ollama --version 2>&1
        Write-Success "Ollama found: $ollamaVersion"
    } catch {
        Write-Warning "Ollama not found in PATH. Please install from https://ollama.com/download"
        Write-Host "You can run setup models later with: .\ops\setup_models.ps1" -ForegroundColor Cyan
    }

    if ($ollamaVersion) {
        # Download models
        $models = @("llama3.1:8b", "llama3.2:3b")

        foreach ($model in $models) {
            Write-Host "Downloading $model..." -ForegroundColor Yellow
            try {
                & ollama pull $model
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "$model downloaded"
                } else {
                    Write-Warning "Failed to download $model"
                }
            } catch {
                Write-Warning "Error downloading $model`: $($_.Exception.Message)"
            }
        }
    }
}

# Create .python-version file
Write-Step "Creating .python-version file..."
$pythonVersionFile = Join-Path $ProjectRoot ".python-version"
$PythonVersion | Out-File -FilePath $pythonVersionFile -Encoding UTF8
Write-Success ".python-version created"

# Run database migrations/init
Write-Step "Initializing database..."
Set-Location $BackendPath
try {
    & $venvPython -c "from app.db.database import init_db; init_db(); print('Database initialized')"
    Write-Success "Database initialized"
} catch {
    Write-Warning "Could not initialize database: $($_.Exception.Message)"
}

# Run database migrations
Write-Step "Running database migrations..."
try {
    & $venvPython scripts/migrate_db.py
    Write-Success "Database migrations completed"
} catch {
    Write-Warning "Database migration failed: $($_.Exception.Message)"
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Bootstrap Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run the application: .\ops\run_all.ps1" -ForegroundColor White
Write-Host "2. Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "3. Set up your first niche in the Settings page" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "- Setup models: .\ops\setup_models.ps1" -ForegroundColor White
Write-Host "- Run backend only: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "- Run frontend only: cd frontend && npm run dev" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")