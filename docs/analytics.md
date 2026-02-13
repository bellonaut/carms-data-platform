# Analytics Features

## Match simulation (`/analytics/simulate`)
- Monte Carlo engine over province x discipline supply.
- Demand model: applicants proportional to current quotas with Dirichlet noise (concentration 50) then multinomial draw; total applicants = sum(quota) x `demand_multiplier`.
- Scenario types:
  - `baseline`: no changes.
  - `quota_shock`: multiply quotas for targeted provinces/disciplines by `quota_multiplier`.
  - `preference_shift`: boost applicant weights for targets by `shift_pct` (+/-) then renormalize.
- Each run returns fill-rate mean and 5th/95th percentiles and average demand per bucket.
- Persisted to `gold_match_scenario` with `scenario_id` (UUID) when `persist=true`.

### Example
```bash
curl -X POST http://localhost:8000/analytics/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario_type":"baseline","iterations":200,"seed":123}'
```

### Response shape
- `scenario_id`, `scenario_type`, `iterations`, `seed`, `params`
- `results`: list of `{province, discipline_name, supply_quota, demand_mean, fill_rate_mean, fill_rate_p05, fill_rate_p95}`

### Defaults and limits
- `iterations`: 300 (min 50, max 2000)
- `quota_multiplier`, `demand_multiplier` must be >= 0.
- `shift_pct` allowed range: -0.9 to 0.9.

## Preference modeling (`/analytics/preferences`)
- Ridge regression over proxy demand (normalized quota) with interpretable features:
  - `discipline_freq`: share of programs in the discipline.
  - `province_mix`: share of a discipline that sits in the province.
  - `stream_is_cmg` / `stream_is_img`: stream indicator.
  - `embedding_similarity`: cosine similarity to the discipline centroid when `gold_program_embedding` exists (0 otherwise).
- Artifact: JSON persisted to `data/preferences_model.json` (override with `PREFERENCE_ARTIFACT_PATH`). Dagster asset `preference_model` refreshes it from silver data.
- Query params: `province` (code filter), `discipline` (substring, min 2 chars), `limit` (1-200).
- Response: `{items:[{program ids, names, province, score, feature_values, label_proxy}], feature_importances, model_version, filters}` sorted by score.
- Caveats: quotas are a proxy label, not observed applicant demand; embeddings mirror scraped text. Use scores for relative ranking only and avoid high-stakes decisions.

## Semantic search (`/semantic/query`) smoke
- Uses `gold_program_embedding` with pgvector on Postgres; JSON fallback on SQLite for tests/demo.
- Optional LangChain QA when `OPENAI_API_KEY` is set.
