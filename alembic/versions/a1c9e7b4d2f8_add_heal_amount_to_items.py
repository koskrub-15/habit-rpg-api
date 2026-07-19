"""add heal_amount to items

Revision ID: a1c9e7b4d2f8
Revises: f5b1d8e3a7c2
Create Date: 2026-07-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "a1c9e7b4d2f8"
down_revision: Union[str, Sequence[str], None] = "f5b1d8e3a7c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "items",
        sa.Column("heal_amount", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("items", "heal_amount")
