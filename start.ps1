$ErrorActionPreference = "Stop"

Write-Host "Starting Ledger..."
Write-Host "  API       http://127.0.0.1:8000"
Write-Host "  Web app   http://localhost:3000"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-backend.ps1")
)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PSScriptRoot "start-frontend.ps1")
)
