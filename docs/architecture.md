# Architecture

## End-to-End Flow

```text
Public CaRMS Data (XLSX/CSV)
  |
  |  Dagster bronze assets:
  |  - bronze_programs
  |  - bronze_disciplines
  |  - bronze_descriptions
  v
Bronze Layer (S3 target / local data/ today)
  |
  |  Dagster silver assets + SQLModel transforms:
  |  - silver_programs
  |  - silver_disciplines
  |  - silver_description_sections
  v
Silver Layer (validated + normalized)
  |
  |  Dagster gold assets + SQLModel models:
  |  - gold_program_profiles
  |  - gold_geo_summary
  |  - gold_program_embeddings
  v
Gold Layer in PostgreSQL
  |
  |  FastAPI + SQLModel query layer
  v
API Consumers (/programs, /disciplines, /map, /pipeline, /analytics, /semantic/query)
  |
  |  Optional LangChain summarization if OPENAI_API_KEY is present
  v
RAG-style grounded response from semantic endpoint
```

## Dagster Asset Groups

### Bronze

- **Purpose:** Land source files into raw relational tables with minimal transformation.
- **Assets:** `bronze_programs`, `bronze_disciplines`, `bronze_descriptions`.
- **Source location:** Current local `data/` directory (target path can map to S3 in deployment).

### Silver

- **Purpose:** Standardize structure and quality for downstream analytics.
- **Assets:** `silver_programs`, `silver_disciplines`, `silver_description_sections`.
- **Key operations:** Province derivation, quota parsing, validity flags, and description section normalization.

### Gold

- **Purpose:** Curate serving-layer tables used directly by APIs and semantic retrieval.
- **Assets:** `gold_program_profiles`, `gold_geo_summary`, `gold_program_embeddings`.
- **Key operations:** Profile denormalization, province/discipline aggregations, text embedding generation.

## SQLModel Schema Summary

| Table name | Key fields |
| --- | --- |
| `bronze_program` | `program_stream_id` (PK), `discipline_id`, `school_name`, `program_name` |
| `bronze_discipline` | `discipline_id` (PK), `discipline` |
| `bronze_description` | `document_id` (PK), `program_description_id`, `program_name` |
| `silver_program` | `program_stream_id` (PK), `discipline_name`, `province`, `quota`, `is_valid` |
| `silver_discipline` | `discipline_id` (PK), `discipline`, `is_valid` |
| `silver_description_section` | `id` (PK), `program_description_id`, `section_name`, `section_text` |
| `gold_program_profile` | `program_stream_id` (PK), `discipline_name`, `province`, `description_text` |
| `gold_geo_summary` | `province` + `discipline_name` (composite PK), `program_count`, `avg_quota` |
| `gold_program_embedding` | `program_stream_id` (PK), `discipline_name`, `province`, `embedding` |
| `gold_match_scenario` | `scenario_id` (PK), `scenario_type`, `province`, `fill_rate_mean` |
