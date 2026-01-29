# Coinbase BTC Prediction Bot - CLI Mode
# Starts the prediction bot in command-line interface

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CryptoAI Prediction Bot - CLI Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Python found: " -NoNewline
    python --version
} else {
    Write-Host "ERROR: Python is not installed!" -ForegroundColor Red
    pause
    exit 1
}

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run start_prediction_dashboard.ps1 first to set up dependencies" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""
Write-Host "Bot Mode Selection:" -ForegroundColor Yellow
Write-Host "1. SIMULATION MODE (Recommended - No real trades)" -ForegroundColor Green
Write-Host "2. LIVE MODE (Executes real trades - BE CAREFUL!)" -ForegroundColor Red
Write-Host ""

$mode = Read-Host "Select mode (1 or 2)"

Write-Host ""
Write-Host "Risk Level Selection:" -ForegroundColor Yellow
Write-Host "1. Low Risk (10% position size)" -ForegroundColor Green
Write-Host "2. Medium Risk (15% position size)" -ForegroundColor Yellow
Write-Host "3. High Risk (20% position size)" -ForegroundColor Red
Write-Host ""

$risk = Read-Host "Select risk level (1, 2, or 3)"

# Build command
$cmd = "python prediction_trading_bot.py"

if ($mode -eq "2") {
    $cmd += " --live"
    Write-Host ""
    Write-Host "WARNING: LIVE MODE SELECTED!" -ForegroundColor Red
    Write-Host "This will execute REAL trades with your portfolio!" -ForegroundColor Red
    $confirm = Read-Host "Type 'YES' to confirm"
    if ($confirm -ne "YES") {
        Write-Host "Cancelled." -ForegroundColor Yellow
        pause
        exit 0
    }
}

if ($risk -eq "1") {
    $cmd += " --low-risk"
} elseif ($risk -eq "3") {
    $cmd += " --high-risk"
}

Write-Host ""
Write-Host "Starting Prediction Bot..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the bot
Invoke-Expression $cmd

Write-Host ""
Write-Host "Bot stopped." -ForegroundColor Yellow
pause
