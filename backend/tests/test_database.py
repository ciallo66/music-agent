"""本机 PostgreSQL 阶段 1 集成测试。"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.database import engine
from sqlalchemy import inspect, text

ALEMBIC_CONFIG = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
EXPECTED_TABLES = {
    "alembic_version",
    "artists",
    "favorites",
    "chat_sessions",
    "chat_messages",
    "music_knowledge",
    "import_jobs",
    "play_records",
    "playlist_songs",
    "playlists",
    "refresh_sessions",
    "song_tags",
    "songs",
    "tags",
    "tool_confirmations",
    "users",
}


def test_database_has_current_schema() -> None:
    """迁移后的数据库应包含 Alembic 和全部核心关系表。"""
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_song_embedding_column_matches_model_schema() -> None:
    """数据库应包含歌曲向量列，且允许尚未生成向量的歌曲为空。"""
    columns = {column["name"]: column for column in inspect(engine).get_columns("songs")}

    assert columns["embedding"]["nullable"] is True
    assert columns["source"]["nullable"] is True
    assert columns["source_id"]["nullable"] is True


def test_catalog_source_indexes_are_unique() -> None:
    """外部来源组合键应具备唯一索引，支持导入幂等。"""
    inspector = inspect(engine)
    for table in ("artists", "songs"):
        indexes = inspector.get_indexes(table)
        assert any(
            index["name"] == f"uq_{table}_source_source_id" and index["unique"] for index in indexes
        )


def test_import_job_active_source_index_is_unique() -> None:
    """同一来源只允许一个待执行或执行中的任务。"""
    indexes = inspect(engine).get_indexes("import_jobs")
    assert any(
        index["name"] == "uq_import_jobs_active_source" and index["unique"] for index in indexes
    )


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

    assert revision == ScriptDirectory.from_config(ALEMBIC_CONFIG).get_current_head()
