@echo off
REM =============================================================
REM setup_local.bat — One-command local setup for Windows
REM Azure Healthcare Analytics Platform
REM =============================================================

echo.
echo ======================================================
echo   Azure Healthcare Analytics Platform - Local Setup
echo ======================================================
echo.

REM Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found. Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Java
java -version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Java not found. Please install Java 11+ from https://adoptium.net
    pause
    exit /b 1
)
echo [OK] Java found

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv .venv
echo [OK] Virtual environment created

REM Activate
call .venv\Scripts\activate.bat
echo [OK] Activated

REM Install dependencies
echo.
echo Installing Python dependencies...
pip install --upgrade pip -q
pip install -r requirements-dev.txt -q
echo [OK] Dependencies installed

REM Generate sample data
echo.
echo Generating synthetic healthcare sample data...
cd sample-data
python generate_data.py
cd ..
echo [OK] Sample data ready

REM Run unit tests
echo.
echo Running unit tests...
pytest tests\unit\ tests\data_quality\ -v --tb=short
echo [OK] Tests complete

echo.
echo ======================================================
echo   Setup complete!
echo.
echo   Next steps:
echo   1. Activate environment:  .venv\Scripts\activate
echo   2. Run all tests:         pytest tests\ -v
echo   3. See README.md for Azure deployment instructions
echo ======================================================
echo.
pause
