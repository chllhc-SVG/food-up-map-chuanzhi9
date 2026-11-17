@echo off
setlocal
cd /d "%~dp0"
echo Open http://127.0.0.1:8794/ in your browser. Press Ctrl+C to stop.
where python >nul 2>nul
if errorlevel 1 (
  py -3 server.py
) else (
  python server.py
)
if errorlevel 1 pause
