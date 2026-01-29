# Launch CryptoAI Web Dashboard
Write-Host "🚀 Starting CryptoAI Trading Assistant..." -ForegroundColor Cyan
Write-Host "📊 Web Dashboard will open at http://127.0.0.1:8050" -ForegroundColor Yellow
Write-Host ""
Write-Host "Features:" -ForegroundColor Green
Write-Host "  ✅ Live trade suggestions with AI analysis" -ForegroundColor White
Write-Host "  ✅ Real-time portfolio tracking" -ForegroundColor White
Write-Host "  ✅ Market sentiment analysis" -ForegroundColor White
Write-Host "  ✅ Interactive charts and data" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Press Ctrl+C to stop the server" -ForegroundColor Red
Write-Host ""

# Activate virtual environment and run dashboard
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\dashboard.py"
