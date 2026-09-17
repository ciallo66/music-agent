"""SQLAlchemy 模型结构测试。"""

from __future__ import annotations

import app.models  # noqa: F401
from app.core.database import Base

EXPECTED_TABLES = {
    "artists",
    "favorites",
    "chat_sessions",
    "chat_messages",
    "music_knowledge",
    "import_jobs",
    "play_records",
    "playlist_songs",
    "playlists",
    "recommendation_feedback",
    "refresh_sessions",
    "song_tags",
    "songs",
    "tags",
    "tool_confirmations",
    "users",
}


def test_core_tables_are_registered() -> None:
    """核心关系表应全部注册到 SQLAlchemy metadata。"""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_vector_fields_allow_provider_selected_dimension() -> None:
    """歌曲和知识库向量先允许由 Embedding 服务选择维度。"""
    songs = Base.metadata.tables["songs"]

    assert "embedding" in songs.columns
    assert "embedding" in Base.metadata.tables["music_knowledge"].columns


def test_association_tables_use_composite_primary_keys() -> None:
    """多对多关联表应使用复合主键阻止重复关系。"""
    playlist_songs = Base.metadata.tables["playlist_songs"]
    song_tags = Base.metadata.tables["song_tags"]

    assert {column.name for column in playlist_songs.primary_key.columns} == {
        "playlist_id",
        "song_id",
    }
    assert {column.name for column in song_tags.primary_key.columns} == {"song_id", "tag_id"}
