# CryptoAI - Test Authentication System
# Tests biometric and 2FA authentication

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🧪 CryptoAI Authentication Test Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Check if API is running
Write-Host "`n🔍 Checking if API server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -Method Get -ErrorAction Stop
    Write-Host "   ✅ API server is running" -ForegroundColor Green
} catch {
    Write-Host "   ❌ API server is not running!" -ForegroundColor Red
    Write-Host "   Start it first: .\start_secure_api.ps1" -ForegroundColor Yellow
    Write-Host ""
    
    $response = Read-Host "Do you want to start the API server in a new window? (y/n)"
    if ($response -eq 'y') {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\start_secure_api.ps1"
        Write-Host "`n⏳ Waiting for API server to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    } else {
        Write-Host "`nExiting. Please start the API server first." -ForegroundColor Red
        exit
    }
}

Write-Host "`n🚀 Running test suite...`n" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

# Run tests
python test_auth.py

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ Tests Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
