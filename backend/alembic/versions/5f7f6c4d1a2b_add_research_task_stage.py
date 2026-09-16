"""add research task stage

Revision ID: 5f7f6c4d1a2b
Revises: 338255031ae5
Create Date: 2026-09-16
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5f7f6c4d1a2b"
down_revision: str | None = "338255031ae5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_tasks",
        sa.Column("current_stage", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("research_tasks", "current_stage")
