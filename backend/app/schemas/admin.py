"""管理后台的概览与账号管理接口模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminCountItem(BaseModel):
    """一个统计项：名称 + 数量。"""

    label: str
    count: int


class AdminOverview(BaseModel):
    """管理后台首页数据：核心计数 + 曲库分布。"""

    songs: int
    artists: int
    users: int
    admins: int
    playlists: int
    feedback: int
    favorites: int
    plays: int
    knowledge: int
    import_jobs: int
    songs_with_embedding: int
    songs_with_audio_features: int
    genre_distribution: list[AdminCountItem]


class AdminUserItem(BaseModel):
    """账号列表行。"""

    id: int
    username: str
    role: str
    status: str
    created_at: datetime
    favorites: int
    playlists: int
    feedback: int

    model_config = ConfigDict(from_attributes=True)


class AdminUserPage(BaseModel):
    """账号分页结果。"""

    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class AdminUserUpdate(BaseModel):
    """可修改的账号字段；留空表示不改。"""

    role: str | None = None
    status: str | None = None
