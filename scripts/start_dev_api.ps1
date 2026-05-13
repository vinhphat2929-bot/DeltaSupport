$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir = Join-Path $ProjectRoot "backend_server"

if (-not $env:DELTA_DB_SERVER) {
    $env:DELTA_DB_SERVER = "localhost"
}

if (-not $env:DELTA_DB_NAME) {
    $env:DELTA_DB_NAME = "DeltaSupport_DEV"
}

if (-not $env:DELTA_DB_USER) {
    $env:DELTA_DB_USER = "delta_user"
}

if (-not $env:DELTA_DB_PASSWORD) {
    $env:DELTA_DB_PASSWORD = "Delta@123456"
}

$env:DELTA_APP_ENV = "development"
$env:DELTA_DB_TRUSTED_CONNECTION = "yes"

Write-Host "Starting DELTA ONE API in DEV mode"
Write-Host "API: http://127.0.0.1:8000"
Write-Host "DB : $($env:DELTA_DB_SERVER) / $($env:DELTA_DB_NAME)"
Write-Host "Auth: Windows Trusted Connection"
Write-Host ""
Write-Host "Keep this window open while testing the app."
Write-Host ""

Push-Location $BackendDir
try {
    python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
}
finally {
    Pop-Location
}
