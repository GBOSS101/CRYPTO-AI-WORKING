# CryptoAI - Setup Authentication System
# Configures 2FA and Biometric authentication

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔐 CryptoAI Authentication Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

Write-Host "`n✅ This setup will configure:" -ForegroundColor Green
Write-Host "   1. 2FA (Two-Factor Authentication)" -ForegroundColor White
Write-Host "   2. Biometric Authentication" -ForegroundColor White
Write-Host "   3. Security database" -ForegroundColor White
Write-Host "   4. QR codes for authenticator apps" -ForegroundColor White

Write-Host "`n👥 For authorized users:" -ForegroundColor Green
Write-Host "   - johndawalka" -ForegroundColor White
Write-Host "   - GBOSS101" -ForegroundColor White

Write-Host "`n============================================================`n" -ForegroundColor Cyan

# Run setup
python setup_auth.py

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n📱 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Open QR codes in data/qr_codes/" -ForegroundColor White
Write-Host "   2. Scan with Google Authenticator or Authy" -ForegroundColor White
Write-Host "   3. Test authentication: .\test_security.ps1" -ForegroundColor White
Write-Host "   4. Start API server: .\start_secure_api.ps1" -ForegroundColor White

Write-Host ""
