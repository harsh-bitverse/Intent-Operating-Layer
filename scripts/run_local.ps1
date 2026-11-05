# Intent Operating Layer (IOL) - Local Startup Script (PowerShell)
# Starts FastAPI backend (port 8000) and Next.js frontend (port 3000) with graceful shutdown.

param (
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " INTENT OPERATING LAYER (IOL) - LOCAL PRODUCTION LAUNCHER   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Python
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python executable not found on PATH. Please install Python 3.11+."
    exit 1
}
Write-Host "[1/4] Found Python: $PythonExe" -ForegroundColor Green

# 2. Check Node
$NodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $NodeExe) {
    Write-Error "Node.js executable not found on PATH. Please install Node 18+."
    exit 1
}
Write-Host "[2/4] Found Node.js: $NodeExe" -ForegroundColor Green

# 3. Ensure Backend Data Directory Exists
$DataDir = Join-Path $ProjectRoot "backend\data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

# 4. Start Backend Process
Write-Host "[3/4] Launching FastAPI Backend on http://127.0.0.1:$BackendPort..." -ForegroundColor Yellow
$BackendEnv = @{
    PYTHONUNBUFFERED = "1"
    IOL_HOST = "127.0.0.1"
    IOL_PORT = "$BackendPort"
    CORS_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
}

$backendProc = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "backend.iol.api.app:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory $ProjectRoot `
    -PassThru

# 5. Start Frontend Process
Write-Host "[4/4] Launching Next.js Frontend on http://localhost:$FrontendPort..." -ForegroundColor Yellow
$FrontendDir = Join-Path $ProjectRoot "frontend"

$frontendCmd = if ($Dev) { "npm run dev -- -p $FrontendPort" } else { "npm run start -- -p $FrontendPort" }
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", $frontendCmd `
    -WorkingDirectory $FrontendDir `
    -PassThru

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " IOL Services Active!" -ForegroundColor Green
Write-Host " -> Backend API:  http://127.0.0.1:$BackendPort (Swagger docs at /docs)" -ForegroundColor White
Write-Host " -> Frontend UI:  http://localhost:$FrontendPort" -ForegroundColor White
Write-Host " Press Ctrl+C in this terminal to stop all IOL services." -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Green

try {
    while ($true) {
        if ($backendProc.HasExited) {
            Write-Host "Backend process terminated unexpectedly." -ForegroundColor Red
            break
        }
        if ($frontendProc.HasExited) {
            Write-Host "Frontend process terminated unexpectedly." -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`nStopping IOL services gracefully..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "IOL shutdown complete." -ForegroundColor Green
}
