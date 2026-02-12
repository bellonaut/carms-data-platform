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

function EnsureEnv() {
    if (Test-Path ".env") {
        Log "Using existing .env"
        return
    }
    if (Test-Path ".env.example") {
        Log "Creating .env from .env.example"
        Copy-Item ".env.example" ".env"
        return
    }
    Log "Generating .env with demo-safe defaults (no secrets)"
    @"
POSTGRES_DB=carms
POSTGRES_USER=carms_app
POSTGRES_PASSWORD=carms_secret
DB_URL=postgresql+psycopg2://carms_app:carms_secret@postgres:5432/carms
ENV=local
DAGSTER_HOME=/app/.dagster
API_PORT=8000
DAGSTER_PORT=3000
API_KEY=
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SEC=60
"@ | Out-File -FilePath ".env" -Encoding ascii -Force
}

NeedCmd docker
NeedCmd docker-compose
NeedCmd python

EnsureEnv

Log "Checking Docker availability..."
try {
    docker info | Out-Null
} catch {
    Fail "Docker is not running or not reachable. Start Docker Desktop (WSL2 backend) and retry."
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
