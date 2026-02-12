#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { printf "\033[1;32m[demo]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[fail]\033[0m %s\n" "$*"; exit 1; }

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ensure_env() {
    if [ -f ".env" ]; then
        log "Using existing .env"
        return
    fi

    if [ -f ".env.example" ]; then
        log "Creating .env from .env.example"
        cp .env.example .env
        return
    fi

    log "Generating .env with demo-safe defaults (no secrets)"
    cat > .env <<'EOF'
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
EOF
}

open_url() {
    local url="$1"
    if command -v open >/dev/null 2>&1; then
        open "$url" >/dev/null 2>&1 || true
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 || true
    else
        warn "Open your browser to: $url"
    fi
}

need_cmd docker
need_cmd docker-compose
need_cmd python

ensure_env

log "Checking Docker availability..."
if ! docker info >/dev/null 2>&1; then
    fail "Docker is not running or not reachable. Start Docker Desktop (WSL2 backend on Windows) and retry."
fi

log "Starting docker-compose (detached, build if needed)..."
docker-compose up -d --build

log "Waiting for Postgres health (carms_postgres)..."
for i in {1..40}; do
    status="$(docker inspect --format='{{.State.Health.Status}}' carms_postgres 2>/dev/null || echo "starting")"
    if [ "$status" = "healthy" ]; then
        log "Postgres is healthy."
        break
    fi
    sleep 3
    if [ "$i" -eq 40 ]; then
        fail "Postgres did not become healthy in time (status: $status)"
    fi
done

log "Applying migrations..."
docker exec carms_dagster alembic upgrade head

log "Materializing all assets..."
docker exec carms_dagster dagster asset materialize --select "*" -m carms.pipelines.definitions --wait

log "Waiting for API and Dagster UIs..."
python scripts/wait_for_http.py http://localhost:8000/health 120
python scripts/wait_for_http.py http://localhost:3000 120

log "Opening key pages (best-effort)..."
open_url "http://localhost:8000/docs"
open_url "http://localhost:8000/map"
open_url "http://localhost:3000"

log "Done. Quick links:"
log "API docs:      http://localhost:8000/docs"
log "Program list:  http://localhost:8000/programs?limit=5&include_total=true"
log "Map:           http://localhost:8000/map"
log "Dagster UI:    http://localhost:3000"
