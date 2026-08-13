$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $null

$Candidates = @(
    (Get-Command python -ErrorAction SilentlyContinue).Source,
    (Get-Command py -ErrorAction SilentlyContinue).Source,
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
) | Where-Object { $_ -and (Test-Path $_) }

if ($Candidates.Count -gt 0) {
    $Python = $Candidates[0]
}

if (-not $Python) {
    throw "Python was not found. Please install Python 3.11+ first, then run this script again."
}

Push-Location $ProjectRoot
try {
    if (-not (Test-Path '.venv')) { & $Python -m venv .venv }
    & '.\.venv\Scripts\python.exe' -m pip install -r '.\backend\requirements.txt'
    Push-Location '.\frontend'
    try { npm.cmd install } finally { Pop-Location }
    Write-Host 'Setup completed.' -ForegroundColor Green
} finally { Pop-Location }
