param(
    [switch]$ListOnly
)

$ErrorActionPreference = "Continue"
$ProjectRoot = (Resolve-Path $PSScriptRoot).Path.TrimEnd("\")
$Marker = $ProjectRoot.ToLowerInvariant()
$Ports = @(8000, 3000)

function Test-ProjectProcess {
    param($Proc)
    $name = [string]$Proc.Name
    if ($name -match '(?i)^(cursor|code|devenv|windowsterminal|explorer)$') {
        return $false
    }
    if ($Proc.ProcessId -eq $PID) {
        return $false
    }

    $haystack = @(
        $Proc.CommandLine,
        $Proc.ExecutablePath
    ) -join " "
    if ([string]::IsNullOrWhiteSpace($haystack)) {
        return $false
    }
    $haystack = $haystack.ToLowerInvariant().Replace("/", "\")
    if (-not $haystack.Contains($Marker)) {
        return $false
    }

    return (
        $haystack -match 'uvicorn' -or
        $haystack -match 'start-backend\.ps1' -or
        $haystack -match 'start-frontend\.ps1' -or
        $haystack -match '\\backend\\.venv\\' -or
        $haystack -match '\\frontend\\' -or
        ($haystack -match 'start\.ps1' -and $haystack -notmatch 'stop\.ps1')
    )
}

function Get-ListenPids {
    param([int[]]$ListenPorts)
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($port in $ListenPorts) {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { [void]$ids.Add([int]$_.OwningProcess) }
    }
    return $ids
}

Write-Host "Looking for Ledger processes under"
Write-Host "  $ProjectRoot"
Write-Host ""

$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
$matches = @($procs | Where-Object { Test-ProjectProcess $_ })

$listenPids = Get-ListenPids -ListenPorts $Ports
foreach ($proc in $procs) {
    if (-not $listenPids.Contains([int]$proc.ProcessId)) {
        continue
    }
    if (Test-ProjectProcess $proc) {
        continue
    }
    $haystack = @($proc.CommandLine, $proc.ExecutablePath) -join " "
    if ($haystack.ToLowerInvariant().Replace("/", "\").Contains($Marker)) {
        $matches += $proc
    }
}

$matches = @($matches | Sort-Object ProcessId -Unique)
if ($matches.Count -eq 0) {
    Write-Host "No project processes found."
    exit 0
}

Write-Host "Found $($matches.Count):"
foreach ($proc in $matches) {
    $cmd = $proc.CommandLine
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        $cmd = $proc.ExecutablePath
    }
    if ($cmd.Length -gt 140) {
        $cmd = $cmd.Substring(0, 137) + "..."
    }
    Write-Host ("  PID {0,-6} {1,-16} {2}" -f $proc.ProcessId, $proc.Name, $cmd)
}

if ($ListOnly) {
    Write-Host ""
    Write-Host "List only. Nothing stopped."
    exit 0
}

Write-Host ""
Write-Host "Stopping..."
$failed = $false
foreach ($proc in $matches) {
    $id = [int]$proc.ProcessId
    if (-not (Get-Process -Id $id -ErrorAction SilentlyContinue)) {
        continue
    }
    & taskkill.exe /PID $id /T /F 2>$null | Out-Null
    if (Get-Process -Id $id -ErrorAction SilentlyContinue) {
        Write-Host "  still running: $id"
        $failed = $true
    } else {
        Write-Host "  stopped $id"
    }
}

if ($failed) {
    Write-Host "Some processes did not stop. Re-run the script."
    exit 1
}

Write-Host "Done."
