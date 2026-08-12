import logging

from fastapi import FastAPI

from app.config import get_settings
from app.routers import health

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(
    title="Planet Express API",
    description="FastAPI + PostgreSQL service, containerized with Docker Compose.",
    version="0.1.0",
)

app.include_router(health.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "planet-express-api", "docs": "/docs", "db_check": "/health/db"}
