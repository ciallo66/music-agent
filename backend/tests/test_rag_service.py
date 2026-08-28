"""知识库检索服务测试。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.models.artist import Artist
from app.models.music_knowledge import MusicKnowledge
from app.models.song import Song
from app.services.agent.music_tools import MusicAgentTools
from app.services.embedding_provider import EmbeddingProviderError
from app.services.rag_service import MusicKnowledgeService


class FakeEmbeddingProvider:
    """测试用 Embedding 服务。"""

    is_configured = True

    def embed(self, _texts: Sequence[str]) -> list[list[float]]:
        """返回固定维度向量。"""
        return [[0.1, 0.2, 0.3]]


def test_knowledge_search_uses_vector_matches(db_session: Any) -> None:
    """配置向量服务且命中时应返回相似度和 vector 模式。"""
    entry = MusicKnowledge(
        content="City Pop 使用明亮的和弦色彩。",
        source="test",
        embedding=[0.1, 0.2, 0.3],
    )
    db_session.add(entry)
    db_session.flush()
    service = MusicKnowledgeService(db_session, FakeEmbeddingProvider())

    result = service.search("City Pop", 5)

    assert result["mode"] == "vector"
    assert result["relevant"] is True
    assert result["items"][0]["similarity"] == 1.0


def test_knowledge_search_falls_back_to_lexical_when_embedding_fails(
    db_session: Any,
) -> None:
    """Embedding 服务失败时应回退关键词检索，不伪造向量命中。"""
    entry = MusicKnowledge(content="Ambient 音乐通常强调空间感。", source="test")
    db_session.add(entry)
    db_session.flush()

    class FailingProvider(FakeEmbeddingProvider):
        """始终失败的测试服务。"""

        def embed(self, _texts: Sequence[str]) -> list[list[float]]:
            raise EmbeddingProviderError("provider unavailable")

    result = MusicKnowledgeService(db_session, FailingProvider()).search("Ambient", 5)

    assert result["mode"] == "lexical"
    assert result["relevant"] is True
    assert result["items"][0]["source"] == "test"


def test_knowledge_search_marks_empty_result_as_not_relevant(db_session: Any) -> None:
    """没有匹配知识时必须返回 relevant=false。"""
    result = MusicKnowledgeService(db_session).search("不存在的术语", 5)

    assert result == {"items": [], "count": 0, "relevant": False, "mode": "lexical"}


def test_similar_song_tool_uses_vector_before_structured_fallback(db_session: Any) -> None:
    """歌曲存在向量时应优先执行 pgvector 相似度查询。"""
    artist = Artist(name="Vector Artist")
    first = Song(
        title="Vector One",
        artist=artist,
        genre="Pop",
        popularity=10,
        embedding=[0.1, 0.2, 0.3],
    )
    second = Song(
        title="Vector Two",
        artist=artist,
        genre="Pop",
        popularity=5,
        embedding=[0.1, 0.2, 0.29],
    )
    db_session.add_all([first, second])
    db_session.flush()

    result = MusicAgentTools(db_session, user_id=1).find_similar_songs(
        {"song_id": first.id, "limit": 5}
    )

    assert result["items"][0]["title"] == "Vector Two"
