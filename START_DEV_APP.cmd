@echo off
setlocal

set "DELTA_APP_ENV=development"
set "DELTA_API_BASE_URL=http://127.0.0.1:8000"

echo Starting DELTA ONE desktop app in DEV mode
echo API: %DELTA_API_BASE_URL%
echo.
echo Make sure START_DEV_API.cmd is already running in another window.
echo.

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo DEV app stopped with an error.
    pause
)
