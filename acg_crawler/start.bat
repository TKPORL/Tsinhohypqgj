@echo off
chcp 65001 >nul
title ACG黄油资源聚合爬取工具

echo ========================================
echo   ACG黄油资源聚合爬取工具
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 安装依赖...
pip install flask requests beautifulsoup4 lxml pyyaml -q

echo [2/3] 启动服务...
start /b python app.py

timeout /t 2 /nobreak >nul

echo [3/3] 打开浏览器...
start http://127.0.0.1:5000

echo.
echo 服务已启动，浏览器已打开。
echo 按 Ctrl+C 停止服务。
echo.
pause
