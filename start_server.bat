@echo off
echo ========================================
echo PDF Requirements Extractor - Web Interface
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found
    echo Creating .env file...
    echo DEEPSEEK_API_KEY=your-api-key-here > .env
    echo.
    echo Please edit .env file and add your DeepSeek API key
    echo Then run this script again
    pause
    exit /b 1
)

echo [OK] .env file found
echo.

REM Check if dependencies are installed
echo [INFO] Checking dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FastAPI not found
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [OK] Dependencies installed
echo.

REM Create necessary directories
if not exist data\uploads mkdir data\uploads
if not exist data\output mkdir data\output
if not exist logs mkdir logs

echo [OK] Directories created
echo.

REM Start API server
echo ========================================
echo Starting API Server...
echo ========================================
echo.
echo API will be available at: http://localhost:8000
echo Frontend: Open frontend/index.html in your browser
echo.
echo Press CTRL+C to stop the server
echo.

python api_server.py
