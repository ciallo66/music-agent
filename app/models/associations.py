"""歌单歌曲和歌曲标签关联表模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.playlist import Playlist
    from app.models.song import Song
    from app.models.tag import Tag


class PlaylistSong(Base):
    """记录歌单中的歌曲及其排序位置。"""

    __tablename__ = "playlist_songs"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_playlist_songs_position_nonnegative"),
        UniqueConstraint("playlist_id", "position", name="uq_playlist_songs_position"),
    )

    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), primary_key=True)
    position: Mapped[int]

    playlist: Mapped[Playlist] = relationship(back_populates="song_links")
    song: Mapped[Song] = relationship(back_populates="playlist_links")


class SongTag(Base):
    """记录歌曲和标签的多对多关系。"""

    __tablename__ = "song_tags"

    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

    song: Mapped[Song] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="song_links")
