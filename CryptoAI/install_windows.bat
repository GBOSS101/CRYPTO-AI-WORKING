@echo off
title CryptoAI - Windows Installer
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║              🪙 CryptoAI Windows Installer                   ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Some features require administrator privileges
    echo    Right-click and "Run as Administrator" for full install
    echo.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed!
    echo.
    echo Please install Python 3.9+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo ✓ Python found
echo.

REM Create virtual environment if needed
if not exist "venv312" (
    if not exist ".venv" (
        echo 📦 Creating virtual environment...
        python -m venv .venv
        echo ✓ Virtual environment created
    )
)

REM Activate virtual environment
if exist "venv312\Scripts\activate.bat" (
    call venv312\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo.
echo 📥 Installing dependencies...
echo.

REM Install core dependencies
pip install -r requirements.txt --quiet

REM Install Windows-specific dependencies
echo Installing Windows-specific packages...
pip install pystray pillow win10toast pywin32 winshell --quiet

echo.
echo ✓ All dependencies installed
echo.

REM Ask about startup
echo ═══════════════════════════════════════════════════════════════
echo.
set /p startup="Add CryptoAI to Windows startup? (y/n): "
if /i "%startup%"=="y" (
    python windows_app.py --add-startup
)

REM Ask about desktop shortcut
echo.
set /p shortcut="Create desktop shortcut? (y/n): "
if /i "%shortcut%"=="y" (
    python windows_app.py --create-shortcut
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo ✅ Installation complete!
echo.
echo To start CryptoAI:
echo   • Double-click "start_windows_app.bat"
echo   • Or run: python windows_app.py
echo.
echo Features:
echo   • System tray icon with quick actions
echo   • Price change notifications
echo   • REST API for mobile apps
echo   • Auto-start with Windows (if enabled)
echo.

set /p launch="Launch CryptoAI now? (y/n): "
if /i "%launch%"=="y" (
    start "" python windows_app.py
)

echo.
pause
