# Launch CryptoAI CLI
Write-Host "🚀 Starting CryptoAI Trading Assistant (CLI Mode)..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment and run CLI
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\main.py"
