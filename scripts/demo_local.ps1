#requires -Version 5.0
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Log([string]$msg) { Write-Host "[demo-local] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Fail([string]$msg) { Write-Host "[fail] $msg" -ForegroundColor Red; exit 1 }

function NeedCmd([string]$cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Fail "Missing required command: $cmd"
    }
}

NeedCmd python

$venv = ".venv-demo"
$venvPython = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Log "Creating virtualenv at $venv"
    python -m venv $venv
}

Log "Installing lightweight demo dependencies..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r requirements-demo.txt

if (-not $env:DB_URL) { $env:DB_URL = "sqlite:///./demo.db" }
if (-not $env:DAGSTER_HOME) { $env:DAGSTER_HOME = ".dagster_local" }
$env:ENV = "local"

Log "Using DB_URL=$env:DB_URL (SQLite) and DAGSTER_HOME=$env:DAGSTER_HOME"
Remove-Item "demo.db" -ErrorAction SilentlyContinue

Log "Applying migrations..."
& $venvPython -m alembic upgrade head

Log "Materializing all assets (headless Dagster)..."
& $venvPython -m dagster asset materialize --select "*" -m carms.pipelines.definitions --wait

Log "Starting Dagster UI and API locally..."
$processIds = @()
$dagsterProc = Start-Process -FilePath $venvPython -ArgumentList "-m","dagster","dev","-m","carms.pipelines.definitions","-h","0.0.0.0","-p","3000" -PassThru -WindowStyle Minimized
$processIds += $dagsterProc.Id

$uvicornProc = Start-Process -FilePath $venvPython -ArgumentList "-m","uvicorn","carms.api.main:app","--host","0.0.0.0","--port","8000","--reload" -PassThru -WindowStyle Minimized
$processIds += $uvicornProc.Id

Log "Waiting for API and Dagster UIs..."
& $venvPython scripts/wait_for_http.py http://localhost:8000/health 120 | Out-Null
& $venvPython scripts/wait_for_http.py http://localhost:3000 120 | Out-Null

Set-Content -Path ".demo-local.pids" -Value ($processIds -join "`n")

Log "Opening key pages (best-effort)..."
Start-Process "http://localhost:8000/docs" | Out-Null
Start-Process "http://localhost:8000/map" | Out-Null
Start-Process "http://localhost:3000" | Out-Null

Log "Done. Quick links:"
Write-Host "API docs:      http://localhost:8000/docs"
Write-Host "Program list:  http://localhost:8000/programs?limit=5&include_total=true"
Write-Host "Map:           http://localhost:8000/map"
Write-Host "Dagster UI:    http://localhost:3000"
Log "To stop local processes: Get-Content .demo-local.pids | ForEach-Object { Stop-Process -Id $_ }"
