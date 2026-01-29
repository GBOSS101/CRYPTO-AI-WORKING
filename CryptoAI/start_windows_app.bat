@echo off
title CryptoAI - Windows Application
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║              🪙 CryptoAI Windows Application                 ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist "venv312\Scripts\activate.bat" (
    echo 📦 Activating virtual environment...
    call venv312\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo 📦 Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Install Windows-specific dependencies if needed
echo.
echo 🔧 Checking Windows dependencies...
pip show pystray >nul 2>&1 || pip install pystray pillow win10toast --quiet
pip show pywin32 >nul 2>&1 || pip install pywin32 winshell --quiet

REM Start the application
echo.
echo 🚀 Starting CryptoAI...
echo.
python windows_app.py %*

pause
