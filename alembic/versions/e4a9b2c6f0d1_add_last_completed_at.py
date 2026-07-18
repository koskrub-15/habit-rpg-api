"""add last_completed_at to habits and tasks

Revision ID: e4a9b2c6f0d1
Revises: d3c7e5f1a8b2
Create Date: 2026-07-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "e4a9b2c6f0d1"
down_revision: Union[str, Sequence[str], None] = "d3c7e5f1a8b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "habits",
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tasks", "last_completed_at")
    op.drop_column("habits", "last_completed_at")
