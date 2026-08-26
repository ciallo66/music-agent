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
        CheckConstraint("bpm IS NULL OR bpm > 0", name="ck_songs_bpm_positive"),
        CheckConstraint(
            "energy IS NULL OR (energy >= 0 AND energy <= 1)",
            name="ck_songs_energy_range",
        ),
        CheckConstraint(
            "valence IS NULL OR (valence >= 0 AND valence <= 1)",
            name="ck_songs_valence_range",
        ),
        CheckConstraint(
            "danceability IS NULL OR (danceability >= 0 AND danceability <= 1)",
            name="ck_songs_danceability_range",
        ),
        Index("ix_songs_title", "title"),
        Index("ix_songs_genre", "genre"),
        Index("ix_songs_language", "language"),
        Index("ix_songs_bpm", "bpm"),
        Index("ix_songs_energy", "energy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), index=True)
    album: Mapped[str | None] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(50))
    duration: Mapped[int | None]
    audio_url: Mapped[str | None] = mapped_column(String(2048))
    lyrics: Mapped[str | None] = mapped_column(Text)
    popularity: Mapped[int] = mapped_column(default=0, server_default="0")

    # 音乐特征字段（Jamendo API / Embeat 数据集来源）
    bpm: Mapped[float | None]
    music_key: Mapped[str | None] = mapped_column(String(20))
    energy: Mapped[float | None]
    valence: Mapped[float | None]
    danceability: Mapped[float | None]
    loudness: Mapped[float | None]
    instruments: Mapped[str | None] = mapped_column(String(255))
    song_structure: Mapped[str | None] = mapped_column(Text)

    artist: Mapped[Artist] = relationship(back_populates="songs")
    playlist_links: Mapped[list[PlaylistSong]] = relationship(back_populates="song")
    tag_links: Mapped[list[SongTag]] = relationship(back_populates="song")
    play_records: Mapped[list[PlayRecord]] = relationship(back_populates="song")
