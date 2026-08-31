"""为目录记录增加外部数据源幂等标识。"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_09"
down_revision: str | None = "20260828_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加来源和来源 ID，并保证同一来源 ID 不重复。"""
    op.add_column("artists", sa.Column("source", sa.String(length=50), nullable=True))
    op.add_column("artists", sa.Column("source_id", sa.String(length=100), nullable=True))
    op.create_index("uq_artists_source_source_id", "artists", ["source", "source_id"], unique=True)
    op.add_column("songs", sa.Column("source", sa.String(length=50), nullable=True))
    op.add_column("songs", sa.Column("source_id", sa.String(length=100), nullable=True))
    op.create_index("uq_songs_source_source_id", "songs", ["source", "source_id"], unique=True)


def downgrade() -> None:
    """删除外部数据源标识。"""
    op.drop_index("uq_songs_source_source_id", table_name="songs")
    op.drop_column("songs", "source_id")
    op.drop_column("songs", "source")
    op.drop_index("uq_artists_source_source_id", table_name="artists")
    op.drop_column("artists", "source_id")
    op.drop_column("artists", "source")
