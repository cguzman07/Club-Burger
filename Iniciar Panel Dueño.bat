@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Club Burger · Panel del dueño
cd /d "%~dp0"

echo.
echo   Preparando el panel del dueño...
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo   No se encontró Python. Instálalo y vuelve a abrir este archivo.
  pause
  exit /b 1
)

if not exist "panel_dueno\.venv\Scripts\python.exe" (
  py -3 -m venv "panel_dueno\.venv"
)

"panel_dueno\.venv\Scripts\python.exe" -m pip install -q -r "panel_dueno\requirements.txt"
if errorlevel 1 (
  echo   No se pudieron instalar las dependencias.
  pause
  exit /b 1
)

netsh advfirewall firewall show rule name="Club Burger Panel Dueño" >nul 2>&1
if errorlevel 1 (
  netsh advfirewall firewall add rule name="Club Burger Panel Dueño" dir=in action=allow protocol=TCP localport=5050 >nul 2>&1
)

echo   Listo. Se abrirá una ventana con el QR y el PIN.
echo   Deja esta ventana abierta mientras atienden.
echo.
"panel_dueno\.venv\Scripts\python.exe" "panel_dueno\server.py"
pause
