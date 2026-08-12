from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas import DbHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness only — deliberately does not touch the database."""
    return HealthResponse(status="ok", app_env=get_settings().app_env)


@router.get("/health/db", response_model=DbHealthResponse)
def health_db(db: Session = Depends(get_db)) -> DbHealthResponse:
    """Readiness: proves the API actually reached Postgres and can query it.

    This is the endpoint to hit when demonstrating that the connection works.
    """
    version = db.execute(text("SHOW server_version")).scalar_one()
    database = db.execute(text("SELECT current_database()")).scalar_one()
    return DbHealthResponse(
        status="ok",
        postgres_version=str(version),
        database=str(database),
    )
