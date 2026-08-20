"""创建阶段 1 核心关系表。

Revision ID: 20260820_01
Revises: None
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建用户、音乐、歌单、标签和播放记录表。"""
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artists_name", "artists", ["name"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "songs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.Column("genre", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("audio_url", sa.String(length=2048), nullable=False),
        sa.Column("lyrics", sa.Text(), nullable=True),
        sa.Column("popularity", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "duration IS NULL OR duration >= 0", name="ck_songs_duration_nonnegative"
        ),
        sa.CheckConstraint("popularity >= 0", name="ck_songs_popularity_nonnegative"),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_songs_artist_id", "songs", ["artist_id"], unique=False)
    op.create_index("ix_songs_genre", "songs", ["genre"], unique=False)
    op.create_index("ix_songs_language", "songs", ["language"], unique=False)
    op.create_index("ix_songs_title", "songs", ["title"], unique=False)

    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlists_user_id", "playlists", ["user_id"], unique=False)

    op.create_table(
        "play_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column(
            "played_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_play_records_song_id", "play_records", ["song_id"], unique=False)
    op.create_index("ix_play_records_user_id", "play_records", ["user_id"], unique=False)
    op.create_index(
        "ix_play_records_user_played_at",
        "play_records",
        ["user_id", "played_at"],
        unique=False,
    )

    op.create_table(
        "playlist_songs",
        sa.Column("playlist_id", sa.Integer(), nullable=False),
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_playlist_songs_position_nonnegative"),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "song_id"),
        sa.UniqueConstraint("playlist_id", "position", name="uq_playlist_songs_position"),
    )

    op.create_table(
        "song_tags",
        sa.Column("song_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("song_id", "tag_id"),
    )


def downgrade() -> None:
    """按依赖逆序删除阶段 1 核心关系表。"""
    op.drop_table("song_tags")
    op.drop_table("playlist_songs")
    op.drop_index("ix_play_records_user_played_at", table_name="play_records")
    op.drop_index("ix_play_records_user_id", table_name="play_records")
    op.drop_index("ix_play_records_song_id", table_name="play_records")
    op.drop_table("play_records")
    op.drop_index("ix_playlists_user_id", table_name="playlists")
    op.drop_table("playlists")
    op.drop_index("ix_songs_title", table_name="songs")
    op.drop_index("ix_songs_language", table_name="songs")
    op.drop_index("ix_songs_genre", table_name="songs")
    op.drop_index("ix_songs_artist_id", table_name="songs")
    op.drop_table("songs")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_artists_name", table_name="artists")
    op.drop_table("artists")
