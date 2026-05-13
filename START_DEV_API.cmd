@echo off
setlocal

set "DELTA_APP_ENV=development"
set "DELTA_DB_SERVER=localhost"
set "DELTA_DB_NAME=DeltaSupport_DEV"
set "DELTA_DB_USER=delta_user"
set "DELTA_DB_PASSWORD=Delta@123456"
set "DELTA_DB_TRUSTED_CONNECTION=yes"

echo Starting DELTA ONE API in DEV mode
echo API: http://127.0.0.1:8000
echo DB : %DELTA_DB_SERVER% / %DELTA_DB_NAME%
echo Auth: Windows Trusted Connection
echo.
echo Keep this window open while testing the app.
echo.

cd /d "%~dp0backend_server"
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload

if errorlevel 1 (
    echo.
    echo DEV API stopped with an error.
    pause
)
