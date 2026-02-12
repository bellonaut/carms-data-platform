#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { printf "\033[1;32m[demo-local]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[fail]\033[0m %s\n" "$*"; exit 1; }

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
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

need_cmd python

VENV=".venv-demo"
if [ ! -d "$VENV" ]; then
    log "Creating virtualenv at $VENV"
    python -m venv "$VENV"
fi

# shellcheck disable=SC1090
source "$VENV/bin/activate"

log "Installing lightweight demo dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements-demo.txt

export DB_URL="${DB_URL:-sqlite:///./demo.db}"
export DAGSTER_HOME="${DAGSTER_HOME:-.dagster_local}"
export ENV="${ENV:-local}"

log "Using DB_URL=$DB_URL (SQLite) and DAGSTER_HOME=$DAGSTER_HOME"
rm -f demo.db

log "Applying migrations..."
alembic upgrade head

log "Materializing all assets (headless Dagster)..."
dagster asset materialize --select "*" -m carms.pipelines.definitions --wait

log "Starting Dagster UI and API locally..."
> .demo-local.pids
nohup env DB_URL="$DB_URL" DAGSTER_HOME="$DAGSTER_HOME" ENV="$ENV" \
    dagster dev -m carms.pipelines.definitions -h 0.0.0.0 -p 3000 \
    > .demo-local-dagster.log 2>&1 &
echo $! >> .demo-local.pids

nohup env DB_URL="$DB_URL" DAGSTER_HOME="$DAGSTER_HOME" ENV="$ENV" \
    uvicorn carms.api.main:app --host 0.0.0.0 --port 8000 --reload \
    > .demo-local-api.log 2>&1 &
echo $! >> .demo-local.pids

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
log "To stop local processes: xargs kill < .demo-local.pids (or manually terminate Dagster/uvicorn)."
