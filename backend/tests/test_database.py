"""本机 PostgreSQL 阶段 1 集成测试。"""

from __future__ import annotations

from app.core.database import engine
from sqlalchemy import inspect, text

EXPECTED_TABLES = {
    "alembic_version",
    "artists",
    "play_records",
    "playlist_songs",
    "playlists",
    "refresh_sessions",
    "song_tags",
    "songs",
    "tags",
    "users",
}


def test_database_has_current_schema() -> None:
    """迁移后的数据库应包含 Alembic 和全部核心关系表。"""
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_pgvector_extension_is_enabled() -> None:
    """项目数据库应启用 pgvector 扩展。"""
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()

    assert version == "0.8.6"


def test_database_is_at_expected_revision() -> None:
    """数据库应处于当前最新迁移版本。"""
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "20260825_04"
