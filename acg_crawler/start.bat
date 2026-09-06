@echo off
title ACG Crawler

echo ========================================
echo   ACG Resource Crawler - Demo
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install flask -q

echo [2/3] Starting server...
start "ACG Crawler" cmd /k "cd /d %~dp0 && python app.py"

timeout /t 3 /nobreak >nul

echo [3/3] Opening browser...
start "" "http://127.0.0.1:5000"

echo.
echo Done. Close the other cmd window to stop.
echo.
pause
