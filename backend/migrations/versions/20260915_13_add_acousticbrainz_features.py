"""为歌曲增加 AcousticBrainz 结构化分析字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260915_13"
down_revision: str | None = "20260911_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加可追溯的节奏、调性、频谱、情绪和人声分析结果。"""
    op.add_column("songs", sa.Column("voice_instrumental", sa.String(length=32), nullable=True))
    op.add_column("songs", sa.Column("voice_probability", sa.Float(), nullable=True))
    for name in (
        "rhythm_features",
        "tonal_features",
        "spectral_features",
        "mood_labels",
        "genre_labels",
        "analysis_metadata",
    ):
        op.add_column(
            "songs",
            sa.Column(name, postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    op.add_column("songs", sa.Column("feature_completeness", sa.Float(), nullable=True))
    op.create_check_constraint(
        "ck_songs_voice_probability_range",
        "songs",
        "voice_probability IS NULL OR (voice_probability >= 0 AND voice_probability <= 1)",
    )
    op.create_check_constraint(
        "ck_songs_feature_completeness_range",
        "songs",
        "feature_completeness IS NULL OR (feature_completeness >= 0 AND feature_completeness <= 1)",
    )
    op.create_index("ix_songs_voice_instrumental", "songs", ["voice_instrumental"])


def downgrade() -> None:
    """删除 AcousticBrainz 新增字段，保留旧歌曲特征列。"""
    op.drop_index("ix_songs_voice_instrumental", table_name="songs")
    op.drop_constraint("ck_songs_feature_completeness_range", "songs", type_="check")
    op.drop_constraint("ck_songs_voice_probability_range", "songs", type_="check")
    op.drop_column("songs", "feature_completeness")
    for name in (
        "analysis_metadata",
        "genre_labels",
        "mood_labels",
        "spectral_features",
        "tonal_features",
        "rhythm_features",
    ):
        op.drop_column("songs", name)
    op.drop_column("songs", "voice_probability")
    op.drop_column("songs", "voice_instrumental")
