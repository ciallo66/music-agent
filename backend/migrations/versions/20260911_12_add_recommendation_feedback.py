"""新增推荐反馈表。

Revision ID: 20260911_12
Revises: 20260910_11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_12"
down_revision: str | None = "20260910_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建推荐反馈表及索引。"""
    op.create_table(
        "recommendation_feedback",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "song_id"),
    )
    op.create_index(
        "ix_recommendation_feedback_user_id",
        "recommendation_feedback",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_feedback_action",
        "recommendation_feedback",
        ["user_id", "action"],
        unique=False,
    )


def downgrade() -> None:
    """删除推荐反馈表。"""
    op.drop_index("ix_recommendation_feedback_action", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_user_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
