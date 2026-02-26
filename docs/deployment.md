# Deployment Target (AWS)

This project is currently optimized for local Docker Compose development. The intended production shape is:

- **Compute:** Amazon ECS (Fargate) for FastAPI and Dagster services.
- **Database:** Amazon RDS/Aurora PostgreSQL for bronze/silver/gold serving tables.
- **Storage:** Amazon S3 for bronze-layer raw files and artifact persistence.

Planned production tasks:

1. Container image publishing and environment-specific ECS task definitions.
2. RDS/Aurora provisioning with migration jobs (`alembic upgrade head`).
3. Dagster schedule/sensor execution against S3 inputs.
4. Secure secrets management and API key handling through AWS-native secret stores.
