"""add activity_logs table

Revision ID: d94b0abd68b5
Revises: b4f6a8c2d9e1
Create Date: 2026-10-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d94b0abd68b5"
down_revision: Union[str, Sequence[str], None] = "b4f6a8c2d9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "activity_logs",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "activity_type",
            sa.Enum(
                "TASK_COMPLETED",
                "HABIT_COMPLETED",
                "ITEM_PURCHASED",
                "ITEM_SOLD",
                "ITEM_USED",
                "ACHIEVEMENT_UNLOCKED",
                "LEVEL_UP",
                "DEATH",
                "DAILY_MISSED",
                "BOSS_DEFEATED",
                name="activitytype",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(length=555), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("habit_id", sa.Integer(), nullable=True),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("achievement_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("activity_logs")
    sa.Enum(name="activitytype").drop(op.get_bind(), checkfirst=True)
