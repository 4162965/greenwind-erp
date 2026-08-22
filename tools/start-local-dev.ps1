$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$codexNodeBin = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"

function Resolve-CommandPath($name, $fallback) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  if ($fallback -and (Test-Path -LiteralPath $fallback)) { return $fallback }
  throw "Missing required command: $name"
}

function Resolve-UsableCommand($name, $fallback, $versionArg = "--version") {
  $candidates = @()
  if ($fallback) { $candidates += $fallback }
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { $candidates += $cmd.Source }

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (!(Test-Path -LiteralPath $candidate)) { continue }
    try {
      & $candidate $versionArg *> $null
      if ($LASTEXITCODE -eq 0) { return $candidate }
    } catch {
      continue
    }
  }

  throw "Missing usable command: $name"
}

$python = Resolve-UsableCommand "python" $codexPython "--version"
$npm = Resolve-UsableCommand "npm.cmd" "C:\Program Files\nodejs\npm.cmd" "--version"

if ((Test-Path -LiteralPath (Join-Path $backend ".venv")) -and !(Test-Path -LiteralPath $venvPython)) {
  Write-Host "Removing incomplete backend virtual environment..."
  Remove-Item -LiteralPath (Join-Path $backend ".venv") -Recurse -Force
}

if (!(Test-Path -LiteralPath $venvPython)) {
  Write-Host "Creating backend virtual environment..."
  & $python -m venv (Join-Path $backend ".venv")
}

Write-Host "Installing backend dependencies..."
& $venvPython -m pip install -r (Join-Path $backend "requirements.txt")

if (!(Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
  Write-Host "Installing frontend dependencies..."
  Push-Location $frontend
  & $npm install
  Pop-Location
}

$backendRunner = Join-Path $PSScriptRoot "run-backend-dev.cmd"
$frontendRunner = Join-Path $PSScriptRoot "run-frontend-dev.cmd"

Start-Process -FilePath $backendRunner -WorkingDirectory $backend -WindowStyle Normal
Start-Sleep -Seconds 2
Start-Process -FilePath $frontendRunner -WorkingDirectory $frontend -WindowStyle Normal

function Wait-HttpReady($url, $name, $seconds = 45) {
  $deadline = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        Write-Host "$name is ready."
        return
      }
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  Write-Host "$name is still starting. Open the service window to check logs."
}

Wait-HttpReady "http://localhost:8010/api/health" "Backend"
Wait-HttpReady "http://localhost:5173" "Frontend"
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Greenwind ERP local dev is starting:"
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://localhost:8010/api/health"
Write-Host "Keep the two PowerShell windows open while testing."
