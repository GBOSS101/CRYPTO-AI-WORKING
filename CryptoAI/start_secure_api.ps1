# CryptoAI - Start Secure API Server
# Runs the authenticated API with CORS, Biometric, and 2FA

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔐 CryptoAI Secure Trading API Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Check if data directory exists
if (-not (Test-Path "data")) {
    Write-Host "📁 Creating data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Check if authentication is setup
if (-not (Test-Path "data\users_auth.json")) {
    Write-Host "`n⚠️  Authentication not setup yet!" -ForegroundColor Red
    Write-Host "   Run setup first: .\setup_security.ps1" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Do you want to run setup now? (y/n)"
    
    if ($response -eq 'y') {
        python setup_auth.py
    } else {
        Write-Host "`nExiting. Please run .\setup_security.ps1 first." -ForegroundColor Red
        exit
    }
}

Write-Host "`n✅ Security Features:" -ForegroundColor Green
Write-Host "   - CORS Policy" -ForegroundColor White
Write-Host "   - Biometric Authentication" -ForegroundColor White
Write-Host "   - 2FA (TOTP)" -ForegroundColor White
Write-Host "   - JWT Token Authentication" -ForegroundColor White
Write-Host "   - Rate Limiting" -ForegroundColor White
Write-Host "   - Audit Logging" -ForegroundColor White

Write-Host "`n👥 Authorized Users:" -ForegroundColor Green
Write-Host "   - johndawalka (Admin)" -ForegroundColor White
Write-Host "   - GBOSS101 (Admin)" -ForegroundColor White

Write-Host "`n🚀 Starting API Server..." -ForegroundColor Yellow
Write-Host "   Server: http://localhost:5000" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

# Start the secure API
python secure_api.py
