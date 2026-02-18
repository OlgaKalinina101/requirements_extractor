#!/bin/bash

echo "========================================"
echo "PDF Requirements Extractor - Web Interface"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found"
    echo "Creating .env file..."
    echo "DEEPSEEK_API_KEY=your-api-key-here" > .env
    echo ""
    echo "Please edit .env file and add your DeepSeek API key"
    echo "Then run this script again"
    exit 1
fi

echo "[OK] .env file found"
echo ""

# Check if dependencies are installed
echo "[INFO] Checking dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "[WARNING] FastAPI not found"
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
fi

echo "[OK] Dependencies installed"
echo ""

# Create necessary directories
mkdir -p data/uploads
mkdir -p data/output
mkdir -p logs

echo "[OK] Directories created"
echo ""

# Start API server
echo "========================================"
echo "Starting API Server..."
echo "========================================"
echo ""
echo "API will be available at: http://localhost:8000"
echo "Frontend: Open frontend/index.html in your browser"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python3 api_server.py
