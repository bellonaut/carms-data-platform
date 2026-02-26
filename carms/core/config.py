from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    db_url: str = Field(
        default="postgresql+psycopg2://carms_app:carms_secret@postgres:5432/carms",
        env="DB_URL",
    )
    env: str = Field(default="local", env="ENV")
    dagster_graphql_url: str = Field(
        default="http://dagster:3000/graphql",
        env="DAGSTER_GRAPHQL_URL",
    )
    api_key: str | None = Field(default=None, env="API_KEY")
    rate_limit_requests: int = Field(default=120, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_sec: int = Field(default=60, env="RATE_LIMIT_WINDOW_SEC")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
