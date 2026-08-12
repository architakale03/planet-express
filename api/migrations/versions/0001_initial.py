"""initial schema: empty base

Revision ID: 0001
Revises:
Create Date: 2026-08-10

The stack ships with no domain tables. This revision is deliberately a no-op: it
is kept rather than deleted so a database already stamped "0001" still resolves
head, and so the first real schema change has a base to chain off.

"""
from collections.abc import Sequence

from alembic import op  # noqa: F401

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
