"""用户歌单与收藏数据访问。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.associations import PlaylistSong
from app.models.favorite import Favorite
from app.models.playlist import Playlist
from app.models.song import Song


class LibraryRepository:
    """封装用户音乐库相关查询和写入。"""

    def __init__(self, db: Session) -> None:
        """绑定用户音乐库所需的数据库会话。"""
        self.db = db

    def list_playlists(self, user_id: int) -> list[tuple[Playlist, int]]:
        """返回用户歌单及歌曲数量。"""
        statement = (
            select(Playlist, func.count(PlaylistSong.song_id))
            .outerjoin(PlaylistSong)
            .where(Playlist.user_id == user_id)
            .group_by(Playlist.id)
            .order_by(Playlist.created_at.desc(), Playlist.id.desc())
        )
        return [(row[0], row[1]) for row in self.db.execute(statement)]

    def get_playlist(self, playlist_id: int, user_id: int) -> Playlist | None:
        """按用户查询歌单并加载歌曲。"""
        statement = (
            select(Playlist)
            .options(
                joinedload(Playlist.song_links)
                .joinedload(PlaylistSong.song)
                .joinedload(Song.artist)
            )
            .where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        )
        return self.db.scalars(statement).unique().one_or_none()

    def create_playlist(self, user_id: int, name: str, description: str | None) -> Playlist:
        """创建歌单。"""
        playlist = Playlist(user_id=user_id, name=name, description=description)
        self.db.add(playlist)
        self.db.flush()
        self.db.refresh(playlist)
        return playlist

    def update_playlist(self, playlist: Playlist, values: Mapping[str, Any]) -> Playlist:
        """修改歌单字段。"""
        for field_name, value in values.items():
            setattr(playlist, field_name, value)
        self.db.flush()
        self.db.refresh(playlist)
        return playlist

    def delete_playlist(self, playlist: Playlist) -> None:
        """删除歌单和关联。"""
        self.db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == playlist.id))
        self.db.delete(playlist)
        self.db.flush()

    def get_song(self, song_id: int) -> Song | None:
        """查询歌曲。"""
        return self.db.get(Song, song_id)

    def add_playlist_song(self, playlist_id: int, song_id: int) -> bool:
        """歌曲不存在于歌单时追加并返回真。"""
        exists = self.db.get(PlaylistSong, (playlist_id, song_id))
        if exists is not None:
            return False
        position = self.db.scalar(
            select(func.coalesce(func.max(PlaylistSong.position), -1)).where(
                PlaylistSong.playlist_id == playlist_id
            )
        )
        if position is None:
            position = -1
        self.db.add(PlaylistSong(playlist_id=playlist_id, song_id=song_id, position=position + 1))
        self.db.flush()
        return True

    def remove_playlist_song(self, playlist_id: int, song_id: int) -> bool:
        """删除歌单歌曲并返回是否存在。"""
        link = self.db.get(PlaylistSong, (playlist_id, song_id))
        if link is None:
            return False
        self.db.delete(link)
        self.db.flush()
        return True

    def list_favorites(self, user_id: int) -> list[Favorite]:
        """返回用户收藏。"""
        return list(
            self.db.scalars(
                select(Favorite)
                .where(Favorite.user_id == user_id)
                .order_by(Favorite.created_at.desc(), Favorite.id.desc())
            )
        )

    def get_favorite(self, user_id: int, song_id: int) -> Favorite | None:
        """查询指定收藏。"""
        return self.db.scalar(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.song_id == song_id)
        )

    def add_favorite(self, user_id: int, song_id: int) -> Favorite:
        """创建收藏。"""
        favorite = Favorite(user_id=user_id, song_id=song_id)
        self.db.add(favorite)
        self.db.flush()
        self.db.refresh(favorite)
        return favorite

    def delete_favorite(self, favorite: Favorite) -> None:
        """删除收藏。"""
        self.db.delete(favorite)
        self.db.flush()
