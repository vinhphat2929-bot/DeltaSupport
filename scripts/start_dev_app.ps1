$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

$env:DELTA_APP_ENV = "development"
$env:DELTA_API_BASE_URL = "http://127.0.0.1:8000"

Write-Host "Starting DELTA ONE desktop app in DEV mode"
Write-Host "API: $($env:DELTA_API_BASE_URL)"
Write-Host ""
Write-Host "Make sure scripts/start_dev_api.ps1 is already running in another window."
Write-Host ""

Push-Location $ProjectRoot
try {
    python main.py
}
finally {
    Pop-Location
}
