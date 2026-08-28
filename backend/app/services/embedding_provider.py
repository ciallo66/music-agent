"""可替换的 Embedding 服务客户端。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from app.core.config import settings


class EmbeddingProviderError(RuntimeError):
    """Embedding 请求或响应格式异常。"""


class EmbeddingProviderNotConfiguredError(EmbeddingProviderError):
    """Embedding 服务尚未配置。"""


class EmbeddingProvider(Protocol):
    """Embedding 服务最小接口，便于替换供应商和编写测试。"""

    @property
    def is_configured(self) -> bool:
        """返回服务是否具备调用所需配置。"""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """批量生成文本向量。"""
        ...


class OpenAICompatibleEmbeddingProvider:
    """调用兼容 OpenAI `/embeddings` 协议的服务，不绑定具体供应商。"""

    @property
    def is_configured(self) -> bool:
        """判断 API 地址、模型和密钥是否已同时配置。"""
        return all(
            (
                settings.embedding_api_key,
                settings.embedding_base_url,
                settings.embedding_model,
            )
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """为一批文本生成向量，并按输入顺序返回。"""
        inputs = [text.strip() for text in texts]
        if not inputs:
            return []
        if not self.is_configured:
            raise EmbeddingProviderNotConfiguredError("未配置 Embedding 服务")
        payload: dict[str, Any] = {
            "model": settings.embedding_model,
            "input": inputs,
            "encoding_format": "float",
        }
        try:
            response = httpx.post(
                f"{settings.embedding_base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
                json=payload,
                timeout=settings.embedding_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as error:
            raise EmbeddingProviderError("Embedding 请求超时") from error
        except (httpx.HTTPError, ValueError) as error:
            raise EmbeddingProviderError("Embedding 请求失败") from error
        return self._parse_embeddings(body, expected_count=len(inputs))

    @staticmethod
    def _parse_embeddings(body: object, expected_count: int) -> list[list[float]]:
        """校验 OpenAI-compatible 响应并按 index 排序。"""
        try:
            if not isinstance(body, dict):
                raise TypeError
            raw_items = body.get("data")
            if not isinstance(raw_items, list) or not all(
                isinstance(item, dict) for item in raw_items
            ):
                raise TypeError
            indexed = sorted(raw_items, key=lambda item: int(item["index"]))
            vectors = []
            for item in indexed:
                raw_vector = item.get("embedding")
                if not isinstance(raw_vector, list):
                    raise TypeError
                vectors.append([float(value) for value in raw_vector])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise EmbeddingProviderError("Embedding 返回格式无效") from error
        if len(vectors) != expected_count or any(not vector for vector in vectors):
            raise EmbeddingProviderError("Embedding 返回数量或向量为空")
        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise EmbeddingProviderError("Embedding 向量维度不一致")
        return vectors
