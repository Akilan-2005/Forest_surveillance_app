@echo off
REM ===================================================
REM Wildlife Surveillance - Flask Backend
REM ===================================================

echo.
echo ========================================================
echo  Flask Backend Server - Port 5000
echo ========================================================
echo.

cd /d "%~dp0"

REM Check if virtual environment is activated
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup first: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✓ Virtual environment activated
echo.
echo Starting Flask server on http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Start the Flask app
python app.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Flask server
    echo Troubleshooting:
    echo 1. Check if port 5000 is already in use
    echo 2. Run: pip install -r requirements.txt
    echo 3. Check MongoDB is running
    pause
)
