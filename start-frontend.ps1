$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "frontend")

if (-not (Test-Path ".\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

Write-Host "Frontend: http://localhost:3000"
npm run dev
