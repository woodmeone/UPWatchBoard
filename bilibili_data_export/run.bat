@echo off
chcp 65001 >nul 2>&1
title B站数据中心自动导出工具

echo ============================================================
echo   B站数据中心自动导出工具
echo   首次运行会自动安装依赖，请耐心等待
echo ============================================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python，请先安装 Python 3.8+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查并安装 playwright
python -c "import playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 正在安装 playwright...
    pip install playwright
    echo.
    echo 📦 正在安装 Chromium 浏览器（可能需要几分钟）...
    playwright install chromium
    echo.
    echo ✅ 安装完成！
    echo.
)

:: 运行脚本
echo 🚀 启动导出脚本...
echo.
python "%~dp0playwright_version.py"

echo.
pause
