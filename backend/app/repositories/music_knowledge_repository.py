"""音乐知识库数据访问。"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.music_knowledge import MusicKnowledge


class MusicKnowledgeRepository:
    """封装音乐知识切片的只读检索。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, query: str, limit: int) -> list[MusicKnowledge]:
        """按查询词进行基础文本检索，向量检索在知识向量导入后启用。"""
        terms = [term for term in query.split() if term]
        if not terms:
            return []
        conditions = [MusicKnowledge.content.ilike(f"%{term}%") for term in terms]
        statement = select(MusicKnowledge).where(or_(*conditions)).limit(limit)
        return list(self.db.scalars(statement))

    def search_vector(
        self, embedding: list[float], limit: int, threshold: float
    ) -> list[tuple[MusicKnowledge, float]]:
        """按知识切片向量余弦相似度查询结果。"""
        distance = MusicKnowledge.embedding.cosine_distance(embedding)
        statement = (
            select(MusicKnowledge, distance.label("distance"))
            .where(
                MusicKnowledge.embedding.is_not(None),
                distance <= 1 - threshold,
            )
            .order_by(distance, MusicKnowledge.id)
            .limit(limit)
        )
        return [
            (item, float(distance_value)) for item, distance_value in self.db.execute(statement)
        ]

    def list_without_embeddings(self, limit: int) -> list[MusicKnowledge]:
        """按主键顺序读取尚未生成向量的知识切片。"""
        statement = (
            select(MusicKnowledge)
            .where(MusicKnowledge.embedding.is_(None))
            .order_by(MusicKnowledge.id)
            .limit(limit)
        )
        return list(self.db.scalars(statement))
