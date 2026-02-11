# Architecture

- **Storage:** PostgreSQL 16 with pgvector extension for future semantic search over program descriptions.
- **Orchestration:** Dagster assets grouped by layer (bronze, silver, gold), with asset checks for basic data quality guardrails.
- **API:** FastAPI app in `carms/api` serving program/disciplines endpoints, map views, and a pipeline trigger.
- **Infrastructure:** Docker Compose runs Postgres, Dagster webserver (`dagster dev`), and API with shared environment variables.

## Data Lineage
1. **Bronze (legacy ingestion):** direct load from the provided Excel/CSV extracts into `bronze_*` tables.
2. **Silver (modern standardized layer):** cleans column noise, normalizes types, adds provinces and validity flags, and unpivots description sections.
3. **Gold:** builds program profiles and geographic rollups for analytics and API serving.

## Schema Management
- Schema changes are migration-driven with Alembic.
- Apply latest schema with:
  - `alembic upgrade head`
- Create a new migration with:
  - `alembic revision -m "<message>"`

## Environments
- Configure via `.env` (DB URL, secrets). Pydantic settings are centralized in `carms/core/config.py`.
