# Content Factory - Cleanup Models from C:\ Drive
# This script finds and removes models that were incorrectly downloaded to C:\ drive

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cleanup Models from C:\ Drive" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$username = $env:USERNAME
$locationsToCheck = @(
    @{
        Path = "C:\Users\$username\.ollama\models"
        Description = "Ollama models"
        Size = 0
    },
    @{
        Path = "C:\Users\$username\AppData\Local\ollama"
        Description = "Ollama AppData"
        Size = 0
    },
    @{
        Path = "C:\Users\$username\.cache\huggingface"
        Description = "HuggingFace cache"
        Size = 0
    },
    @{
        Path = "C:\Users\$username\AppData\Local\huggingface"
        Description = "HuggingFace AppData"
        Size = 0
    },
    @{
        Path = "C:\Users\$username\.cache\transformers"
        Description = "Transformers cache"
        Size = 0
    },
    @{
        Path = "C:\Users\$username\.cache\torch"
        Description = "PyTorch cache"
        Size = 0
    }
)

Write-Host "Scanning C:\ drive for model files..." -ForegroundColor Yellow
Write-Host ""

$foundLocations = @()
$totalSize = 0

foreach ($location in $locationsToCheck) {
    if (Test-Path $location.Path) {
        Write-Host "[FOUND] $($location.Description):" -ForegroundColor Yellow
        Write-Host "  Path: $($location.Path)" -ForegroundColor Gray
        
        # Calculate size
        try {
            $size = (Get-ChildItem -Path $location.Path -Recurse -ErrorAction SilentlyContinue | 
                     Measure-Object -Property Length -Sum).Sum
            if ($size) {
                $sizeGB = [math]::Round($size / 1GB, 2)
                $location.Size = $sizeGB
                $totalSize += $sizeGB
                Write-Host "  Size: $sizeGB GB" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  Size: Could not calculate" -ForegroundColor Gray
        }
        
        # List contents
        try {
            $items = Get-ChildItem -Path $location.Path -ErrorAction SilentlyContinue | Select-Object -First 5
            if ($items) {
                Write-Host "  Contents:" -ForegroundColor Gray
                foreach ($item in $items) {
                    Write-Host "    - $($item.Name)" -ForegroundColor DarkGray
                }
                if ((Get-ChildItem -Path $location.Path -ErrorAction SilentlyContinue).Count -gt 5) {
                    Write-Host "    ... and more" -ForegroundColor DarkGray
                }
            }
        } catch {
            Write-Host "  Contents: Could not list" -ForegroundColor Gray
        }
        
        Write-Host ""
        $foundLocations += $location
    }
}

if ($foundLocations.Count -eq 0) {
    Write-Host "[OK] No model directories found on C:\ drive" -ForegroundColor Green
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  Summary" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Found $($foundLocations.Count) location(s) with models" -ForegroundColor White
Write-Host "Total size: $([math]::Round($totalSize, 2)) GB" -ForegroundColor White
Write-Host ""

Write-Host "WARNING: This will DELETE all models from these locations!" -ForegroundColor Red
Write-Host ""
Write-Host "Locations to be deleted:" -ForegroundColor Yellow
foreach ($loc in $foundLocations) {
    Write-Host "  - $($loc.Description) ($($loc.Size) GB)" -ForegroundColor White
}
Write-Host ""

$confirm = Read-Host "Are you sure you want to delete these? Type 'YES' to confirm"
if ($confirm -ne "YES") {
    Write-Host ""
    Write-Host "Cancelled. No files were deleted." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host ""
Write-Host "Deleting models..." -ForegroundColor Yellow
Write-Host ""

$deletedCount = 0
$deletedSize = 0

foreach ($location in $foundLocations) {
    Write-Host "Deleting: $($location.Description)..." -ForegroundColor Yellow
    try {
        $sizeBefore = 0
        if (Test-Path $location.Path) {
            $sizeBefore = (Get-ChildItem -Path $location.Path -Recurse -ErrorAction SilentlyContinue | 
                          Measure-Object -Property Length -Sum).Sum / 1GB
        }
        
        Remove-Item -Path $location.Path -Recurse -Force -ErrorAction Stop
        Write-Host "  [OK] Deleted: $($location.Path)" -ForegroundColor Green
        $deletedCount++
        $deletedSize += $sizeBefore
    } catch {
        Write-Host "  [ERROR] Failed to delete: $($location.Path)" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Deleted: $deletedCount location(s)" -ForegroundColor White
Write-Host "Freed: $([math]::Round($deletedSize, 2)) GB" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run setup_models.bat to download models to correct location (D:\Ideas\content_factory\models)" -ForegroundColor White
Write-Host "2. Run setup_ltx.bat to download LTX models to correct location" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
