@echo off
REM ===================================================
REM Wildlife Surveillance - FastAPI Detection Server
REM ===================================================

echo.
echo ========================================================
echo  FastAPI YOLO Detection Service - Port 8000
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
echo Starting FastAPI server on http://0.0.0.0:8000
echo Press Ctrl+C to stop the server
echo.

REM Start the detection service
python -m uvicorn api_yolo:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start FastAPI server
    echo Troubleshooting:
    echo 1. Check if port 8000 is already in use
    echo 2. Run: pip install -r requirements.txt
    echo 3. Ensure you have Python 3.8+
    pause
)
