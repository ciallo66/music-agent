"""歌曲和音乐知识的批量向量化服务。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy.orm import Session

from app.models.music_knowledge import MusicKnowledge
from app.models.song import Song
from app.repositories.catalog_repository import SongRepository
from app.repositories.music_knowledge_repository import MusicKnowledgeRepository
from app.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderNotConfiguredError,
)

EmbeddingTarget = Literal["songs", "knowledge"]


@dataclass(frozen=True)
class EmbeddingReport:
    """一次批量向量化的处理统计。"""

    target: EmbeddingTarget
    processed: int
    remaining: int


class EmbeddingBatchService:
    """为尚未向量化的歌曲或知识切片生成并写入 embedding。"""

    def __init__(self, db: Session, provider: EmbeddingProvider) -> None:
        self.db = db
        self.provider = provider
        self.songs = SongRepository(db)
        self.knowledge = MusicKnowledgeRepository(db)

    def embed_missing(
        self,
        target: EmbeddingTarget,
        *,
        limit: int = 100,
        batch_size: int = 32,
        dry_run: bool = False,
    ) -> EmbeddingReport:
        """批量处理缺少向量的记录；事务提交由调用边界负责。"""
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        if batch_size < 1:
            raise ValueError("batch_size 必须大于 0")
        if not self.provider.is_configured:
            raise EmbeddingProviderNotConfiguredError("未配置 Embedding 服务")

        processed = 0
        while processed < limit:
            current_limit = min(batch_size, limit - processed)
            items = self._list_missing(target, current_limit)
            if not items:
                break
            vectors = self.provider.embed([self._text_for(target, item) for item in items])
            for item, vector in zip(items, vectors, strict=True):
                item.embedding = vector
            self.db.flush()
            processed += len(items)
            if dry_run:
                break

        remaining = len(self._list_missing(target, 1))
        return EmbeddingReport(target=target, processed=processed, remaining=remaining)

    def _list_missing(self, target: EmbeddingTarget, limit: int) -> list[Song | MusicKnowledge]:
        """按目标类型读取未完成记录。"""
        if target == "songs":
            return [item for item in self.songs.list_without_embeddings(limit)]
        return [item for item in self.knowledge.list_without_embeddings(limit)]

    @staticmethod
    def _text_for(target: EmbeddingTarget, item: Song | MusicKnowledge) -> str:
        """构造稳定的向量化文本，不包含用户私有信息。"""
        if target == "knowledge":
            knowledge = cast(MusicKnowledge, item)
            return "\n".join(part for part in (knowledge.source, knowledge.content) if part)

        song = cast(Song, item)
        fields = (
            song.title,
            song.artist.name,
            song.album,
            song.genre,
            song.language,
            song.instruments,
            song.song_structure,
        )
        return " | ".join(part for part in fields if part)
