"""为 songs 表增加音乐特征字段（对齐开发书：BPM/Key/Energy/Valence 等）。

Revision ID: 20260825_04
Revises: 20260821_03
Create Date: 2026-08-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_04"
down_revision: str | None = "20260821_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为歌曲表增加专辑和音乐特征字段，并允许音频地址为空。"""
    op.add_column("songs", sa.Column("album", sa.String(length=255), nullable=True))
    op.add_column("songs", sa.Column("bpm", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("music_key", sa.String(length=20), nullable=True))
    op.add_column("songs", sa.Column("energy", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("valence", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("danceability", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("loudness", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("instruments", sa.String(length=255), nullable=True))
    op.add_column("songs", sa.Column("song_structure", sa.Text(), nullable=True))
    op.alter_column("songs", "audio_url", existing_type=sa.String(length=2048), nullable=True)

    op.create_check_constraint("ck_songs_bpm_positive", "songs", "bpm IS NULL OR bpm > 0")
    op.create_check_constraint(
        "ck_songs_energy_range", "songs", "energy IS NULL OR (energy >= 0 AND energy <= 1)"
    )
    op.create_check_constraint(
        "ck_songs_valence_range", "songs", "valence IS NULL OR (valence >= 0 AND valence <= 1)"
    )
    op.create_check_constraint(
        "ck_songs_danceability_range",
        "songs",
        "danceability IS NULL OR (danceability >= 0 AND danceability <= 1)",
    )
    op.create_index("ix_songs_bpm", "songs", ["bpm"], unique=False)
    op.create_index("ix_songs_energy", "songs", ["energy"], unique=False)


def downgrade() -> None:
    """回滚：删除索引、约束和新字段。"""
    op.drop_index("ix_songs_energy", table_name="songs")
    op.drop_index("ix_songs_bpm", table_name="songs")
    op.drop_constraint("ck_songs_danceability_range", "songs", type_="check")
    op.drop_constraint("ck_songs_valence_range", "songs", type_="check")
    op.drop_constraint("ck_songs_energy_range", "songs", type_="check")
    op.drop_constraint("ck_songs_bpm_positive", "songs", type_="check")
    op.alter_column("songs", "audio_url", existing_type=sa.String(length=2048), nullable=False)
    op.drop_column("songs", "song_structure")
    op.drop_column("songs", "instruments")
    op.drop_column("songs", "loudness")
    op.drop_column("songs", "danceability")
    op.drop_column("songs", "valence")
    op.drop_column("songs", "energy")
    op.drop_column("songs", "music_key")
    op.drop_column("songs", "bpm")
    op.drop_column("songs", "album")
