# CaRMS Analytics Platform

Built by Bashir ("bellonaut") Bello. I love intuitive, interactive maps--see the [Health Desert explorer](https://bashir-healthdesert.streamlit.app) built from the [health-desert-scorer](https://github.com/bellonaut/health-desert-scorer) repo--so the province choropleth comes from that obsession. My younger brother will be an IMG soon, so the insights lean toward that lens; check the static write-up at [docs/insights.html](docs/insights.html).

### What it is
An end-to-end, production-style data platform for the public CaRMS residency program dataset. It ingests raw Excel/CSV extracts, shapes them into bronze -> silver -> gold tables with Dagster and Postgres (pgvector-ready), and serves both program search APIs and a province-level choropleth map via FastAPI. The goal is to showcase systems thinking for a junior data scientist focused on data engineering, analytics, and delivery.

### Demo options (pick one)
| Mode | Stack | Data path | Run (macOS/Linux) | Run (Windows) | Opens |
|------|-------|-----------|-------------------|---------------|-------|
| UI-only demo | FastAPI + SQLite | Synthetic seed into gold tables | `make ui-demo` | `powershell -ExecutionPolicy Bypass -File scripts/ui_demo.ps1` | /docs, /map (FastAPI only) |
| Full platform demo | Docker: Postgres + Dagster + API | Dagster materializes bronze -> silver -> gold | `make demo` | `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1` | Dagster UI :3000, /docs, /map |

### Architecture (ASCII)
```
           +-------------+
           | Source CSV  |
           +------+------+
                  |
                  v
         +--------+--------+        Docker Compose
         |  Dagster Assets |        (Postgres, Dagster UI, API)
         | bronze/silver   |
         +--------+--------+
                  |
                  v
         +-----------------+   Postgres (pgvector enabled)
         |   Gold Layer    |   gold_program_profile
         |                 |   gold_geo_summary
         +--------+--------+
                  |
        +---------+---------+
        | FastAPI + SQLModel|
        +----+-----------+--+
             |           |
      /programs JSON   /map HTML (Plotly)
```

### Data layers
- bronze_program / bronze_discipline / bronze_description - raw CaRMS extracts as-is.
- silver_program - cleaned columns, province derivation, quota parsing, validity flags.
- silver_description_section - unpivoted description text per section.
- gold_program_profile - curated program metadata plus concatenated descriptions.
- gold_program_embedding - pgvector embeddings from gold descriptions for semantic search.
- gold_geo_summary - province x discipline rollups with program counts and avg quota.

### UI-only demo (FastAPI + seeded SQLite)
- Commands: `make ui-demo` (macOS/Linux) OR `powershell -ExecutionPolicy Bypass -File scripts/ui_demo.ps1` (Windows).
- Starts FastAPI on http://localhost:8000; opens Swagger at `/docs` and the map at `/map`.
- Seeds synthetic gold tables so `/programs` and `/map` return data; `/pipeline/run` is not available here.

### Full platform demo (Docker + Dagster + Postgres)
- Commands: `make demo` (macOS/Linux) OR `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1` (Windows).
- Builds/starts Docker Compose, applies Alembic in the container, materializes assets bronze -> silver -> gold.
- Opens Dagster UI at http://localhost:3000 plus FastAPI `/docs` and `/map` on http://localhost:8000.

### Run it in 10 minutes (manual)
1. `cp .env.example .env`
2. `docker-compose up --build`
3. Run migrations: `alembic upgrade head`
4. Visit Dagster UI `http://localhost:3000` and run job `carms_job` (materializes bronze -> silver -> gold).
5. Check API docs at `http://localhost:8000/docs` and the map at `http://localhost:8000/map`.

If ports are in use from an earlier run, stop and reset:
- UI-only: remove `.venv-demo` and `demo.db`, then rerun the script.
- Full platform: `docker compose down -v`

### Endpoints
| Method | Path | Purpose | Key params |
|--------|------|---------|------------|
| GET | `/health` | Liveness | - |
| GET | `/programs` | List/search programs | discipline, province, school, limit, offset, include_total, preview_chars |
| GET | `/programs/{program_stream_id}` | Program detail | program_stream_id |
| GET | `/disciplines` | Active discipline lookup | - |
| POST | `/pipeline/run` | Trigger Dagster carms_job via GraphQL | - |
  | GET | `/map` | Choropleth HTML | - |
  | GET | `/map/data.json` | Province rollup JSON | - |
  | GET | `/map/canada.geojson` | GeoJSON | - |
  | POST | `/semantic/query` | Semantic search with optional LangChain QA summary | query, province?, discipline?, top_k |
  | POST / GET | `/analytics/simulate` | Monte Carlo match scenarios | scenario_type, demand/quota multipliers, shift_pct, iterations |
  | GET | `/analytics/preferences` | Preference scores + feature importances | province, discipline, limit |

Security and limits (configurable via `.env`):
- X-API-Key header enforced when `API_KEY` is set.
- Rate limit: `RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SEC` (default 120/min per client IP).

### 5-minute demo script
1) Open `/docs` and run `GET /programs?province=ON&limit=5` to show filters and pagination.  
2) Click `/programs/{id}` for a detail view with full description text.  
3) In Dagster (`http://localhost:3000`), open job `carms_job` to show the bronze/silver/gold asset graph.  
4) Open `/map`, toggle choropleth vs bubble, hover a province to show counts and share.  
5) Mention optional API key plus rate limiting and point to `docs/api-contract.md`.

### Insights notebook
- Static HTML render with province/discipline mix, IMG lens, and description similarity: [docs/insights.html](docs/insights.html)

### Screenshots
#### Province choropleth (program count)
![Choropleth map](docs/images/map-program-count.png)

#### API list + filters
![Program list](docs/images/program-filter.png)

#### Discipline lookup
![Disciplines](docs/images/disciplines-search.png)

#### Pipelines (Dagster assets)
![Dagster](docs/images/dagster-assets.png)

#### Program detail view
![Program detail](docs/images/program-view.png)


### Roadmap
- Expand preference modeling + scenario simulation with stored results.
- Performance notes: [docs/performance.md](docs/performance.md)
- Schedule Dagster runs with data quality checks and freshness alerts.
- Deploy a lightweight demo (RDS + ECS/Fargate or Fly) with CI (pytest + ruff).

### Sharing a clean copy
- Source data now lives under `data/`; heavy root archives were removed to keep the repo lean.
- After staging/committing, create a slim zip for HR with: `git archive --format=zip -o carms_hr.zip HEAD`.

### License
MIT

More about me: [www.bashir.bio](https://www.bashir.bio)
