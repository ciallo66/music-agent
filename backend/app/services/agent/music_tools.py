"""音乐 Agent 的只读业务工具。"""

from __future__ import annotations  # 惯例：类型注解延迟求值（见 registry.py 说明）

import logging  # 标准库：打日志
from typing import Any  # 类型提示：Any = 类型不限

from sqlalchemy import text  # 写原生 SQL（给查询设超时用）
from sqlalchemy.exc import SQLAlchemyError  # 数据库出错的异常类型（用来捕获）
from sqlalchemy.orm import Session  # 数据库会话类型（标注函数入参）

from app.core.config import settings  # 读 .env 配置（超时秒数、向量阈值等）
from app.models.song import Song  # 歌曲"表"的模型（查询结果的类型）
from app.repositories.catalog_repository import SongRepository  # 仓库：去数据库搜歌
from app.repositories.recommendation_repository import RecommendationRepository  # 仓库：查用户口味
from app.schemas.agent import (  # 工具的"入参校验器"：生成参数 schema + 校验模型传参
    KnowledgeSearchInput,  # 知识问答工具的入参
    SearchSongsInput,  # 搜歌工具的入参
    SimilarSongsInput,  # 相似歌工具的入参
    SongIdInput,  # 按歌曲 ID 查询的入参
    WebSearchInput,  # 联网搜索工具的入参
)
from app.schemas.catalog import SongDetail, SongSummary  # 歌曲的"返回格式"（查询结果转成什么样）
from app.schemas.library import PlaylistCreate  # 创建歌单入参（与接口共用同一套校验）
from app.services.agent.registry import (  # 工具格式 + 操作类型 + 工具箱（登记用）
    AgentTool,
    ToolOperation,
    ToolRegistry,
)
from app.services.embedding_provider import (  # 生成"向量"的服务（相似歌/知识库要用）
    EmbeddingProvider,  # 向量服务接口
    EmbeddingProviderError,  # 向量服务异常
    OpenAICompatibleEmbeddingProvider,  # 向量服务实现（真干活那个）
)
from app.services.library_service import LibraryService  # 歌单与收藏业务（写操作复用）
from app.services.rag_service import MusicKnowledgeService  # RAG 音乐知识库服务
from app.services.song_embedding_text import (  # 歌曲向量化文本（与批量向量化共用）
    build_song_text,
)
from app.services.web_search_service import (  # 联网搜索服务（查站外资料用）
    DuckDuckGoWebSearchService,  # 搜索服务实现（真干活那个）
    WebSearchProvider,  # 搜索服务接口
)

logger = logging.getLogger(__name__)


class AgentToolError(ValueError):
    """工具参数合法但业务数据无法满足请求。"""


class MusicAgentTools:
    """把音乐查询能力封装成 Agent 可调用的只读工具。"""

    def __init__(
        self,
        db: Session,
        user_id: int,
        embedding_provider: EmbeddingProvider | None = None,
        web_search: WebSearchProvider | None = None,
    ) -> None:
        """为当前用户装配只读音乐工具，并共享同一数据库会话。"""
        self.db = db
        self.songs = SongRepository(db)
        self.recommendations = RecommendationRepository(db)
        self.embedding_provider = embedding_provider or OpenAICompatibleEmbeddingProvider()
        self.knowledge = MusicKnowledgeService(db, self.embedding_provider)
        self.web_search = web_search or DuckDuckGoWebSearchService()
        self.library = LibraryService(db)
        self.user_id = user_id

    def register_all(self, registry: ToolRegistry) -> None:
        """注册文档规定的核心工具（全部为只读）。"""
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
                (
                    "分析歌曲的 AcousticBrainz 音频特征，包括节奏、调性、频谱、"
                    "情绪/流派标签以及各项置信度；仅在缺失字段影响当前问题时说明。"
                ),
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
        registry.register(
            AgentTool(
                "search_web",
                "联网搜索站外资料，用于查询音乐库之外的最新信息或外部事实。",
                WebSearchInput.model_json_schema(),
                self.search_web,
            )
        )
        registry.register(
            AgentTool(
                "create_playlist",
                "为当前用户创建新歌单；这是写操作，需要用户确认后才会真正执行。",
                PlaylistCreate.model_json_schema(),
                self.create_playlist,
                ToolOperation.WRITE,
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

    def create_playlist(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """为当前登录用户创建歌单（写操作，所有权由服务端身份决定）。"""
        payload = PlaylistCreate.model_validate(arguments)
        self._apply_statement_timeout()
        # 放在保存点里执行：失败只回滚这一步，不污染整个请求的事务。
        with self.db.begin_nested():
            item = self.library.create_playlist(self.user_id, payload)
        return {"playlist": item.model_dump(mode="json")}

    def search_web(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """检索站外资料，返回标题、链接和摘要。"""
        payload = WebSearchInput.model_validate(arguments)
        limit = min(payload.limit, settings.web_search_max_results)
        items = self.web_search.search(payload.query, limit, payload.freshness)
        return {"items": items, "count": len(items)}

    def _find_similar_by_vector(self, song: Song, limit: int) -> list[Song]:
        """优先使用歌曲向量检索；服务未配置或查询失败时返回空列表。"""
        embedding = song.embedding
        if embedding is None and self.embedding_provider.is_configured:
            try:
                vectors = self.embedding_provider.embed([build_song_text(song)])
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
