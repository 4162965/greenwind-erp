param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDirectory = Join-Path $ProjectRoot "logs"
$BackendLog = Join-Path $LogDirectory "backend.log"
$FrontendLog = Join-Path $LogDirectory "frontend.log"
$AppUrl = "http://127.0.0.1:5173/projects"
$BackendPort = 8010
$FrontendPort = 5173

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Test-LocalPort {
    param([int]$Port)

    $Client = [System.Net.Sockets.TcpClient]::new()
    try {
        $Task = $Client.ConnectAsync("127.0.0.1", $Port)
        return $Task.Wait(300) -and $Client.Connected
    }
    catch {
        return $false
    }
    finally {
        $Client.Dispose()
    }
}

if (-not (Test-LocalPort -Port $BackendPort)) {
    $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $Python)) {
        throw "Python virtual environment was not found. Run setup first."
    }

    Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort" `
        -WorkingDirectory (Join-Path $ProjectRoot "backend") `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError (Join-Path $LogDirectory "backend-error.log")
}

if (-not (Test-LocalPort -Port $FrontendPort)) {
    $Npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    Start-Process -FilePath $Npm `
        -ArgumentList "run", "dev", "--", "--host", "127.0.0.1" `
        -WorkingDirectory (Join-Path $ProjectRoot "frontend") `
        -WindowStyle Hidden `
        -RedirectStandardOutput $FrontendLog `
        -RedirectStandardError (Join-Path $LogDirectory "frontend-error.log")
}

$Deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $Deadline) {
    $BackendReady = $false
    try {
        $BackendReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2).StatusCode -eq 200
    }
    catch {
        $BackendReady = $false
    }

    if ($BackendReady -and (Test-LocalPort -Port $FrontendPort)) {
        if (-not $NoBrowser) {
            Start-Process $AppUrl
        }
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

throw "Greenwind ERP startup timed out. Check the logs directory."
