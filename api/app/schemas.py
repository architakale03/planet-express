from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_env: str


class DbHealthResponse(BaseModel):
    status: str
    postgres_version: str
    database: str
