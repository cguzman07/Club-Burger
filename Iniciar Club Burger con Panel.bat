@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "%~dp0Club Burger.exe"
timeout /t 2 /nobreak >nul
call "%~dp0Iniciar Panel Dueño.bat"
