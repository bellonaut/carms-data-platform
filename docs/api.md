# API Reference

The FastAPI app is defined in `carms/api/main.py` and serves these endpoint groups.

## Health

- `GET /health` - liveness check returning `{ "status": "ok" }`.

## Programs

- `GET /programs` - list/search programs with filtering, pagination, and optional totals.
- `GET /programs/{program_stream_id}` - full record for one program stream.

## Disciplines

- `GET /disciplines` - list active disciplines from silver-layer data.

## Pipeline

- `POST /pipeline/run` - trigger Dagster job execution via Dagster GraphQL.

## Map

- `GET /map` - interactive map HTML page.
- `GET /map/canada.geojson` - static GeoJSON used by the map.
- `GET /map/data.json` - province-level program counts for map rendering.

## Semantic

- `POST /semantic/query` - semantic retrieval over program descriptions.
  - Returns top hits with similarity scores.
  - Optionally returns a LangChain-generated summary answer when `OPENAI_API_KEY` is available.

## Analytics

- `POST /analytics/simulate` - run a scenario simulation.
- `GET /analytics/simulate/{scenario_id}` - retrieve a saved simulation scenario.
- `GET /analytics/preferences` - score and return preference model outputs for a filtered slice.

## Security and Limits

- `X-API-Key` enforcement is enabled when `API_KEY` is configured.
- Request limiting is controlled by `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SEC`.
