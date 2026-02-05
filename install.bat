@echo off
REM Windows AI Agent Installation Script

echo =========================================
echo Windows AI Agent - Installation Script
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo ✓ Virtual environment created

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    echo Please check the error messages above
    pause
    exit /b 1
)

echo ✓ Requirements installed successfully

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo Creating .env file from template...
    copy .env.example .env
    echo ✓ .env file created
    echo.
    echo IMPORTANT: Please edit the .env file and add your Google API key!
    echo You can get a free API key from https://makersuite.google.com/app/apikey
) else (
    echo ✓ .env file already exists
)

REM Create logs directory
if not exist logs mkdir logs
echo ✓ Logs directory ready

echo.
echo =========================================
echo Installation completed successfully! 🚀
echo =========================================
echo.
echo Next steps:
echo 1. Edit .env file and add your Google API key
echo 2. Run: python main.py
echo.
echo For help, run: python main.py --help
echo.
pause