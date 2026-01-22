# Content Factory - Run All Services
# Run as: .\run_all.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BASE_PATH = "D:\Ideas\content_factory"

# ============================================
# 1. Check Ollama
# ============================================
Write-Host "[1/4] Checking Ollama..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Write-Host "Ollama started" -ForegroundColor Green
}

# ============================================
# 2. Start Backend
# ============================================
Write-Host ""
Write-Host "[2/4] Starting Backend API..." -ForegroundColor Yellow

$backendPath = "$BASE_PATH\backend"
$venvPath = "$backendPath\venv\Scripts\python.exe"

# Check if venv exists
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found. Run install.ps1 first." -ForegroundColor Red
    exit 1
}

# Start backend in new window
$backendCmd = @"
cd "$backendPath"
& "$venvPath" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal
Write-Host "Backend starting on http://127.0.0.1:8000" -ForegroundColor Green

# Wait for backend to be ready
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
$retries = 0
$maxRetries = 30
while ($retries -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
        Write-Host "Backend is ready!" -ForegroundColor Green
        break
    } catch {
        $retries++
        Start-Sleep -Seconds 1
    }
}

if ($retries -eq $maxRetries) {
    Write-Host "Warning: Backend may not be fully ready yet" -ForegroundColor Yellow
}

# ============================================
# 3. Start Frontend
# ============================================
Write-Host ""
Write-Host "[3/4] Starting Frontend..." -ForegroundColor Yellow

$frontendPath = "$BASE_PATH\frontend"

# Start frontend in new window
$frontendCmd = @"
cd "$frontendPath"
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
Write-Host "Frontend starting on http://localhost:3000" -ForegroundColor Green

# Wait a moment for frontend to start
Start-Sleep -Seconds 5

# ============================================
# 4. Open Browser
# ============================================
Write-Host ""
Write-Host "[4/4] Opening dashboard..." -ForegroundColor Yellow

Start-Process "http://localhost:3000"

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory is Running!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor Yellow
Write-Host "  - Ollama:   http://localhost:11434" -ForegroundColor White
Write-Host "  - Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  - Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "To stop:" -ForegroundColor Yellow
Write-Host "  Close the PowerShell windows for backend and frontend" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
