"""音乐 Agent 的只读业务工具。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.song import Song
from app.repositories.catalog_repository import SongRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.agent import (
    KnowledgeSearchInput,
    SearchSongsInput,
    SimilarSongsInput,
    SongIdInput,
)
from app.schemas.catalog import SongDetail, SongSummary
from app.services.agent.registry import AgentTool, ToolRegistry
from app.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
    OpenAICompatibleEmbeddingProvider,
)
from app.services.rag_service import MusicKnowledgeService

logger = logging.getLogger(__name__)


class AgentToolError(ValueError):
    """工具参数合法但业务数据无法满足请求。"""


class MusicAgentTools:
    """把音乐查询能力封装成 Agent 可调用的只读工具。"""

    def __init__(
        self, db: Session, user_id: int, embedding_provider: EmbeddingProvider | None = None
    ) -> None:
        """为当前用户装配只读音乐工具，并共享同一数据库会话。"""
        self.db = db
        self.songs = SongRepository(db)
        self.recommendations = RecommendationRepository(db)
        self.embedding_provider = embedding_provider or OpenAICompatibleEmbeddingProvider()
        self.knowledge = MusicKnowledgeService(db, self.embedding_provider)
        self.user_id = user_id

    def register_all(self, registry: ToolRegistry) -> None:
        """注册文档规定的五个核心工具。"""
        registry.register(
            AgentTool(
                "search_songs",
                "搜索歌曲，可按歌名、歌手、风格和标签筛选。",
                SearchSongsInput.model_json_schema(),
                self.search_songs,
            )
        )
        registry.register(
            AgentTool(
                "analyze_song",
                "分析歌曲的 BPM、Key、Energy、Valence、Danceability 等音乐特征。",
                SongIdInput.model_json_schema(),
                self.analyze_song,
            )
        )
        registry.register(
            AgentTool(
                "find_similar_songs",
                "根据歌曲的风格和结构化音乐特征查找相似歌曲。",
                SimilarSongsInput.model_json_schema(),
                self.find_similar_songs,
            )
        )
        registry.register(
            AgentTool(
                "analyze_user_taste",
                "根据当前用户的收藏和播放记录分析音乐偏好。",
                {"type": "object", "properties": {}, "additionalProperties": False},
                self.analyze_user_taste,
            )
        )
        registry.register(
            AgentTool(
                "search_music_knowledge",
                "检索音乐理论、术语和风格知识库。",
                KnowledgeSearchInput.model_json_schema(),
                self.search_music_knowledge,
            )
        )

    def search_songs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行歌曲搜索工具。"""
        payload = SearchSongsInput.model_validate(arguments)
        self._apply_statement_timeout()
        songs = self.songs.search(payload.query, payload.genre, payload.tags, payload.limit)
        return {"items": [self._summary(song) for song in songs], "count": len(songs)}

    def analyze_song(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """返回一首歌曲的完整音乐特征。"""
        payload = SongIdInput.model_validate(arguments)
        self._apply_statement_timeout()
        song = self.songs.get_by_id(payload.song_id)
        if song is None:
            raise AgentToolError("歌曲不存在")
        return SongDetail.model_validate(song).model_dump(mode="json")

    def find_similar_songs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行结构化特征相似歌曲查询。"""
        payload = SimilarSongsInput.model_validate(arguments)
        self._apply_statement_timeout()
        song = self.songs.get_by_id(payload.song_id)
        if song is None:
            raise AgentToolError("歌曲不存在")
        vector_songs = self._find_similar_by_vector(song, payload.limit)
        if vector_songs:
            return {
                "items": [self._summary(item) for item in vector_songs],
                "count": len(vector_songs),
            }
        songs = self.songs.find_similar(song, payload.limit)
        return {"items": [self._summary(item) for item in songs], "count": len(songs)}

    def analyze_user_taste(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """返回当前用户的偏好风格和平均特征。"""
        if arguments:
            raise AgentToolError("该工具不接受参数")
        self._apply_statement_timeout()
        return {
            "user_id": self.user_id,
            "preferred_genres": self.recommendations.preferred_genres(self.user_id),
            "feature_profile": self.recommendations.feature_profile(self.user_id),
        }

    def search_music_knowledge(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """检索知识库文本切片。"""
        payload = KnowledgeSearchInput.model_validate(arguments)
        self._apply_statement_timeout()
        return self.knowledge.search(payload.query, payload.limit)

    def _find_similar_by_vector(self, song: Song, limit: int) -> list[Song]:
        """优先使用歌曲向量检索；服务未配置或查询失败时返回空列表。"""
        embedding = song.embedding
        if embedding is None and self.embedding_provider.is_configured:
            try:
                vectors = self.embedding_provider.embed([self._song_text(song)])
                embedding = vectors[0]
            except (EmbeddingProviderError, IndexError) as error:
                logger.warning("歌曲向量生成失败，回退结构化检索：%s", error)
                return []
        if embedding is None:
            return []
        try:
            with self.db.begin_nested():
                matches = self.songs.find_similar_vector(
                    song,
                    embedding,
                    limit,
                    settings.embedding_similarity_threshold,
                )
        except SQLAlchemyError:
            logger.exception("歌曲向量查询失败，回退结构化检索")
            return []
        return [item for item, _distance in matches]

    @staticmethod
    def _song_text(song: Song) -> str:
        """将歌曲元数据组合为 Embedding 输入文本。"""
        artist_name = song.artist.name if song.artist is not None else ""
        fields = [
            song.title,
            artist_name,
            song.genre or "",
            song.music_key or "",
            song.instruments or "",
            f"bpm:{song.bpm}" if song.bpm is not None else "",
            f"energy:{song.energy}" if song.energy is not None else "",
            f"valence:{song.valence}" if song.valence is not None else "",
            f"danceability:{song.danceability}" if song.danceability is not None else "",
        ]
        return " | ".join(field for field in fields if field)

    @staticmethod
    def _summary(song: object) -> dict[str, Any]:
        """转换歌曲列表项为可序列化字典。"""
        return SongSummary.model_validate(song).model_dump(mode="json")

    def _apply_statement_timeout(self) -> None:
        """为 PostgreSQL 当前事务设置单次工具查询的超时。"""
        bind = self.db.bind
        if bind is None or bind.dialect.name != "postgresql":
            return
        timeout_ms = max(1, int(settings.agent_tool_timeout_seconds * 1000))
        self.db.execute(
            text("SELECT set_config('statement_timeout', :timeout, true)"),
            {"timeout": f"{timeout_ms}ms"},
        )
