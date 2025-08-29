@echo off
echo ========================================
echo Django Project Setup and Server Launcher
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check for virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install requirements
if exist requirements.txt (
    echo Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install some requirements
        echo Continuing with server startup...
    )
) else (
    echo Warning: requirements.txt not found
    echo Installing Django and pymongo only...
    pip install Django pymongo
)

REM Check if manage.py exists
if not exist manage.py (
    echo Error: manage.py not found in current directory
    echo Please run this script from your Django project root
    pause
    exit /b 1
)

REM Run the Django server
echo Starting Django development server...
echo Press Ctrl+C to stop the server
echo.
python manage.py runserver

REM Keep the window open after the server stops
echo.
echo Server stopped. Press any key to close this window...
pause >nul