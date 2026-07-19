"""notification read state and drop dead available_in_shop

Revision ID: b4f6a8c2d9e1
Revises: a2d4f6b8c1e5
Create Date: 2026-07-19 01:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "b4f6a8c2d9e1"
down_revision: Union[str, Sequence[str], None] = "a2d4f6b8c1e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "notifications",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.drop_column("items", "available_in_shop")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "items",
        sa.Column("available_in_shop", sa.Boolean(), nullable=True),
    )
    op.drop_column("notifications", "is_read")
