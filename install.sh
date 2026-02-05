#!/bin/bash

# Windows AI Agent Installation Script for WSL/Linux

echo "========================================="
echo "Windows AI Agent - Installation Script"
echo "========================================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python found"
python3 --version

# Create virtual environment
echo
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created"

# Activate virtual environment
echo
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo
echo "Installing requirements..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to install requirements"
    echo "Please check the error messages above"
    exit 1
fi

echo "✅ Requirements installed successfully"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo
    echo "⚠️  IMPORTANT: Please edit the .env file and add your Google API key!"
    echo "You can get a free API key from https://makersuite.google.com/app/apikey"
else
    echo "✅ .env file already exists"
fi

# Create logs directory
mkdir -p logs
echo "✅ Logs directory ready"

echo
echo "========================================="
echo "Installation completed successfully! 🚀"
echo "========================================="
echo
echo "Next steps:"
echo "1. Edit .env file and add your Google API key"
echo "2. Run: python main.py"
echo
echo "For help, run: python main.py --help"
echo