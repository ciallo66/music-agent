"""为歌曲增加可选向量字段。"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260828_08"
down_revision: str | None = "20260828_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加歌曲向量列；维度由配置的 Embedding 模型决定。"""
    op.add_column("songs", sa.Column("embedding", Vector(), nullable=True))


def downgrade() -> None:
    """删除歌曲向量列。"""
    op.drop_column("songs", "embedding")
