"""add_preferred_languages

Revision ID: 0002_add_preferred_languages
Revises: 0001_initial_tables
Create Date: 2026-10-20 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_preferred_languages"
down_revision: str | None = "0001_initial_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    try:
        op.add_column("users", sa.Column("preferred_book_languages", sa.JSON(), nullable=True, server_default="[]"))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column("users", "preferred_book_languages")
    except Exception:
        pass
