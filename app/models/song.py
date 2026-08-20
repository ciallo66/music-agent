"""歌曲表模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.artist import Artist
    from app.models.associations import PlaylistSong, SongTag
    from app.models.play_record import PlayRecord


class Song(Base):
    """可播放和推荐的歌曲元数据。"""

    __tablename__ = "songs"
    __table_args__ = (
        CheckConstraint("duration IS NULL OR duration >= 0", name="ck_songs_duration_nonnegative"),
        CheckConstraint("popularity >= 0", name="ck_songs_popularity_nonnegative"),
        Index("ix_songs_title", "title"),
        Index("ix_songs_genre", "genre"),
        Index("ix_songs_language", "language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), index=True)
    genre: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(50))
    duration: Mapped[int | None]
    audio_url: Mapped[str] = mapped_column(String(2048))
    lyrics: Mapped[str | None] = mapped_column(Text)
    popularity: Mapped[int] = mapped_column(default=0, server_default="0")

    artist: Mapped[Artist] = relationship(back_populates="songs")
    playlist_links: Mapped[list[PlaylistSong]] = relationship(back_populates="song")
    tag_links: Mapped[list[SongTag]] = relationship(back_populates="song")
    play_records: Mapped[list[PlayRecord]] = relationship(back_populates="song")
