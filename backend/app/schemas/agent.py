"""Agent 对话接口模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolConfirmationDecision(BaseModel):
    """用户对单条待确认工具调用的决定。"""

    confirmation_id: Annotated[int, Field(gt=0)]
    approved: bool


class ToolConfirmationRequest(BaseModel):
    """提交待确认工具调用的处理结果。"""

    session_id: Annotated[int, Field(gt=0)]
    decisions: Annotated[list[ToolConfirmationDecision], Field(min_length=1)]

    model_config = ConfigDict(extra="forbid")


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


class WebSearchInput(BaseModel):
    """联网搜索工具参数。"""

    query: Annotated[str, Field(min_length=1, max_length=200)]
    limit: Annotated[int, Field(ge=1, le=8)] = 4
    freshness: Literal["day", "week", "month", "year"] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AddSongsToPlaylistInput(BaseModel):
    """把歌曲加入歌单的工具参数。

    歌单与歌曲都按主键定位：歌单必须属于当前用户，歌曲必须存在，
    两者都在工具执行前校验，避免模型凭歌名猜测。
    """

    playlist_id: Annotated[int, Field(gt=0)]
    song_ids: Annotated[list[Annotated[int, Field(gt=0)]], Field(min_length=1, max_length=20)]

    model_config = ConfigDict(extra="forbid")


class AgentSessionSummary(BaseModel):
    """历史会话列表项：标题、时间与消息条数。"""

    id: int
    created_at: datetime
    message_count: int
    # 标题取该会话第一条用户消息；没有用户消息时为 None，由前端显示兜底文案
    title: str | None
    # 最后一条消息的主键，用来代表活跃度排序（会话表本身没有更新时间列）
    last_message_id: int | None


class AgentSessionMessage(BaseModel):
    """历史会话里的一条消息。"""

    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class AgentSessionDetail(BaseModel):
    """单个历史会话的完整消息，用于刷新后恢复对话。"""

    id: int
    created_at: datetime
    messages: list[AgentSessionMessage]
