"""本机 PostgreSQL 阶段 1 集成测试。"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import settings
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


def test_database_has_current_schema() -> None:
    """迁移后的数据库应包含 Alembic 和全部核心关系表。"""
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_song_embedding_column_matches_model_schema() -> None:
    """数据库应包含歌曲向量列，且允许尚未生成向量的歌曲为空。"""
    columns = {column["name"]: column for column in inspect(engine).get_columns("songs")}

    assert columns["embedding"]["nullable"] is True
    assert columns["source"]["nullable"] is True
    assert columns["source_id"]["nullable"] is True


def test_embedding_columns_are_dimensioned() -> None:
    """向量列必须声明固定维度，否则 HNSW 索引建不了。"""
    with engine.connect() as connection:
        for table in ("songs", "music_knowledge"):
            column_type = connection.execute(
                text(
                    "select format_type(a.atttypid, a.atttypmod) "
                    "from pg_attribute a join pg_class c on c.oid = a.attrelid "
                    "where c.relname = :table and a.attname = 'embedding'"
                ),
                {"table": table},
            ).scalar_one()
            assert column_type == f"vector({settings.embedding_dimension})", column_type


def test_hnsw_indexes_exist_on_vector_columns() -> None:
    """两个向量列都应存在 HNSW 索引，保证相似度检索不退化成全表扫描。"""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select i.indexname, i.indexdef, am.amname "
                "from pg_indexes i "
                "join pg_class c on c.relname = i.indexname "
                "join pg_am am on am.oid = c.relam "
                "where i.tablename in ('songs', 'music_knowledge') and am.amname = 'hnsw'"
            )
        ).fetchall()

    indexed_tables = {row[0] for row in rows}
    assert indexed_tables == {"ix_songs_embedding_hnsw", "ix_music_knowledge_embedding_hnsw"}
    assert all("vector_cosine_ops" in row[1] for row in rows)


def test_catalog_source_indexes_are_unique() -> None:
    """外部来源组合键应具备唯一索引，支持导入幂等。"""
    inspector = inspect(engine)
    for table in ("artists", "songs"):
        indexes = inspector.get_indexes(table)
        assert any(
            index["name"] == f"uq_{table}_source_source_id" and index["unique"] for index in indexes
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
