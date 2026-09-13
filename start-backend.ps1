$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "backend")

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating backend virtualenv..."
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r requirements.txt
}

Write-Host "Backend: http://127.0.0.1:8000"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
