@echo off
REM Coinbase BTC Prediction Dashboard - Windows Batch Launcher
REM Double-click this file to start the dashboard

echo ========================================
echo  CryptoAI Prediction Market Dashboard
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo Python found: 
python --version

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting Prediction Market Dashboard...
echo Dashboard will open at: http://localhost:8050
echo Press Ctrl+C to stop
echo.

REM Start the dashboard
python dashboard_predictions.py

echo.
echo Dashboard stopped.
pause
