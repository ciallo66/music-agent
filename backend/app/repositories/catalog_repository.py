"""歌曲和歌手目录的数据访问。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.artist import Artist
from app.models.associations import PlaylistSong, SongTag
from app.models.play_record import PlayRecord
from app.models.song import Song


class ArtistRepository:
    """封装歌手查询和写入。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话。"""
        self.db = db

    def list_page(
        self, page: int, page_size: int, search: str | None
    ) -> tuple[list[tuple[Artist, int]], int]:
        """分页查询歌手并加载歌曲数量。"""
        conditions = []
        if search:
            conditions.append(Artist.name.ilike(_contains(search), escape="\\"))
        total = self.db.scalar(select(func.count()).select_from(Artist).where(*conditions)) or 0
        statement = (
            select(Artist, func.count(Song.id))
            .outerjoin(Song)
            .where(*conditions)
            .group_by(Artist.id)
            .order_by(Artist.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [(row[0], row[1]) for row in self.db.execute(statement)], total

    def get_by_id(self, artist_id: int) -> Artist | None:
        """按主键查询歌手。"""
        return self.db.get(Artist, artist_id)

    def count_songs(self, artist_id: int) -> int:
        """统计歌手关联的歌曲数量。"""
        statement = select(func.count()).select_from(Song).where(Song.artist_id == artist_id)
        return self.db.scalar(statement) or 0

    def create(self, name: str, avatar_url: str | None) -> Artist:
        """创建歌手并刷新数据库字段。"""
        artist = Artist(name=name, avatar_url=avatar_url)
        self.db.add(artist)
        self.db.flush()
        self.db.refresh(artist)
        return artist

    def update(self, artist: Artist, values: Mapping[str, Any]) -> Artist:
        """更新指定歌手字段。"""
        for field_name, value in values.items():
            setattr(artist, field_name, value)
        self.db.flush()
        self.db.refresh(artist)
        return artist

    def delete(self, artist: Artist) -> None:
        """删除没有歌曲关联的歌手。"""
        self.db.delete(artist)
        self.db.flush()


class SongRepository:
    """封装歌曲查询、写入和关联清理。"""

    def __init__(self, db: Session) -> None:
        """绑定当前数据库会话。"""
        self.db = db

    def list_page(
        self,
        page: int,
        page_size: int,
        query: str | None,
        genre: str | None,
        language: str | None,
        artist_id: int | None,
    ) -> tuple[list[Song], int]:
        """分页搜索和筛选歌曲。"""
        conditions = self._conditions(query, genre, language, artist_id)
        count_statement = select(func.count()).select_from(Song).join(Artist).where(*conditions)
        total = self.db.scalar(count_statement) or 0
        statement = (
            select(Song)
            .join(Artist)
            .options(joinedload(Song.artist))
            .where(*conditions)
            .order_by(Song.popularity.desc(), Song.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(statement)), total

    def get_by_id(self, song_id: int) -> Song | None:
        """按主键查询歌曲并加载歌手。"""
        statement = select(Song).options(joinedload(Song.artist)).where(Song.id == song_id)
        return self.db.scalar(statement)

    def create(self, values: Mapping[str, Any]) -> Song:
        """创建歌曲并加载歌手。"""
        song = Song(**values)
        self.db.add(song)
        self.db.flush()
        self.db.refresh(song)
        return song

    def update(self, song: Song, values: Mapping[str, Any]) -> Song:
        """更新指定歌曲字段。"""
        for field_name, value in values.items():
            setattr(song, field_name, value)
        self.db.flush()
        self.db.expire(song, ["artist"])
        return song

    def delete_with_relations(self, song: Song) -> None:
        """显式清理歌曲关联记录后删除歌曲。"""
        self.db.execute(delete(PlaylistSong).where(PlaylistSong.song_id == song.id))
        self.db.execute(delete(SongTag).where(SongTag.song_id == song.id))
        self.db.execute(delete(PlayRecord).where(PlayRecord.song_id == song.id))
        self.db.delete(song)
        self.db.flush()

    @staticmethod
    def _conditions(
        query: str | None,
        genre: str | None,
        language: str | None,
        artist_id: int | None,
    ) -> list[Any]:
        """构造歌曲列表的统一筛选条件。"""
        conditions: list[Any] = []
        if query:
            pattern = _contains(query)
            conditions.append(
                or_(
                    Song.title.ilike(pattern, escape="\\"),
                    Artist.name.ilike(pattern, escape="\\"),
                )
            )
        if genre:
            conditions.append(func.lower(Song.genre) == genre.lower())
        if language:
            conditions.append(func.lower(Song.language) == language.lower())
        if artist_id is not None:
            conditions.append(Song.artist_id == artist_id)
        return conditions


def _contains(value: str) -> str:
    """转义 SQL LIKE 通配符并生成包含匹配模式。"""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
