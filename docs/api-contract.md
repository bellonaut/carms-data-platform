# API Contract

## Security
- Optional API key header: `X-API-Key`. Enabled when `API_KEY` is set (see `.env.example`). All routes enforce it when present.
- Rate limit: `RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SEC` (default 120 requests / 60s) applied per client IP.

## Base URL
- Local dev: `http://localhost:8000`

## Endpoints

### `GET /health`
- Purpose: liveness check.
- Responses: `200 {"status": "ok"}` when healthy.

### `GET /programs`
- Query params:
  - `discipline` (str, optional, substring match)
  - `province` (str, optional, codes AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT|UNKNOWN)
  - `school` (str, optional, substring match)
  - `limit` (int, default 100, min 1, max 500)
  - `offset` (int, default 0, min 0)
  - `include_total` (bool, default false)
  - `preview_chars` (int, default 900, max 5000)
- Responses:
  - `200` ProgramListResponse
  - `422` on validation errors.

### `GET /programs/{program_stream_id}`
- Path params: `program_stream_id` (int, required)
- Responses:
  - `200` ProgramDetail
  - `404` if not found

### `GET /disciplines`
- Purpose: active discipline lookup.
- Responses: list of disciplines.

### `POST /pipeline/run`
- Purpose: trigger Dagster asset job via GraphQL.
- Responses:
  - `200` with `{status, detail, run_id?}` on success.
  - `502` if Dagster unreachable.
  - `404/502` when job not found.

### Map endpoints
- `GET /map` (HTML choropleth UI)
- `GET /map/data.json` (province rollup JSON: province, name, lat, lon, programs)
- `GET /map/canada.geojson` (static GeoJSON)

### `POST /semantic/query`
- Purpose: semantic search over program descriptions with optional LangChain Q&A summarization.
- Body:
  - `query` (str, required)
  - `province` (str, optional, code filter)
  - `discipline` (str, optional, substring filter)
  - `top_k` (int, default 5, min 1, max 20)
- Responses:
  - `200` with `{hits: [program_stream_id, names, province, discipline, similarity, description_snippet], answer?, top_k}`
  - `422` when top_k is out of bounds.

### `POST /analytics/simulate`
- Purpose: run Monte Carlo match scenarios and persist results.
- Body:
  - `scenario_type` (baseline | quota_shock | preference_shift, required)
  - `scenario_label` (optional)
  - `demand_multiplier` (float ≥0, default 1.0)
  - `quota_multiplier` (float ≥0, default 1.0)
  - `target_provinces`, `target_disciplines` (lists, optional)
  - `shift_pct` (float between -0.9 and 0.9, default 0.15 for preference_shift)
  - `iterations` (int 50–2000, default 300)
  - `seed` (int, optional)
  - `persist` (bool, default true)
- Responses:
  - `200` SimulationResponse with scenario_id, params, and province×discipline results.
  - `422` on validation errors.

### `GET /analytics/simulate/{scenario_id}`
- Purpose: retrieve a previously saved simulation result.
- Responses:
  - `200` SimulationResponse
  - `404` if scenario not found

### `GET /analytics/preferences`
- Purpose: sliceable preference scores per program using a ridge model over proxy demand (normalized quota).
- Query params:
  - `province` (str, optional, codes AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT|UNKNOWN)
  - `discipline` (str, optional, substring match, min length 2)
  - `limit` (int, default 50, min 1, max 200)
- Responses:
  - `200` with `{items:[{program ids, names, province, score, feature_values, label_proxy}], feature_importances, model_version, filters}`
  - `404` when no programs match or training data is empty
  - `422` on validation errors.
- Notes: model artifact persisted at `data/preferences_model.json` (overridable via `PREFERENCE_ARTIFACT_PATH`); uses quota as a proxy label so interpret with care.

## Error envelope
- Validation: FastAPI default `422 Unprocessable Entity` with details.
- Auth: `401` with message when API key invalid/missing.
- Rate limit: `429` with retry message.
