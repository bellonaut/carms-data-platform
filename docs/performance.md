# Performance Notes

## API Query Indexing

The `gold_program_profile` table now has dedicated indexes for high-frequency filters used by `/programs`:

- `ix_gold_program_profile_province`
- `ix_gold_program_profile_discipline_name`
- `ix_gold_program_profile_school_name`

These indexes are created in the Alembic baseline migration (`alembic/versions/20260211_0001_create_core_schema.py`) and mirrored in SQLModel field definitions.

## Why These Indexes

`GET /programs` supports filter combinations on:
- `province` (exact match)
- `discipline_name` (substring)
- `school_name` (substring)

While `%...%` predicates on substring filters may not always fully use b-tree indexes, indexing these fields still improves selective filtering patterns and supports future optimization (e.g., trigram indexes or materialized search views).

## Validation Workflow

For local profiling, run:

```sql
EXPLAIN ANALYZE
SELECT *
FROM gold_program_profile
WHERE province = 'ON'
ORDER BY program_stream_id
LIMIT 100;
```

And for combined filters:

```sql
EXPLAIN ANALYZE
SELECT *
FROM gold_program_profile
WHERE province = 'ON'
  AND discipline_name ILIKE '%internal medicine%'
LIMIT 100;
```

Capture before/after runtime snapshots when introducing additional indexes.

## Pagination Guardrails

API pagination defaults and limits are intentionally constrained:
- `limit` default 100
- `limit` max 500

This prevents unbounded scans and oversized payloads during exploratory use.
