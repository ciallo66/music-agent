"""歌曲和歌手目录业务逻辑。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.artist import Artist
from app.models.song import Song
from app.repositories.catalog_repository import ArtistRepository, SongRepository
from app.schemas.catalog import (
    ArtistCreate,
    ArtistPage,
    ArtistResponse,
    ArtistUpdate,
    SongCreate,
    SongDetail,
    SongPage,
    SongSummary,
    SongUpdate,
)


class ArtistNotFoundError(Exception):
    """请求的歌手不存在。"""


class SongNotFoundError(Exception):
    """请求的歌曲不存在。"""


class ArtistHasSongsError(Exception):
    """歌手仍有关联歌曲，不能删除。"""


class CatalogService:
    """编排公开目录查询和管理员写入。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话及目录仓储。"""
        self.artists = ArtistRepository(db)
        self.songs = SongRepository(db)

    def list_artists(self, page: int, page_size: int, search: str | None) -> ArtistPage:
        """分页返回歌手及歌曲数量。"""
        artists, total = self.artists.list_page(page, page_size, search)
        items = [self._artist_response(artist, song_count) for artist, song_count in artists]
        return ArtistPage(items=items, total=total, page=page, page_size=page_size)

    def get_artist(self, artist_id: int) -> ArtistResponse:
        """返回歌手详情，不存在时抛出业务异常。"""
        artist = self._require_artist(artist_id)
        return self._artist_response(artist)

    def create_artist(self, payload: ArtistCreate) -> ArtistResponse:
        """创建歌手并刷新持久化对象。"""
        values = payload.model_dump(mode="json")
        artist = self.artists.create(**values)
        return self._artist_response(artist)

    def update_artist(self, artist_id: int, payload: ArtistUpdate) -> ArtistResponse:
        """局部更新歌手并刷新持久化对象。"""
        artist = self._require_artist(artist_id)
        values = payload.model_dump(exclude_unset=True, mode="json")
        artist = self.artists.update(artist, values)
        return self._artist_response(artist)

    def delete_artist(self, artist_id: int) -> None:
        """删除无歌曲关联的歌手。"""
        artist = self._require_artist(artist_id)
        if self.artists.count_songs(artist_id) > 0:
            raise ArtistHasSongsError
        self.artists.delete(artist)

    def list_songs(
        self,
        page: int,
        page_size: int,
        query: str | None,
        genre: str | None,
        language: str | None,
        artist_id: int | None,
    ) -> SongPage:
        """分页搜索歌曲并返回精简列表项。"""
        songs, total = self.songs.list_page(page, page_size, query, genre, language, artist_id)
        items = [SongSummary.model_validate(song) for song in songs]
        return SongPage(items=items, total=total, page=page, page_size=page_size)

    def list_genres(self) -> list[str]:
        """返回目录中实际存在的风格列表，供前端筛选选项使用。"""
        return self.songs.list_genres()

    def get_song(self, song_id: int) -> SongDetail:
        """返回歌曲详情，不存在时抛出业务异常。"""
        return SongDetail.model_validate(self._require_song(song_id))

    def create_song(self, payload: SongCreate) -> SongDetail:
        """验证歌手后创建歌曲并刷新持久化对象。"""
        self._require_artist(payload.artist_id)
        song = self.songs.create(payload.model_dump(mode="json"))
        return SongDetail.model_validate(song)

    def update_song(self, song_id: int, payload: SongUpdate) -> SongDetail:
        """验证关联后局部更新歌曲并刷新持久化对象。"""
        song = self._require_song(song_id)
        values = payload.model_dump(exclude_unset=True, mode="json")
        artist_id = values.get("artist_id")
        if artist_id is not None:
            self._require_artist(artist_id)
        song = self.songs.update(song, values)
        return SongDetail.model_validate(song)

    def delete_song(self, song_id: int) -> None:
        """清理歌曲关联后删除歌曲。"""
        song = self._require_song(song_id)
        self.songs.delete_with_relations(song)

    def _require_artist(self, artist_id: int) -> Artist:
        """获取歌手或抛出统一不存在异常。"""
        artist = self.artists.get_by_id(artist_id)
        if artist is None:
            raise ArtistNotFoundError
        return artist

    def _require_song(self, song_id: int) -> Song:
        """获取歌曲或抛出统一不存在异常。"""
        song = self.songs.get_by_id(song_id)
        if song is None:
            raise SongNotFoundError
        return song

    def _artist_response(self, artist: Artist, song_count: int | None = None) -> ArtistResponse:
        """组装带歌曲数量的歌手响应。"""
        return ArtistResponse(
            id=artist.id,
            name=artist.name,
            avatar_url=artist.avatar_url,
            song_count=(
                song_count if song_count is not None else self.artists.count_songs(artist.id)
            ),
        )
