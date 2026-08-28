"""Embedding Provider 协议测试。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.core.config import settings
from app.services.embedding_provider import (
    EmbeddingProviderError,
    EmbeddingProviderNotConfiguredError,
    OpenAICompatibleEmbeddingProvider,
)


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
