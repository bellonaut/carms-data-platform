# CaRMS Data Platform

An end-to-end data platform over the public CaRMS residency data from the `dnokes/Junior-Data-Scientist` source dataset.

## Architecture

```text
Public CaRMS Data (XLSX/CSV)
  |
  |  Dagster bronze assets (bronze_programs, bronze_disciplines, bronze_descriptions)
  v
Bronze Layer (S3 target / local data/ in this repo)
  |
  |  Dagster silver assets + SQLModel transforms
  v
Silver Layer (cleaned, normalized tables)
  |
  |  Dagster gold assets + SQLModel models
  v
Gold Layer in PostgreSQL (gold_program_profile, gold_geo_summary, gold_program_embedding)
  |
  |  FastAPI routes + SQLModel sessions
  v
FastAPI API (/programs, /disciplines, /map, /pipeline, /analytics, /semantic/query)
  |
  |  Optional LangChain summarization chain when OPENAI_API_KEY is set
  v
RAG-style grounded response on semantic queries
```

## Stack

| Tool | Role in this project |
| --- | --- |
| PostgreSQL | System of record for bronze/silver/gold tables (with pgvector support). |
| SQLAlchemy/SQLModel | ORM models, schema mapping, and session management for assets and API routes. |
| Dagster | Asset orchestration across Bronze -> Silver -> Gold (and analytics assets). |
| FastAPI | REST API and interactive docs for programs, map, pipeline, semantic, and analytics endpoints. |
| Alembic | Migration workflow for schema changes. |
| MkDocs | Documentation site under `docs/` and `mkdocs.yml`. |
| Docker | Local multi-service runtime (`postgres`, `dagster`, `api`) via `docker-compose`. |
| Ruff | Linting and formatting checks. |
| pre-commit | Local hook runner for Ruff and hygiene checks before commits. |
| LangChain | Optional summarization step in `POST /semantic/query` when `OPENAI_API_KEY` is configured. |
| AWS (ECS/Fargate + RDS) | Target deployment environment - see `docs/deployment.md`. |

## Quickstart

```bash
git clone <repo-url> && cd Junior-Data-Scientist-main
cp .env.example .env
make dev
```

`make dev` runs `docker-compose up` and starts PostgreSQL, Dagster, and FastAPI.
Manual steps still required for full end-to-end data availability:

```bash
docker exec carms_dagster alembic upgrade head
docker exec carms_dagster dagster asset materialize --select "*" -m carms.pipelines.definitions --wait
```

## Project Structure

```text
carms/        # main package (Dagster assets, FastAPI app, SQLModel schemas)
alembic/      # database migrations
docs/         # MkDocs documentation
notebooks/    # Quarto-based insight reports
tests/        # pytest test suite
scripts/      # utility scripts
data/         # local data directory (gitignored - populate via pipeline)
```

## Data

This project uses public CaRMS residency program extracts (program master, disciplines, and description sections) sourced from the `dnokes/Junior-Data-Scientist` dataset lineage. The files contain program metadata, discipline mappings, and free-text program descriptions used to build bronze/silver/gold analytical tables. Populate local `data/` by running the Dagster pipeline after starting services.

## Testing

Run the test suite with:

```bash
make test
```

or:

```bash
pytest tests/
```

## Documentation

Serve docs locally with:

```bash
mkdocs serve
```

## What's Next

- Deploy the current compose stack to AWS ECS/Fargate with PostgreSQL on RDS/Aurora.
- Move bronze ingestion from local `data/` to S3-backed ingestion contracts.
- Harden the LangChain path with retrieval evaluation and prompt regression tests.
- Add CI gates for tests, Ruff, pre-commit, and strict MkDocs build checks.
- Publish operational runbooks for migration, backfill, and rollback workflows.
