from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives at the repo root, beside docker-compose.yml, so Compose reads it
    # without --env-file. Every local entrypoint (uvicorn, alembic, pytest) runs
    # with api/ as cwd, hence "../.env". Later entries win in pydantic-settings,
    # so ".env" comes second: a file dropped in api/ overrides the root one for a
    # one-off. Both are optional — a missing env_file is not an error. Inside the
    # container neither path exists, and nothing needs them: real environment
    # variables outrank the file, so the DATABASE_URL Compose injects wins there.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/planet_express"
    app_env: str = "development"
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
