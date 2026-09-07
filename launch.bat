@echo off
REM YouTube Agent Engine Launcher
REM Run this to start the web UI. Pin to taskbar for easy access.

cd /d "%~dp0"

REM Check if .venv exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check for .env file
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please create a .env file with your GEMINI_API_KEY:
    echo.
    echo   GEMINI_API_KEY=your_key_here
    echo.
    echo Or run with --demo mode (no API key needed):
    echo.
)

REM Start the app
echo Starting YouTube Agent Engine...
echo.
python app.py %*

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Error occurred. Press any key to close...
    pause
)
