@echo off
chcp 65001 >nul
title TikTok Auto Cleaner Pro - CLI Edition
cd /d "%~dp0"

echo ======================================================================
echo                 TIKTOK AUTO CLEANER PRO (CLI EDITION)
echo ======================================================================
echo.
echo Verificando dependencias de Python...
python -c "import selenium, webdriver_manager" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando librerias necesarias...
    pip install -r requirements.txt
)

echo.
echo Iniciando programa...
python cleaner.py
echo.
pause
