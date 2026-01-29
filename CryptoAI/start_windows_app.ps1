# CryptoAI Windows Application Launcher
# PowerShell script with enhanced Windows integration

param(
    [switch]$AddStartup,
    [switch]$RemoveStartup,
    [switch]$CreateShortcut,
    [switch]$Console,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Banner
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║              🪙 CryptoAI Windows Application                 ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
$venvPaths = @("venv312\Scripts\Activate.ps1", ".venv\Scripts\Activate.ps1", "venv\Scripts\Activate.ps1")
foreach ($venv in $venvPaths) {
    if (Test-Path $venv) {
        Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
        & $venv
        break
    }
}

# Install Windows dependencies
if ($Install) {
    Write-Host ""
    Write-Host "🔧 Installing Windows dependencies..." -ForegroundColor Yellow
    pip install pystray pillow win10toast pywin32 winshell --quiet
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
    exit 0
}

# Check dependencies
$deps = @("pystray", "win10toast")
$missing = @()
foreach ($dep in $deps) {
    $result = pip show $dep 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missing += $dep
    }
}

if ($missing.Count -gt 0) {
    Write-Host "⚠️ Missing dependencies: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "Installing..." -ForegroundColor Yellow
    pip install pystray pillow win10toast --quiet
}

# Handle command line options
$pythonArgs = @()

if ($AddStartup) {
    $pythonArgs += "--add-startup"
}
if ($RemoveStartup) {
    $pythonArgs += "--remove-startup"
}
if ($CreateShortcut) {
    $pythonArgs += "--create-shortcut"
}
if ($Console) {
    $pythonArgs += "--console"
}

# Run the application
Write-Host ""
Write-Host "🚀 Starting CryptoAI..." -ForegroundColor Green
Write-Host ""

if ($pythonArgs.Count -gt 0) {
    python windows_app.py @pythonArgs
} else {
    python windows_app.py
}
