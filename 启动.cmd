@echo off
setlocal
cd /d "%~dp0"
echo Opening Food Up Map at http://127.0.0.1:8794/ ... Press Ctrl+C to stop a new server.
where python >nul 2>nul
if errorlevel 1 (
  py -3 server.py --open
) else (
  python server.py --open
)
if errorlevel 1 pause
