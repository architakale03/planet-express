from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Sync engine + psycopg3. Chosen deliberately over async: for this workload the
# async machinery buys nothing measurable, and sync sessions are far easier to
# reason about (and to debug live) than greenlet-bridged ones. FastAPI runs the
# sync path handlers in a threadpool.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # survives Postgres restarts without a stale-connection error
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
