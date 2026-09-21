@echo off
chcp 65001 >nul
echo =====================================================
echo   Khoi dong Telegram AI Bot ^& WebApp bang Docker
echo =====================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-run.ps1"

pause
