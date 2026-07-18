"""rename habits.overfullfillment to overfulfillment

Revision ID: d3c7e5f1a8b2
Revises: b2f1a9c4d7e3
Create Date: 2026-07-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "d3c7e5f1a8b2"
down_revision: Union[str, Sequence[str], None] = "b2f1a9c4d7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("habits", "overfullfillment", new_column_name="overfulfillment")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("habits", "overfulfillment", new_column_name="overfullfillment")
