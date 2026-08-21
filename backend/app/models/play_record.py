"""播放记录表模型。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.user import User


class PlayRecord(Base):
    """用户每次播放歌曲的行为记录。"""

    __tablename__ = "play_records"
    __table_args__ = (Index("ix_play_records_user_played_at", "user_id", "played_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), index=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="play_records")
    song: Mapped[Song] = relationship(back_populates="play_records")
