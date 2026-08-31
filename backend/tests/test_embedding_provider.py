"""Embedding Provider 协议测试。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from app.core.config import settings
from app.models import Artist, Song
from app.services.embedding_batch_service import EmbeddingBatchService
from app.services.embedding_provider import (
    EmbeddingProviderError,
    EmbeddingProviderNotConfiguredError,
    OpenAICompatibleEmbeddingProvider,
)
from sqlalchemy import select


def test_embedding_provider_parses_indexed_vectors(monkeypatch: Any) -> None:
    """Provider 应按输入顺序解析 OpenAI-compatible 向量响应。"""
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            }

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_base_url", "https://embedding.test/v1")
    monkeypatch.setattr(settings, "embedding_model", "test-embedding")
    monkeypatch.setattr(httpx, "post", fake_post)

    vectors = OpenAICompatibleEmbeddingProvider().embed(["第一段", "第二段"])

    assert captured["url"] == "https://embedding.test/v1/embeddings"
    assert captured["json"]["model"] == "test-embedding"
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embedding_provider_requires_configuration(monkeypatch: Any) -> None:
    """未配置 Embedding 服务时应明确失败，不发起网络请求。"""
    monkeypatch.setattr(settings, "embedding_api_key", "")
    monkeypatch.setattr(settings, "embedding_base_url", "")
    monkeypatch.setattr(settings, "embedding_model", "")

    with pytest.raises(EmbeddingProviderNotConfiguredError, match="未配置"):
        OpenAICompatibleEmbeddingProvider().embed(["测试"])


def test_embedding_provider_rejects_inconsistent_dimensions(monkeypatch: Any) -> None:
    """不同文本返回不同维度时应拒绝写入向量库。"""

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2]},
                    {"index": 1, "embedding": [0.3]},
                ]
            }

    monkeypatch.setattr(settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_base_url", "https://embedding.test/v1")
    monkeypatch.setattr(settings, "embedding_model", "test-embedding")
    monkeypatch.setattr(httpx, "post", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(EmbeddingProviderError, match="维度不一致"):
        OpenAICompatibleEmbeddingProvider().embed(["第一段", "第二段"])


def test_embedding_batch_service_processes_missing_songs_in_batches(db_session: Any) -> None:
    """批量向量化只处理缺失项，重复执行不会覆盖或新增记录。"""
    artist = Artist(name="测试歌手")
    db_session.add(artist)
    db_session.flush()
    db_session.add_all([Song(title=f"歌曲 {index}", artist_id=artist.id) for index in range(3)])
    db_session.flush()

    class FakeProvider:
        is_configured = True

        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return [[float(index), 1.0] for index, _ in enumerate(texts)]

    service = EmbeddingBatchService(db_session, FakeProvider())
    first = service.embed_missing("songs", limit=2, batch_size=2)
    second = service.embed_missing("songs", limit=2, batch_size=2)

    assert (first.processed, first.remaining) == (2, 1)
    assert (second.processed, second.remaining) == (1, 0)
    assert all(song.embedding is not None for song in db_session.scalars(select(Song)).all())
