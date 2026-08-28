"""新增用户收藏表。

Revision ID: 20260828_05
Revises: 20260825_04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_05"
down_revision: str | None = "20260825_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建收藏表和查询索引。"""
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "song_id", name="uq_favorites_user_song"),
    )
    op.create_index("ix_favorites_song_id", "favorites", ["song_id"], unique=False)
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"], unique=False)


def downgrade() -> None:
    """删除收藏表。"""
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_index("ix_favorites_song_id", table_name="favorites")
    op.drop_table("favorites")
