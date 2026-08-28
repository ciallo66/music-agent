"""新增音乐知识库切片表。

Revision ID: 20260828_06
Revises: 20260828_05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260828_06"
down_revision: str | None = "20260828_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建音乐知识库切片表。"""
    op.create_table(
        "music_knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=512), nullable=True),
        sa.Column("embedding", Vector(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """删除音乐知识库切片表。"""
    op.drop_table("music_knowledge")
