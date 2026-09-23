"""为向量列钉定维度并建立 HNSW 索引。

背景：`songs.embedding` 与 `music_knowledge.embedding` 当初建成了**无维度**的 `vector`，
而 pgvector 只允许在**声明了维度**的向量列上建 HNSW / IVFFlat 索引。没有索引时每次
相似度检索都要全表算余弦距离，数据量一上去就线性变慢。

这条迁移做两件事：
1. 把两列钉成 `vector(1024)`（与配置的 Embedding 模型 BAAI/bge-m3 一致）；
2. 在 cosine 距离上建 HNSW 索引（`vector_cosine_ops`）。

为什么是 1024：线上与本地库的向量维度实测都是 1024。**代价要说清楚**：维度从此固定，
换用其它维度的 Embedding 模型必须新写一条迁移改列（见 `EMBEDDING_DIMENSION` 配置项）。
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260923_15"
down_revision: str | None = "20260920_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 与 Embedding 模型（BAAI/bge-m3）一致；换模型要同步改这里并新写迁移。
EMBEDDING_DIMENSION = 1024


def upgrade() -> None:
    """钉定向量维度并建 HNSW 余弦索引。"""
    # 建索引前先确认库里没有别的维度，否则直接报错而不是留下一个坏索引。
    op.execute(
        f"""
        DO $$
        DECLARE
            bad_dim integer;
        BEGIN
            SELECT vector_dims(embedding) INTO bad_dim
            FROM songs
            WHERE embedding IS NOT NULL AND vector_dims(embedding) <> {EMBEDDING_DIMENSION}
            LIMIT 1;
            IF bad_dim IS NOT NULL THEN
                RAISE EXCEPTION 'songs.embedding 存在 % 维向量，与目标维度 % 不一致',
                    bad_dim, {EMBEDDING_DIMENSION};
            END IF;

            SELECT vector_dims(embedding) INTO bad_dim
            FROM music_knowledge
            WHERE embedding IS NOT NULL AND vector_dims(embedding) <> {EMBEDDING_DIMENSION}
            LIMIT 1;
            IF bad_dim IS NOT NULL THEN
                RAISE EXCEPTION 'music_knowledge.embedding 存在 % 维向量，与目标维度 % 不一致',
                    bad_dim, {EMBEDDING_DIMENSION};
            END IF;
        END
        $$;
        """
    )

    # 无维度 vector → vector(N)：已有数据维度一致才允许。
    op.execute("ALTER TABLE songs ALTER COLUMN embedding TYPE vector(%d)" % EMBEDDING_DIMENSION)
    op.execute(
        "ALTER TABLE music_knowledge ALTER COLUMN embedding TYPE vector(%d)" % EMBEDDING_DIMENSION
    )

    # HNSW：查询时不需要训练、对增量写入友好，适合本项目这种边导入边检索的场景。
    op.execute(
        "CREATE INDEX ix_songs_embedding_hnsw ON songs "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_music_knowledge_embedding_hnsw ON music_knowledge "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """删除 HNSW 索引并把向量列还原为无维度类型。"""
    op.execute("DROP INDEX IF EXISTS ix_songs_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_music_knowledge_embedding_hnsw")
    op.execute("ALTER TABLE songs ALTER COLUMN embedding TYPE vector")
    op.execute("ALTER TABLE music_knowledge ALTER COLUMN embedding TYPE vector")
