"""歌曲和歌手目录的 Pydantic 请求与响应模型。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Name = Annotated[str, Field(min_length=1, max_length=255)]


class ArtistCreate(BaseModel):
    """管理员创建歌手请求。"""

    name: Name
    avatar_url: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ArtistUpdate(BaseModel):
    """管理员局部更新歌手请求。"""

    name: Name | None = None
    avatar_url: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_update(self) -> ArtistUpdate:
        """要求至少更新一个字段，且歌手名不能显式置空。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个待更新字段")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("歌手名不能为空")
        return self


class ArtistResponse(BaseModel):
    """歌手列表和详情响应。"""

    id: int
    name: str
    avatar_url: str | None
    song_count: int


class ArtistPage(BaseModel):
    """分页歌手响应。"""

    items: list[ArtistResponse]
    total: int
    page: int
    page_size: int


class SongCreate(BaseModel):
    """管理员创建歌曲请求。"""

    title: Name
    artist_id: Annotated[int, Field(gt=0)]
    genre: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    language: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    duration: Annotated[int, Field(ge=0)] | None = None
    audio_url: HttpUrl
    lyrics: str | None = None
    popularity: Annotated[int, Field(ge=0)] = 0

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SongUpdate(BaseModel):
    """管理员局部更新歌曲请求。"""

    title: Name | None = None
    artist_id: Annotated[int, Field(gt=0)] | None = None
    genre: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    language: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    duration: Annotated[int, Field(ge=0)] | None = None
    audio_url: HttpUrl | None = None
    lyrics: str | None = None
    popularity: Annotated[int, Field(ge=0)] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_update(self) -> SongUpdate:
        """要求至少更新一个字段，且必填字段不能显式置空。"""
        if not self.model_fields_set:
            raise ValueError("至少提供一个待更新字段")
        for field_name in ("title", "artist_id", "audio_url", "popularity"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为空")
        return self


class SongArtist(BaseModel):
    """歌曲响应中的精简歌手信息。"""

    id: int
    name: str
    avatar_url: str | None

    model_config = ConfigDict(from_attributes=True)


class SongSummary(BaseModel):
    """歌曲列表项。"""

    id: int
    title: str
    artist: SongArtist
    genre: str | None
    language: str | None
    duration: int | None
    audio_url: str
    popularity: int

    model_config = ConfigDict(from_attributes=True)


class SongDetail(SongSummary):
    """歌曲详情响应。"""

    lyrics: str | None


class SongPage(BaseModel):
    """分页歌曲响应。"""

    items: list[SongSummary]
    total: int
    page: int
    page_size: int
