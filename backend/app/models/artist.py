"""歌手表模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.song import Song


class Artist(Base):
    """歌曲对应的歌手信息。"""

    __tablename__ = "artists"
    __table_args__ = (Index("uq_artists_source_source_id", "source", "source_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    source: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(100))

    songs: Mapped[list[Song]] = relationship(back_populates="artist")
