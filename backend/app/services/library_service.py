"""用户歌单与收藏业务逻辑。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.playlist import Playlist
from app.repositories.library_repository import LibraryRepository
from app.schemas.catalog import SongSummary
from app.schemas.library import (
    FavoriteItem,
    FavoritePage,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItem,
    PlaylistPage,
    PlaylistUpdate,
)


class PlaylistNotFoundError(Exception):
    """歌单不存在或不属于当前用户。"""


class SongNotFoundError(Exception):
    """歌曲不存在。"""


class DuplicateRelationError(Exception):
    """收藏或歌单歌曲关系已存在。"""


class RelationNotFoundError(Exception):
    """收藏或歌单歌曲关系不存在。"""


class LibraryService:
    """编排用户歌单和收藏业务。"""

    def __init__(self, db: Session) -> None:
        self.repository = LibraryRepository(db)

    def list_playlists(self, user_id: int) -> PlaylistPage:
        """列出当前用户歌单。"""
        items = [
            self._playlist_item(item, count)
            for item, count in self.repository.list_playlists(user_id)
        ]
        return PlaylistPage(items=items)

    def get_playlist(self, playlist_id: int, user_id: int) -> PlaylistDetail:
        """读取当前用户歌单详情。"""
        playlist = self._require_playlist(playlist_id, user_id)
        links = sorted(playlist.song_links, key=lambda link: link.position)
        return PlaylistDetail(
            **self._playlist_item(playlist, len(links)).model_dump(),
            songs=[SongSummary.model_validate(link.song) for link in links],
        )

    def create_playlist(self, user_id: int, payload: PlaylistCreate) -> PlaylistItem:
        """创建当前用户歌单。"""
        playlist = self.repository.create_playlist(user_id, payload.name, payload.description)
        return self._playlist_item(playlist, 0)

    def update_playlist(
        self, playlist_id: int, user_id: int, payload: PlaylistUpdate
    ) -> PlaylistItem:
        """修改当前用户歌单。"""
        playlist = self._require_playlist(playlist_id, user_id)
        playlist = self.repository.update_playlist(playlist, payload.model_dump(exclude_unset=True))
        count = len(playlist.song_links)
        return self._playlist_item(playlist, count)

    def delete_playlist(self, playlist_id: int, user_id: int) -> None:
        """删除当前用户歌单。"""
        self.repository.delete_playlist(self._require_playlist(playlist_id, user_id))

    def add_playlist_song(self, playlist_id: int, user_id: int, song_id: int) -> None:
        """向当前用户歌单追加歌曲。"""
        self._require_playlist(playlist_id, user_id)
        self._require_song(song_id)
        if not self.repository.add_playlist_song(playlist_id, song_id):
            raise DuplicateRelationError

    def remove_playlist_song(self, playlist_id: int, user_id: int, song_id: int) -> None:
        """从当前用户歌单删除歌曲。"""
        self._require_playlist(playlist_id, user_id)
        if not self.repository.remove_playlist_song(playlist_id, song_id):
            raise RelationNotFoundError

    def list_favorites(self, user_id: int) -> FavoritePage:
        """列出当前用户收藏。"""
        return FavoritePage(
            items=[
                FavoriteItem.model_validate(item, from_attributes=True)
                for item in self.repository.list_favorites(user_id)
            ]
        )

    def add_favorite(self, user_id: int, song_id: int) -> FavoriteItem:
        """收藏歌曲。"""
        self._require_song(song_id)
        if self.repository.get_favorite(user_id, song_id) is not None:
            raise DuplicateRelationError
        item = self.repository.add_favorite(user_id, song_id)
        return FavoriteItem.model_validate(item, from_attributes=True)

    def remove_favorite(self, user_id: int, song_id: int) -> None:
        """取消收藏歌曲。"""
        favorite = self.repository.get_favorite(user_id, song_id)
        if favorite is None:
            raise RelationNotFoundError
        self.repository.delete_favorite(favorite)

    def _require_playlist(self, playlist_id: int, user_id: int) -> Playlist:
        playlist = self.repository.get_playlist(playlist_id, user_id)
        if playlist is None:
            raise PlaylistNotFoundError
        return playlist

    def _require_song(self, song_id: int) -> None:
        if self.repository.get_song(song_id) is None:
            raise SongNotFoundError

    @staticmethod
    def _playlist_item(playlist: Playlist, song_count: int) -> PlaylistItem:
        return PlaylistItem(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            song_count=song_count,
            created_at=playlist.created_at,
        )
