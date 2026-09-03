"""音乐知识检索服务：向量优先，文本检索兜底。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.music_knowledge_repository import MusicKnowledgeRepository
from app.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
)

logger = logging.getLogger(__name__)


class MusicKnowledgeService:
    """编排知识库向量检索、阈值过滤和文本兜底。"""

    def __init__(self, db: Session, embedding_provider: EmbeddingProvider | None = None) -> None:
        """注入知识库仓储和可选向量服务；未配置时保持可查询的降级路径。"""
        self.repository = MusicKnowledgeRepository(db)
        self.embedding_provider = embedding_provider

    def search(self, query: str, limit: int) -> dict[str, Any]:
        """检索相关知识；无向量服务或无匹配时回退到文本检索。"""
        normalized_query = query.strip()
        if not normalized_query:
            return self._empty_result("lexical")

        if self.embedding_provider is not None and self.embedding_provider.is_configured:
            vector_result = self._search_vector(normalized_query, limit)
            if vector_result is not None and vector_result["items"]:
                return vector_result

        return self._search_lexical(normalized_query, limit)

    def _search_vector(self, query: str, limit: int) -> dict[str, Any] | None:
        """调用 Embedding 和 pgvector；异常时保留事务可继续执行。"""
        provider = self.embedding_provider
        if provider is None:
            return None
        try:
            vectors = provider.embed([query])
            embedding = vectors[0]
        except (EmbeddingProviderError, IndexError) as error:
            logger.warning("知识库向量生成失败，回退文本检索：%s", error)
            return None

        try:
            with self.repository.db.begin_nested():
                matches = self.repository.search_vector(
                    embedding,
                    limit,
                    settings.embedding_similarity_threshold,
                )
        except SQLAlchemyError:
            logger.exception("知识库向量查询失败，回退文本检索")
            return None
        return {
            "items": [
                {
                    "content": entry.content,
                    "source": entry.source,
                    "similarity": round(max(0.0, min(1.0, 1 - distance)), 4),
                }
                for entry, distance in matches
            ],
            "count": len(matches),
            "relevant": bool(matches),
            "mode": "vector",
        }

    def _search_lexical(self, query: str, limit: int) -> dict[str, Any]:
        """执行无额外模型依赖的关键词检索。"""
        entries = self.repository.search(query, limit)
        return {
            "items": [{"content": entry.content, "source": entry.source} for entry in entries],
            "count": len(entries),
            "relevant": bool(entries),
            "mode": "lexical",
        }

    @staticmethod
    def _empty_result(mode: str) -> dict[str, Any]:
        """构造空检索结果，明确告诉模型不要硬答。"""
        return {"items": [], "count": 0, "relevant": False, "mode": mode}
