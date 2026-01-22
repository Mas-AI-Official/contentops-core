# Content Factory - Installation Script
# Run as: .\install.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory - Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BASE_PATH = "D:\Ideas\content_factory"

# Check if running from correct location
if (-not (Test-Path "$BASE_PATH\ops")) {
    Write-Host "Error: Please run this script from the content_factory\ops directory" -ForegroundColor Red
    exit 1
}

# ============================================
# 1. Check Python
# ============================================
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Please install Python 3.11+" -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# ============================================
# 2. Create Python Virtual Environment
# ============================================
Write-Host ""
Write-Host "[2/6] Setting up Python virtual environment..." -ForegroundColor Yellow

$venvPath = "$BASE_PATH\backend\venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "Created virtual environment" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
}

# Activate venv and install dependencies
& "$venvPath\Scripts\Activate.ps1"

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r "$BASE_PATH\backend\requirements.txt"
Write-Host "Python dependencies installed" -ForegroundColor Green

# ============================================
# 3. Check FFmpeg
# ============================================
Write-Host ""
Write-Host "[3/6] Checking FFmpeg..." -ForegroundColor Yellow

$ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCheck) {
    Write-Host "FFmpeg not found. Attempting to install via winget..." -ForegroundColor Yellow
    try {
        winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        Write-Host "FFmpeg installed. You may need to restart your terminal." -ForegroundColor Green
    } catch {
        Write-Host "Could not auto-install FFmpeg." -ForegroundColor Red
        Write-Host "Please install manually from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
        Write-Host "Or via chocolatey: choco install ffmpeg" -ForegroundColor Yellow
    }
} else {
    Write-Host "FFmpeg found: $($ffmpegCheck.Source)" -ForegroundColor Green
}

# ============================================
# 4. Check Ollama
# ============================================
Write-Host ""
Write-Host "[4/6] Checking Ollama..." -ForegroundColor Yellow

$ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCheck) {
    Write-Host "Ollama not found." -ForegroundColor Yellow
    Write-Host "Please install Ollama from: https://ollama.ai/download" -ForegroundColor Yellow
    Write-Host "After installing, run: ollama serve" -ForegroundColor Yellow
} else {
    Write-Host "Ollama found: $($ollamaCheck.Source)" -ForegroundColor Green
}

# ============================================
# 5. Check Node.js and install frontend dependencies
# ============================================
Write-Host ""
Write-Host "[5/6] Setting up frontend..." -ForegroundColor Yellow

$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCheck) {
    Write-Host "Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    Write-Host "Download from: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

$nodeVersion = node --version
Write-Host "Found Node.js: $nodeVersion" -ForegroundColor Green

Set-Location "$BASE_PATH\frontend"
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
npm install
Write-Host "Frontend dependencies installed" -ForegroundColor Green

# ============================================
# 6. Create .env file if not exists
# ============================================
Write-Host ""
Write-Host "[6/6] Checking configuration..." -ForegroundColor Yellow

$envFile = "$BASE_PATH\backend\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item "$BASE_PATH\ops\env.example" $envFile
    Write-Host "Created .env file from template" -ForegroundColor Green
    Write-Host "Please edit $envFile to configure your settings" -ForegroundColor Yellow
} else {
    Write-Host ".env file already exists" -ForegroundColor Green
}

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start Ollama: ollama serve" -ForegroundColor White
Write-Host "2. Pull models: .\setup_models.ps1" -ForegroundColor White
Write-Host "3. Edit backend\.env with your API keys" -ForegroundColor White
Write-Host "4. Run the system: .\run_all.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Dashboard will be at: http://localhost:3000" -ForegroundColor Cyan
