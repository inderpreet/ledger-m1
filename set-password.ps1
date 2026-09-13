$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "backend")
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r requirements.txt
}
& .\.venv\Scripts\python.exe set_password.py @args
