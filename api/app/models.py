"""SQLAlchemy models.

Empty by design — the stack ships with no domain tables yet. Declare models here
against `Base`, then add an Alembic revision; `migrations/env.py` imports this
module so anything declared here registers on `Base.metadata` for autogenerate.
"""

from app.db import Base  # noqa: F401
