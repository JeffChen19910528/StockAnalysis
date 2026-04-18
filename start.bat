@echo off
echo ========================================
echo  Taiwan Stock Analysis - Starting...
echo ========================================

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.9+
    echo         Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create venv if missing
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Install / update packages using venv python directly
echo Installing packages...
venv\Scripts\python.exe -m pip install -r requirements.txt -q
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

:: Create .env from example if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo.
        echo [INFO] .env file created from template.
        echo        To enable AI analysis, open .env and set your ANTHROPIC_API_KEY.
        echo        The system works without a key using rule-based analysis.
        echo.
    )
)

:: Kill any existing app.py process on port 5000
echo Checking for existing server process...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING" 2^>nul') do (
    echo   Killing old process PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Server starting at: http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.

venv\Scripts\python.exe app.py
pause
