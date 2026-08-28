"""用户歌单与收藏接口模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalog import SongSummary


class PlaylistCreate(BaseModel):
    """创建歌单请求。"""

    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=1000)] | None = None
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PlaylistUpdate(BaseModel):
    """修改歌单请求。"""

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: Annotated[str, Field(max_length=1000)] | None = None
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_update(self) -> PlaylistUpdate:
        """要求至少提供一个修改字段。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个待更新字段")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("歌单名称不能为空")
        return self


class SongReference(BaseModel):
    """歌曲主键请求。"""

    song_id: Annotated[int, Field(gt=0)]
    model_config = ConfigDict(extra="forbid")


class PlaylistItem(BaseModel):
    """歌单列表项。"""

    id: int
    name: str
    description: str | None
    song_count: int
    created_at: datetime


class PlaylistPage(BaseModel):
    """当前用户歌单列表。"""

    items: list[PlaylistItem]


class PlaylistDetail(PlaylistItem):
    """包含歌曲的歌单详情。"""

    songs: list[SongSummary]


class FavoriteItem(BaseModel):
    """收藏记录。"""

    id: int
    song_id: int
    created_at: datetime


class FavoritePage(BaseModel):
    """当前用户收藏列表。"""

    items: list[FavoriteItem]
