#requires -Version 5.0
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Log([string]$msg) { Write-Host "[demo] $msg" -ForegroundColor Green }
function Warn([string]$msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Fail([string]$msg) { Write-Host "[fail] $msg" -ForegroundColor Red; exit 1 }

function NeedCmd([string]$cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Fail "Missing required command: $cmd"
    }
}

NeedCmd docker
NeedCmd docker-compose
NeedCmd python

if (-not (Test-Path ".env")) {
    Log "Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
}

Log "Starting docker-compose (detached, build if needed)..."
docker-compose up -d --build | Out-Null

Log "Waiting for Postgres health (carms_postgres)..."
for ($i = 0; $i -lt 40; $i++) {
    $status = $(docker inspect -f '{{.State.Health.Status}}' carms_postgres 2>$null) -join ""
    if ($status -eq "healthy") {
        Log "Postgres is healthy."
        break
    }
    Start-Sleep -Seconds 3
    if ($i -eq 39) { Fail "Postgres did not become healthy in time (status: $status)" }
}

Log "Applying migrations..."
docker exec carms_dagster alembic upgrade head | Out-Null

Log "Materializing all assets..."
docker exec carms_dagster dagster asset materialize --select "*" -m carms.pipelines.definitions --wait | Out-Null

Log "Waiting for API and Dagster UIs..."
python scripts/wait_for_http.py http://localhost:8000/health 120 | Out-Null
python scripts/wait_for_http.py http://localhost:3000 120 | Out-Null

Log "Opening key pages (best-effort)..."
Start-Process "http://localhost:8000/docs" | Out-Null
Start-Process "http://localhost:8000/map" | Out-Null
Start-Process "http://localhost:3000" | Out-Null

Log "Done. Quick links:"
Write-Host "API docs:      http://localhost:8000/docs"
Write-Host "Program list:  http://localhost:8000/programs?limit=5&include_total=true"
Write-Host "Map:           http://localhost:8000/map"
Write-Host "Dagster UI:    http://localhost:3000"
