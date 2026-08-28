"""Agent 对话接口模型。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AgentMessage(BaseModel):
    """Agent 用户消息。"""

    message: Annotated[str, Field(min_length=1, max_length=2000)]
    session_id: Annotated[int, Field(gt=0)] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchSongsInput(BaseModel):
    """歌曲搜索工具参数。"""

    query: Annotated[str | None, Field(max_length=255)] = None
    genre: Annotated[str | None, Field(max_length=100)] = None
    tags: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list)
    limit: Annotated[int, Field(ge=1, le=20)] = 10

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SongIdInput(BaseModel):
    """歌曲 ID 工具参数。"""

    song_id: Annotated[int, Field(gt=0)]

    model_config = ConfigDict(extra="forbid")


class SimilarSongsInput(SongIdInput):
    """相似歌曲工具参数。"""

    limit: Annotated[int, Field(ge=1, le=20)] = 10


class KnowledgeSearchInput(BaseModel):
    """音乐知识检索工具参数。"""

    query: Annotated[str, Field(min_length=1, max_length=500)]
    limit: Annotated[int, Field(ge=1, le=10)] = 5

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentEvent(BaseModel):
    """SSE 事件内容。"""

    type: str
    content: str
