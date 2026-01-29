@echo off
title CryptoAI - Build Executable
color 0E

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║              🪙 CryptoAI - Build Windows EXE                 ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Activate virtual environment
if exist "venv312\Scripts\activate.bat" (
    call venv312\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Install PyInstaller if needed
echo 🔧 Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller --quiet
)

REM Create icon if it doesn't exist
if not exist "cryptoai.ico" (
    echo 🎨 Creating application icon...
    python create_icon.py
)

REM Clean previous builds
echo 🧹 Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the executable
echo.
echo 🔨 Building CryptoAI.exe...
echo    This may take a few minutes...
echo.

pyinstaller CryptoAI.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ❌ Build failed! Trying alternative method...
    echo.
    
    REM Fallback: simple one-file build
    pyinstaller --onefile --windowed --name CryptoAI --icon cryptoai.ico windows_app.py
)

if exist "dist\CryptoAI.exe" (
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo ✅ BUILD SUCCESSFUL!
    echo.
    echo    Executable: dist\CryptoAI.exe
    echo.
    
    REM Get file size
    for %%A in ("dist\CryptoAI.exe") do (
        set size=%%~zA
        set /a sizeMB=!size! / 1048576
    )
    
    echo    Location: %cd%\dist\CryptoAI.exe
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo.
    
    set /p run="Run CryptoAI.exe now? (y/n): "
    if /i "%run%"=="y" (
        start "" "dist\CryptoAI.exe"
    )
) else (
    echo.
    echo ❌ Build failed. Check the error messages above.
    echo.
)

pause
