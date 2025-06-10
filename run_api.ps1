# PowerShell script to test and run the new Async PocketOption API
# Run this script from the project root directory

param(
    [string]$Command = "test",
    [string]$SessionId = "",
    [switch]$Demo = $true,
    [switch]$Help
)

function Show-Help {
    Write-Host "PocketOption Async API - PowerShell Helper Script" -ForegroundColor Cyan
    Write-Host "=" * 50 -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run_api.ps1 [command] [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  test         - Run API tests (default)" -ForegroundColor White
    Write-Host "  install      - Install dependencies" -ForegroundColor White
    Write-Host "  example      - Run basic example" -ForegroundColor White
    Write-Host "  migrate      - Show migration guide" -ForegroundColor White
    Write-Host "  help         - Show this help" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -SessionId   - Your PocketOption session ID" -ForegroundColor White
    Write-Host "  -Demo        - Use demo account (default: true)" -ForegroundColor White
    Write-Host "  -Help        - Show this help" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run_api.ps1 test" -ForegroundColor Green
    Write-Host "  .\run_api.ps1 install" -ForegroundColor Green
    Write-Host "  .\run_api.ps1 example -SessionId 'your_session_id'" -ForegroundColor Green
    Write-Host ""
}

function Test-PythonInstalled {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
        Write-Host "   Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function Install-Dependencies {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    
    if (-not (Test-PythonInstalled)) {
        return $false
    }
    
    try {
        Write-Host "Installing main dependencies..." -ForegroundColor Yellow
        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt
        
        Write-Host "Installing development dependencies..." -ForegroundColor Yellow
        python -m pip install -r requirements-dev.txt
        
        Write-Host "✅ Dependencies installed successfully!" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Failed to install dependencies: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Run-Tests {
    Write-Host "🧪 Running API tests..." -ForegroundColor Cyan
    
    if (-not (Test-PythonInstalled)) {
        return
    }
    
    # Set session ID if provided
    if ($SessionId) {
        $env:POCKET_OPTION_SSID = $SessionId
        Write-Host "🔑 Session ID set for testing" -ForegroundColor Yellow
    }
    
    try {
        # Run the new API test
        Write-Host "Running new async API test..." -ForegroundColor Yellow
        python test_new_api.py
        
        # Run pytest if available
        $pytestOutput = python -m pytest --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`nRunning pytest suite..." -ForegroundColor Yellow
            python -m pytest tests/ -v
        }
        else {
            Write-Host "ℹ️ pytest not available, install with: pip install pytest pytest-asyncio" -ForegroundColor Blue
        }
    }
    catch {
        Write-Host "❌ Tests failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Run-Example {
    Write-Host "🚀 Running example..." -ForegroundColor Cyan
    
    if (-not (Test-PythonInstalled)) {
        return
    }
    
    if (-not $SessionId) {
        Write-Host "⚠️ No session ID provided. Using mock session for demonstration." -ForegroundColor Yellow
        Write-Host "   For live testing, use: .\run_api.ps1 example -SessionId 'your_session_id'" -ForegroundColor Blue
    }
    else {
        $env:POCKET_OPTION_SSID = $SessionId
        Write-Host "🔑 Using provided session ID" -ForegroundColor Green
    }
    
    try {
        python examples/async_examples.py
    }
    catch {
        Write-Host "❌ Example failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-Migration {
    Write-Host "🔄 Running migration guide..." -ForegroundColor Cyan
    
    if (-not (Test-PythonInstalled)) {
        return
    }
    
    try {
        python migration_guide.py
    }
    catch {
        Write-Host "❌ Migration guide failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-Status {
    Write-Host "📊 PocketOption API Status" -ForegroundColor Cyan
    Write-Host "=" * 30 -ForegroundColor Cyan
    
    # Check Python
    if (Test-PythonInstalled) {
        Write-Host "✅ Python installed" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Python not found" -ForegroundColor Red
    }
    
    # Check if new API files exist
    $apiFiles = @(
        "pocketoptionapi_async\__init__.py",
        "pocketoptionapi_async\client.py",
        "pocketoptionapi_async\models.py",
        "pocketoptionapi_async\websocket_client.py"
    )
    
    $missingFiles = @()
    foreach ($file in $apiFiles) {
        if (Test-Path $file) {
            Write-Host "✅ $file" -ForegroundColor Green
        }
        else {
            Write-Host "❌ $file" -ForegroundColor Red
            $missingFiles += $file
        }
    }
    
    if ($missingFiles.Count -eq 0) {
        Write-Host "`n🎉 All API files present!" -ForegroundColor Green
    }
    else {
        Write-Host "`n⚠️ Missing files detected. Re-run setup." -ForegroundColor Yellow
    }
    
    # Check environment
    if ($env:POCKET_OPTION_SSID) {
        Write-Host "🔑 Session ID configured" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️ No session ID set" -ForegroundColor Yellow
        Write-Host "   Set with: `$env:POCKET_OPTION_SSID='your_session_id'" -ForegroundColor Blue
    }
}

# Main script logic
if ($Help -or $Command -eq "help") {
    Show-Help
    exit 0
}

Write-Host "🚀 PocketOption Async API Helper" -ForegroundColor Cyan
Write-Host "Current Time: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

switch ($Command.ToLower()) {
    "test" {
        Show-Status
        Write-Host ""
        Run-Tests
    }
    "install" {
        Install-Dependencies
    }
    "example" {
        Run-Example
    }
    "migrate" {
        Show-Migration
    }
    "status" {
        Show-Status
    }
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Write-Host "Use '.\run_api.ps1 help' for available commands" -ForegroundColor Yellow
    }
}

Write-Host "`n✨ Script completed!" -ForegroundColor Green
