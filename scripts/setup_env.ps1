# Content Factory - Environment Setup Script
# Creates venv, installs dependencies, and ensures everything is ready.

$ErrorActionPreference = "Stop"
$Root = "D:\Ideas\content_factory"
$VenvPath = "$Root\venv"
$LogsDir = "$Root\data\logs"

# Ensure logs directory exists
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$LogFile = "$LogsDir\setup_env.log"

function Log-Message {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$Timestamp] $Message"
    Write-Host $Message -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value $LogLine
}

Log-Message "Starting environment setup..."

# 1. Check Python Version
$PythonVersion = python --version 2>&1
Log-Message "System Python: $PythonVersion"

if ($PythonVersion -notmatch "3\.11") {
    Log-Message "WARNING: Python 3.11 is recommended. You are using $PythonVersion"
}

# 2. Create Virtual Environment
if (-not (Test-Path $VenvPath)) {
    Log-Message "Creating virtual environment at $VenvPath..."
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        Log-Message "ERROR: Failed to create venv."
        exit 1
    }
    Log-Message "Virtual environment created."
}
else {
    Log-Message "Virtual environment already exists."
}

# 3. Install Dependencies
$Pip = "$VenvPath\Scripts\pip.exe"
$Python = "$VenvPath\Scripts\python.exe"

Log-Message "Upgrading pip..."
& $Pip install --upgrade pip | Out-Null

Log-Message "Installing dependencies from backend/requirements.txt..."
if (Test-Path "$Root\backend\requirements.txt") {
    & $Pip install -r "$Root\backend\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Log-Message "ERROR: Failed to install dependencies."
        exit 1
    }
}
else {
    Log-Message "ERROR: backend/requirements.txt not found!"
    exit 1
}

# 4. Install missing critical packages explicitly
Log-Message "Verifying critical packages..."
$Packages = @("httpx", "playwright", "loguru", "sqlmodel", "fastapi", "uvicorn", "python-multipart", "jinja2")
foreach ($pkg in $Packages) {
    & $Pip install $pkg
}

# 5. Install Playwright browsers
Log-Message "Installing Playwright browsers..."
& $Python -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Log-Message "WARNING: Failed to install Playwright browsers. You may need to run 'playwright install' manually."
}

Log-Message "Setup complete! You can now run the application."
Log-Message "To start: scripts\start_all.ps1"
