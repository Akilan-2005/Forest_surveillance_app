@echo off
REM ===================================================
REM Wildlife Surveillance - Frontend Start Script
REM ===================================================

echo.
echo ========================================================
echo  React Frontend - Port 3000
echo ========================================================
echo.

cd /d "%~dp0\..\frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo ✓ Dependencies ready
echo.
echo Starting React server on http://localhost:3000
echo Press Ctrl+C to stop the server
echo.

REM Start the React app
call npm start

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start React server
    echo Troubleshooting:
    echo 1. Check if port 3000 is already in use
    echo 2. Run: npm install
    echo 3. Ensure Node.js is installed
    pause
)
