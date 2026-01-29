# Coinbase BTC Prediction Bot - PowerShell Startup Script
# Starts the prediction market dashboard

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CryptoAI Prediction Market Dashboard" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Python found: " -NoNewline
    python --version
} else {
    Write-Host "ERROR: Python is not installed!" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://python.org" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    & "venv\Scripts\Activate.ps1"
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "Starting Prediction Market Dashboard..." -ForegroundColor Green
Write-Host "Dashboard will open at: http://localhost:8050" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the dashboard
python dashboard_predictions.py

Write-Host ""
Write-Host "Dashboard stopped." -ForegroundColor Yellow
pause
