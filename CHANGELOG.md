# Changelog

This changelog is backfilled from git history to capture project progress over time.

## [Unreleased]

### Added
- Added analytics modules for simulation and preference modeling under `carms/analytics`.
- Added analytics API endpoints: `POST /analytics/simulate`, `GET /analytics/simulate/{scenario_id}`, and `GET /analytics/preferences`.
- Added `gold_match_scenario` persistence model and Alembic migration for simulation outputs.
- Added Dagster analytics assets for default scenario materialization and preference model artifact generation.
- Added/expanded test coverage for analytics API, simulation behavior, preference scoring, semantic search, and assets.

### Changed
- Backfilled and structured changelog entries by date and milestone.
- Updated semantic search to support PostgreSQL pgvector and SQLite cosine-similarity fallback.
- Updated embedding schema/migration logic to use pgvector on PostgreSQL and JSON fallback on SQLite.
- Updated DB engine setup for SQLite compatibility (`check_same_thread=False`, `StaticPool` for in-memory DBs).
- Updated API schemas, README endpoint matrix, and API contract docs for analytics features.

### Fixed
- Improved runtime error handling when `sentence-transformers` is not installed.
- Stabilized tests by setting default `DB_URL` values before module imports in API/model tests.

## [1.0.1] - 2026-02-13

### Added
- Added `.gitignore` entries for interview-related artifacts and job-posting items.

## 2026-02-12 (Post-v1.0.0)

### Added
- Added semantic search foundation and updated interview mastery planning docs.
- Added interview-focused project mastery study guide artifacts.
- Added one-click demo scripts for Docker and local runs.
- Added data context section and IMG insight updates in insights documentation.

### Changed
- Simplified demos to UI-only and full-platform flows.
- Cleaned root data artifacts and reorganized supporting project assets.
- Refined README links, site references, and documentation alignment.

### Fixed
- Fixed UI demo seeding by exporting `PYTHONPATH`.
- Hardened one-click demo behavior on Windows and ensured env template setup.

## [1.0.0] - 2026-02-11

### Added
- Initial platform release: Dagster -> Postgres gold -> FastAPI -> choropleth map.
- Published v1.0.0 portfolio release.
- Enabled Alembic migrations.
- Added Dagster checks.
- Consolidated the application tree structure.
- Added a comprehensive hiring audit report and a concrete hiring action plan.

### Changed
- Refreshed README screenshots and aligned image references.

## 2026-02-02 (Project Bootstrap)

### Added
- Initial project commit.
- Added foundational source artifacts, including zipped CSV/Markdown datasets and Excel files.
- Added JSON program description outputs (Markdown and HTML variants).

### Changed
- Iterated on README documentation during initial setup.
